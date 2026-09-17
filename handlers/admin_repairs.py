from aiogram import (
    Router,
    F
)

from aiogram.types import (
    Message,
    CallbackQuery
)

from aiogram.fsm.context import (
    FSMContext
)

from config import (
    ADMIN_IDS
)

from states.admin_states import (
    AdminRepairStates
)

from keyboards.admin_repair_keyboards import (
    admin_repair_keyboard,
    admin_rejection_cancel_keyboard
)

from keyboards.main_menu import (
    admin_menu
)

from database.admin_db import (
    get_pending_repairs,
    get_repair_for_admin,
    approve_repair,
    reject_repair
)


router = Router()


def is_admin(
    telegram_id: int
):
    return telegram_id in ADMIN_IDS


def money(
    value
):
    try:
        return f"{float(value or 0):,.0f}"
    except (
        ValueError,
        TypeError
    ):
        return "0"


def payer_text(
    payer_type
):
    if payer_type == "company":
        return "🏢 За счет компании"

    return "👤 За счет клиента"


def repair_type_text(
    repair_type
):
    if repair_type == "part":
        return "🔩 С заменой запчасти"

    return "🔧 Без замены запчасти"


def source_text(
    source_type
):
    if source_type == "warehouse":
        return "📦 Со склада"

    if source_type == "donor":
        return "🚲 С донора"

    return "-"


def payment_method_text(
    method
):
    methods = {
        "qr": "📱 QR",
        "cash": "💵 Наличные",
        "transfer": "🏦 Перевод"
    }

    return methods.get(
        method,
        method or "-"
    )


def payment_status_text(
    repair: dict
):
    if (
        repair.get("payer_type")
        == "company"
    ):
        return (
            "🏢 Оплата клиента не требуется"
        )

    status = repair.get(
        "client_payment_status"
    )

    expected = float(
        repair.get(
            "expected_amount"
        ) or 0
    )

    paid = float(
        repair.get(
            "paid_amount"
        ) or 0
    )

    if status == "paid":
        return (
            "✅ ОПЛАЧЕНО\n"
            f"Получено: {money(paid)} сом"
        )

    if status == "partial":
        debt = max(
            expected - paid,
            0
        )

        return (
            "🟡 ЧАСТИЧНО ОПЛАЧЕНО\n"
            f"Получено: {money(paid)} сом\n"
            f"Остаток: {money(debt)} сом"
        )

    if expected > 0:
        return (
            "🔴 НЕ ОПЛАЧЕНО\n"
            f"К оплате: "
            f"{money(expected)} сом"
        )

    return "🔴 НЕ ОПЛАЧЕНО"


def build_repair_card(
    repair: dict
):
    parts = repair.get(
        "parts",
        []
    )

    if parts:
        part_lines = []

        for part in parts:
            text = (
                f"• {part['part_name']}\n"
                f"  Количество: "
                f"{part['quantity']}\n"
                f"  Источник: "
                f"{source_text(part['source_type'])}"
            )

            if (
                part.get("source_type")
                == "donor"
            ):
                text += (
                    "\n  Донор: №"
                    f"{part.get('donor_bike_number') or '-'}"
                )

            part_lines.append(
                text
            )

        parts_text = "\n\n".join(
            part_lines
        )

    else:
        parts_text = (
            "Запчасти не использовались"
        )

    company_reason = ""

    if (
        repair.get("payer_type")
        == "company"
    ):
        company_reason = (
            "\n\n🏢 Причина ремонта:\n"
            f"{repair.get('company_reason') or '-'}"
        )

    text = (
        "🔧 РЕМОНТ НА ПОДТВЕРЖДЕНИЕ\n\n"

        f"Ремонт: "
        f"{repair.get('repair_code') or '-'}\n"

        f"Заявка: "
        f"{repair.get('request_code') or '-'}\n\n"

        f"🚲 Велосипед: "
        f"№{repair.get('bike_number')}\n"

        f"👨‍🔧 Мастер: "
        f"{repair.get('master_name') or '-'}\n\n"

        f"💰 {payer_text(repair.get('payer_type'))}\n"

        f"{company_reason}\n\n"

        f"{repair_type_text(repair.get('repair_type'))}\n\n"

        f"🔩 Запчасти:\n"
        f"{parts_text}\n\n"

        f"📝 Проделанная работа:\n"
        f"{repair.get('description') or '-'}\n\n"

        f"💳 Оплата:\n"
        f"{payment_status_text(repair)}"
    )

    return text


async def send_admin_repair_card(
    message: Message,
    repair: dict
):
    text = build_repair_card(
        repair
    )

    photo = repair.get(
        "bike_photo_file_id"
    )

    if photo:
        try:
            await message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=(
                    admin_repair_keyboard(
                        repair["id"]
                    )
                )
            )
            return

        except Exception:
            pass

    await message.answer(
        text,
        reply_markup=(
            admin_repair_keyboard(
                repair["id"]
            )
        )
    )


# =========================================================
# ОЧЕРЕДЬ ПОДТВЕРЖДЕНИЯ
# =========================================================

@router.message(
    F.text == "✅ На подтверждение"
)
async def pending_repairs_handler(
    message: Message
):
    if not is_admin(
        message.from_user.id
    ):
        return

    repairs = await get_pending_repairs()

    if not repairs:
        await message.answer(
            "✅ Ремонтов на подтверждение нет.",
            reply_markup=admin_menu()
        )
        return

    await message.answer(
        "✅ НА ПОДТВЕРЖДЕНИЕ\n\n"
        f"Ожидают проверки: "
        f"{len(repairs)}"
    )

    for item in repairs:
        repair = await get_repair_for_admin(
            item["id"]
        )

        if repair:
            await send_admin_repair_card(
                message,
                repair
            )


# =========================================================
# ПОДТВЕРЖДЕНИЕ
# =========================================================

@router.callback_query(
    F.data.startswith(
        "admin_approve:"
    )
)
async def approve_handler(
    callback: CallbackQuery,
    state: FSMContext
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

    result = await approve_repair(
        repair_id=repair_id,
        admin_id=callback.from_user.id,
        admin_name=(
            callback.from_user.full_name
        )
    )

    if not result["success"]:
        await callback.answer(
            "Ремонт уже обработан.",
            show_alert=True
        )
        return

    try:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    await callback.message.answer(
        "✅ РЕМОНТ ПОДТВЕРЖДЕН\n\n"
        f"Ремонт: {repair['repair_code']}\n"
        f"🚲 Велосипед: "
        f"№{repair['bike_number']}",
        reply_markup=admin_menu()
    )

    # Уведомляем мастера
    try:
        await callback.bot.send_message(
            chat_id=repair[
                "master_telegram_id"
            ],
            text=(
                "✅ РЕМОНТ ПОДТВЕРЖДЕН\n\n"
                f"Ремонт: "
                f"{repair['repair_code']}\n"
                f"🚲 Велосипед: "
                f"№{repair['bike_number']}\n\n"
                "Администратор подтвердил ремонт."
            )
        )
    except Exception:
        pass

    await state.clear()

    await callback.answer(
        "Подтверждено."
    )


# =========================================================
# ВОЗВРАТ МАСТЕРУ
# =========================================================

@router.callback_query(
    F.data.startswith(
        "admin_reject:"
    )
)
async def reject_start_handler(
    callback: CallbackQuery,
    state: FSMContext
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

    if repair["status"] != "pending":
        await callback.answer(
            "Ремонт уже обработан.",
            show_alert=True
        )
        return

    await state.clear()

    await state.update_data(
        repair_id=repair_id
    )

    await state.set_state(
        AdminRepairStates.rejection_reason
    )

    await callback.message.answer(
        "↩️ ВОЗВРАТ МАСТЕРУ\n\n"
        f"Ремонт: {repair['repair_code']}\n"
        f"🚲 Велосипед: "
        f"№{repair['bike_number']}\n\n"
        "Укажите причину возврата.\n\n"
        "Например:\n"
        "На фотографии не виден номер "
        "велосипеда.",
        reply_markup=(
            admin_rejection_cancel_keyboard()
        )
    )

    await callback.answer()


@router.message(
    AdminRepairStates.rejection_reason
)
async def rejection_reason_handler(
    message: Message,
    state: FSMContext
):
    if not is_admin(
        message.from_user.id
    ):
        return

    if not message.text:
        await message.answer(
            "Введите причину возврата текстом."
        )
        return

    reason = message.text.strip()

    if len(reason) < 3:
        await message.answer(
            "Причина слишком короткая."
        )
        return

    data = await state.get_data()

    repair_id = data.get(
        "repair_id"
    )

    if not repair_id:
        await state.clear()

        await message.answer(
            "❌ Не удалось определить ремонт.",
            reply_markup=admin_menu()
        )
        return

    repair = await get_repair_for_admin(
        repair_id
    )

    if not repair:
        await state.clear()

        await message.answer(
            "❌ Ремонт не найден.",
            reply_markup=admin_menu()
        )
        return

    result = await reject_repair(
        repair_id=repair_id,
        admin_id=message.from_user.id,
        admin_name=message.from_user.full_name,
        reason=reason
    )

    if not result["success"]:
        await state.clear()

        await message.answer(
            "❌ Ремонт уже обработан.",
            reply_markup=admin_menu()
        )
        return

    await state.clear()

    await message.answer(
        "↩️ РЕМОНТ ВОЗВРАЩЕН МАСТЕРУ\n\n"
        f"Ремонт: {repair['repair_code']}\n"
        f"🚲 Велосипед: "
        f"№{repair['bike_number']}\n\n"
        f"Причина:\n{reason}",
        reply_markup=admin_menu()
    )

    # Уведомление мастеру
    try:
        await message.bot.send_message(
            chat_id=repair[
                "master_telegram_id"
            ],
            text=(
                "↩️ РЕМОНТ ВОЗВРАЩЕН\n\n"
                f"Ремонт: "
                f"{repair['repair_code']}\n"
                f"🚲 Велосипед: "
                f"№{repair['bike_number']}\n\n"
                f"Причина администратора:\n"
                f"{reason}\n\n"
                "Заявка снова находится "
                "в разделе «🔧 Мои ремонты».\n"
                "Исправьте данные и отправьте "
                "ремонт повторно."
            )
        )
    except Exception:
        pass


@router.callback_query(
    F.data == "admin_rejection_cancel"
)
async def rejection_cancel_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.clear()

    try:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    await callback.message.answer(
        "Возврат ремонта отменен.",
        reply_markup=admin_menu()
    )

    await callback.answer()