from datetime import (
    datetime,
    timedelta,
    timezone
)

from aiogram import (
    Router,
    F
)

from aiogram.types import (
    Message,
    CallbackQuery
)

from config import (
    ADMIN_IDS
)

from keyboards.admin_requests_keyboards import (
    admin_requests_filter_keyboard,
    admin_request_card_keyboard
)

from keyboards.main_menu import (
    admin_menu
)

from database.admin_db import (
    get_admin_requests,
    get_repair_for_admin
)

from handlers.admin_repairs import (
    send_admin_repair_card
)


router = Router()


BISHKEK_TIMEZONE = timezone(
    timedelta(hours=6)
)


def is_admin(
    telegram_id: int
):
    return telegram_id in ADMIN_IDS


def format_money(
    value
):
    try:
        return (
            f"{float(value or 0):,.0f}"
        )
    except (
        ValueError,
        TypeError
    ):
        return "0"


def format_date(
    value
):
    if not value:
        return "-"

    try:
        dt = datetime.strptime(
            str(value),
            "%Y-%m-%d %H:%M:%S"
        )

        dt = dt.replace(
            tzinfo=timezone.utc
        )

        dt = dt.astimezone(
            BISHKEK_TIMEZONE
        )

        return dt.strftime(
            "%d.%m.%Y %H:%M"
        )

    except ValueError:
        return str(value)


def status_text(
    value
):
    statuses = {
        "new": "🆕 Новая",
        "in_work": "🔧 В работе",
        "awaiting_approval":
            "⏳ На подтверждении",
        "approved":
            "✅ Подтверждена",
        "returned":
            "↩️ Возвращена мастеру",
        "cancelled":
            "❌ Отменена"
    }

    return statuses.get(
        value,
        value or "-"
    )


def payment_text(
    request: dict
):
    status = request.get(
        "client_payment_status"
    )

    paid = float(
        request.get(
            "paid_amount"
        ) or 0
    )

    expected = float(
        request.get(
            "expected_amount"
        ) or 0
    )

    if status == "paid":
        return (
            "✅ Оплачено — "
            f"{format_money(paid)} сом"
        )

    if status == "partial":
        debt = max(
            expected - paid,
            0
        )

        return (
            "🟡 Частично — "
            f"{format_money(paid)} сом"
            f" / остаток "
            f"{format_money(debt)} сом"
        )

    if expected > 0:
        return (
            "🔴 Не оплачено — "
            f"{format_money(expected)} сом"
        )

    return "🔴 Не оплачено"


def build_request_card(
    request: dict
):
    master = (
        request.get(
            "master_name"
        )
        or "Не назначен"
    )

    workflow_status = (
        request.get(
            "workflow_status"
        )
    )

    text = (
        f"📋 {request['request_code']}\n\n"

        f"🚲 Велосипед: "
        f"№{request['bike_number']}\n"

        f"📌 Статус: "
        f"{status_text(workflow_status)}\n"

        f"👨‍🔧 Мастер: "
        f"{master}\n\n"

        f"💳 Оплата:\n"
        f"{payment_text(request)}\n\n"

        f"👤 Создал: "
        f"{request.get('creator_name') or '-'}\n"

        f"📅 Создано: "
        f"{format_date(request.get('created_at'))}"
    )

    if request.get(
        "latest_repair_code"
    ):
        text += (
            "\n\n🔧 Последний ремонт: "
            f"{request['latest_repair_code']}"
        )

    if (
        workflow_status == "returned"
        and request.get(
            "rejection_reason"
        )
    ):
        text += (
            "\n\n↩️ Причина возврата:\n"
            f"{request['rejection_reason']}"
        )

    if request.get(
        "comment"
    ):
        text += (
            "\n\n📝 Комментарий:\n"
            f"{request['comment']}"
        )

    return text


async def show_requests(
    message: Message,
    status_filter: str
):
    requests = await get_admin_requests(
        status_filter=status_filter
    )

    titles = {
        "new": "🆕 НОВЫЕ ЗАЯВКИ",
        "in_work": "🔧 ЗАЯВКИ В РАБОТЕ",
        "awaiting_approval":
            "⏳ НА ПОДТВЕРЖДЕНИИ",
        "approved":
            "✅ ПОДТВЕРЖДЕННЫЕ",
        "returned":
            "↩️ ВОЗВРАЩЕННЫЕ",
        "all":
            "📋 ВСЕ ЗАЯВКИ"
    }

    title = titles.get(
        status_filter,
        "📋 ЗАЯВКИ"
    )

    if not requests:
        await message.answer(
            f"{title}\n\n"
            "Заявок нет.",
            reply_markup=admin_menu()
        )
        return

    await message.answer(
        f"{title}\n\n"
        f"Количество: {len(requests)}"
    )

    for request in requests:
        await message.answer(
            build_request_card(
                request
            ),
            reply_markup=(
                admin_request_card_keyboard(
                    request_id=request["id"],
                    repair_id=request.get(
                        "latest_repair_id"
                    ),
                    workflow_status=request[
                        "workflow_status"
                    ]
                )
            )
        )


# =========================================================
# ГЛАВНЫЙ РАЗДЕЛ
# =========================================================

@router.message(
    F.text == "📋 Все заявки"
)
async def admin_all_requests_menu(
    message: Message
):
    if not is_admin(
        message.from_user.id
    ):
        return

    await message.answer(
        "📋 ЗАЯВКИ\n\n"
        "Выберите статус:",
        reply_markup=(
            admin_requests_filter_keyboard()
        )
    )


# =========================================================
# ФИЛЬТРЫ
# =========================================================

@router.callback_query(
    F.data.startswith(
        "admin_requests:"
    )
)
async def admin_requests_filter(
    callback: CallbackQuery
):
    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    try:
        status_filter = (
            callback.data.split(":")[1]
        )

    except IndexError:
        await callback.answer(
            "Ошибка фильтра.",
            show_alert=True
        )
        return

    allowed = {
        "new",
        "in_work",
        "awaiting_approval",
        "approved",
        "returned",
        "all"
    }

    if status_filter not in allowed:
        await callback.answer(
            "Неизвестный фильтр.",
            show_alert=True
        )
        return

    await callback.answer()

    await show_requests(
        callback.message,
        status_filter
    )


# =========================================================
# ОТКРЫТЬ РЕМОНТ
# =========================================================

@router.callback_query(
    F.data.startswith(
        "admin_open_repair:"
    )
)
async def admin_open_repair(
    callback: CallbackQuery
):
    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    try:
        repair_id = int(
            callback.data.split(":")[1]
        )

    except (
        ValueError,
        IndexError
    ):
        await callback.answer(
            "Ошибка ID ремонта.",
            show_alert=True
        )
        return

    repair = await get_repair_for_admin(
        repair_id
    )

    if not repair:
        await callback.answer(
            "Ремонт не найден.",
            show_alert=True
        )
        return

    await callback.answer()

    await send_admin_repair_card(
        callback.message,
        repair
    )