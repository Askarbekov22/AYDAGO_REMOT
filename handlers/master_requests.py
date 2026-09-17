from aiogram import (
    Router,
    F
)

from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardRemove
)

from aiogram.fsm.context import (
    FSMContext
)

from config import (
    MASTER_IDS,
    ADMIN_IDS
)

from states.master_request_states import (
    MasterRepairStates
)

from keyboards.main_menu import (
    master_menu
)

from keyboards.master_request_keyboards import (
    take_request_keyboard,
    resume_request_keyboard,
    master_repair_confirmation_keyboard
)

from database.db import (
    get_new_repair_requests,
    get_request_by_id,
    assign_request_to_master,
    create_repair_from_request,
    get_master_requests
)

from utils.master_repair_parser import (
    parse_master_repair
)


router = Router()


# =========================================================
# ШАБЛОН МАСТЕРА
# =========================================================

MASTER_REPAIR_TEMPLATE = """Тип ремонта: с запчастью / без запчасти
Запчасть:
Количество:
Источник: склад / донор
Номер донора:
Описание:"""


# =========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================================

def is_master(
    telegram_id: int
):
    return telegram_id in MASTER_IDS


def format_money(
    value
):
    try:
        return f"{float(value or 0):,.0f}"
    except (
        ValueError,
        TypeError
    ):
        return "0"


def payment_text(
    request: dict
):
    status = request.get(
        "client_payment_status",
        "unpaid"
    )

    expected = float(
        request.get(
            "expected_amount",
            0
        ) or 0
    )

    paid = float(
        request.get(
            "paid_amount",
            0
        ) or 0
    )

    if status == "paid":

        if paid > 0:
            return (
                "✅ ОПЛАЧЕНО\n"
                f"Получено: "
                f"{format_money(paid)} сом"
            )

        return "✅ ОПЛАЧЕНО"

    if status == "partial":

        debt = max(
            expected - paid,
            0
        )

        text = (
            "🟡 ЧАСТИЧНО ОПЛАЧЕНО\n"
            f"Получено: "
            f"{format_money(paid)} сом"
        )

        if expected > 0:
            text += (
                f"\nК оплате: "
                f"{format_money(expected)} сом"
                f"\nОстаток: "
                f"{format_money(debt)} сом"
            )

        return text

    if expected > 0:
        return (
            "🔴 НЕ ОПЛАЧЕНО\n"
            f"К оплате: "
            f"{format_money(expected)} сом"
        )

    return "🔴 НЕ ОПЛАЧЕНО"


def request_status_text(
    status: str
):
    statuses = {
        "new": "🆕 Новая",
        "in_work": "🔧 В работе",
        "awaiting_approval": "⏳ На подтверждении",
        "approved": "✅ Подтвержден",
        "rejected": "↩️ Возвращен",
        "cancelled": "❌ Отменен"
    }

    return statuses.get(
        status,
        status
    )


async def send_master_form(
    message: Message,
    state: FSMContext,
    request: dict
):
    await state.clear()

    await state.update_data(
        request_id=request["id"],
        request_code=request["request_code"],
        bike_number=request["bike_number"]
    )

    await state.set_state(
        MasterRepairStates.form
    )

    await message.answer(
        "🔧 РЕМОНТ ВЕЛОСИПЕДА\n\n"
        f"Заявка: "
        f"{request['request_code']}\n"
        f"🚲 Велосипед: "
        f"№{request['bike_number']}\n\n"
        f"💳 Оплата:\n"
        f"{payment_text(request)}\n\n"
        "Заполните один шаблон и отправьте его "
        "одним сообщением.\n\n"
        "Если запчасть не использовалась — "
        "поставьте «-» в ненужных полях.",
        reply_markup=ReplyKeyboardRemove()
    )

    # Шаблон отдельным сообщением,
    # чтобы мастер мог быстро скопировать.
    await message.answer(
        MASTER_REPAIR_TEMPLATE
    )


# =========================================================
# НОВЫЕ ЗАЯВКИ
# =========================================================

@router.message(
    F.text == "🆕 Новые заявки"
)
async def new_requests_handler(
    message: Message
):
    if not is_master(
        message.from_user.id
    ):
        return

    requests = (
        await get_new_repair_requests()
    )

    if not requests:
        await message.answer(
            "✅ Новых заявок сейчас нет.",
            reply_markup=master_menu()
        )
        return

    await message.answer(
        f"🆕 НОВЫЕ ЗАЯВКИ\n\n"
        f"Количество: {len(requests)}"
    )

    for request in requests:

        comment = (
            request.get("comment")
            or "Нет комментария"
        )

        text = (
            f"📋 {request['request_code']}\n\n"
            f"🚲 Велосипед: "
            f"№{request['bike_number']}\n\n"

            f"💳 Оплата:\n"
            f"{payment_text(request)}\n\n"

            f"📝 Комментарий:\n"
            f"{comment}\n\n"

            f"👤 Создал:\n"
            f"{request.get('creator_name') or '-'}"
        )

        await message.answer(
            text,
            reply_markup=take_request_keyboard(
                request["id"]
            )
        )


# =========================================================
# ВЗЯТЬ В РАБОТУ
# =========================================================

@router.callback_query(
    F.data.startswith(
        "take_request:"
    )
)
async def take_request_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    if not is_master(
        callback.from_user.id
    ):
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    try:
        request_id = int(
            callback.data.split(":")[1]
        )
    except (
        ValueError,
        IndexError
    ):
        await callback.answer(
            "Некорректная заявка.",
            show_alert=True
        )
        return

    success = (
        await assign_request_to_master(
            request_id=request_id,
            master_telegram_id=(
                callback.from_user.id
            ),
            master_name=(
                callback.from_user.full_name
            )
        )
    )

    if not success:
        await callback.answer(
            "Эту заявку уже взял другой мастер "
            "или она больше не новая.",
            show_alert=True
        )
        return

    request = await get_request_by_id(
        request_id
    )

    if not request:
        await callback.answer(
            "Заявка не найдена.",
            show_alert=True
        )
        return

    try:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    await callback.answer(
        "Заявка взята в работу."
    )

    await send_master_form(
        callback.message,
        state,
        request
    )


# =========================================================
# МОИ РЕМОНТЫ
# =========================================================

@router.message(
    F.text == "🔧 Мои ремонты"
)
async def my_repairs_handler(
    message: Message
):
    if not is_master(
        message.from_user.id
    ):
        return

    requests = await get_master_requests(
        message.from_user.id
    )

    if not requests:
        await message.answer(
            "🔧 У вас пока нет ремонтов.",
            reply_markup=master_menu()
        )
        return

    in_work = [
        request
        for request in requests
        if request.get("status")
        == "in_work"
    ]

    awaiting = [
        request
        for request in requests
        if request.get("status")
        == "awaiting_approval"
    ]

    approved = [
        request
        for request in requests
        if request.get("status")
        == "approved"
    ]

    rejected = [
        request
        for request in requests
        if request.get("status")
        == "rejected"
    ]

    await message.answer(
        "🔧 МОИ РЕМОНТЫ\n\n"
        f"🔧 В работе: {len(in_work)}\n"
        f"⏳ На подтверждении: "
        f"{len(awaiting)}\n"
        f"✅ Подтверждено: "
        f"{len(approved)}\n"
        f"↩️ Возвращено: "
        f"{len(rejected)}"
    )

    # =====================================================
    # В РАБОТЕ
    # =====================================================

    if in_work:

        await message.answer(
            "🔧 В РАБОТЕ"
        )

        for request in in_work:

            comment = (
                request.get("comment")
                or "Нет комментария"
            )

            text = (
                f"📋 "
                f"{request['request_code']}\n\n"

                f"🚲 Велосипед: "
                f"№{request['bike_number']}\n"

                f"Статус: "
                f"{request_status_text(request['status'])}"
                f"\n\n"

                f"💳 Оплата:\n"
                f"{payment_text(request)}\n\n"

                f"📝 Комментарий:\n"
                f"{comment}"
            )

            await message.answer(
                text,
                reply_markup=(
                    resume_request_keyboard(
                        request["id"]
                    )
                )
            )

    # =====================================================
    # НА ПОДТВЕРЖДЕНИИ
    # =====================================================

    if awaiting:

        await message.answer(
            "⏳ НА ПОДТВЕРЖДЕНИИ"
        )

        for request in awaiting:

            text = (
                f"📋 "
                f"{request['request_code']}\n\n"

                f"🚲 Велосипед: "
                f"№{request['bike_number']}\n"

                f"Статус: "
                f"⏳ Ожидает подтверждения "
                f"администратора\n\n"

                f"💳 Оплата:\n"
                f"{payment_text(request)}"
            )

            await message.answer(
                text
            )

    # =====================================================
    # ПОДТВЕРЖДЕННЫЕ
    # =====================================================

    if approved:

        await message.answer(
            "✅ ПОДТВЕРЖДЕННЫЕ"
        )

        for request in approved[:10]:

            await message.answer(
                f"✅ "
                f"{request['request_code']}\n"
                f"🚲 Велосипед: "
                f"№{request['bike_number']}\n\n"
                f"💳 "
                f"{payment_text(request)}"
            )

    # =====================================================
    # ВОЗВРАЩЕННЫЕ
    # =====================================================

    if rejected:

        await message.answer(
            "↩️ ВОЗВРАЩЕННЫЕ"
        )

        for request in rejected:

            await message.answer(
                f"↩️ "
                f"{request['request_code']}\n"
                f"🚲 Велосипед: "
                f"№{request['bike_number']}\n\n"
                "Ремонт возвращен "
                "администратором."
            )


# =========================================================
# ПРОДОЛЖИТЬ РЕМОНТ
# =========================================================

@router.callback_query(
    F.data.startswith(
        "resume_request:"
    )
)
async def resume_request_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    if not is_master(
        callback.from_user.id
    ):
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    try:
        request_id = int(
            callback.data.split(":")[1]
        )
    except (
        ValueError,
        IndexError
    ):
        await callback.answer(
            "Некорректная заявка.",
            show_alert=True
        )
        return

    request = await get_request_by_id(
        request_id
    )

    if not request:
        await callback.answer(
            "Заявка не найдена.",
            show_alert=True
        )
        return

    if (
        request.get(
            "assigned_master_id"
        )
        != callback.from_user.id
    ):
        await callback.answer(
            "Эта заявка принадлежит "
            "другому мастеру.",
            show_alert=True
        )
        return

    if request.get("status") != "in_work":
        await callback.answer(
            "Эта заявка уже не находится "
            "в работе.",
            show_alert=True
        )
        return

    await callback.answer()

    await send_master_form(
        callback.message,
        state,
        request
    )


# =========================================================
# ПОЛУЧЕНИЕ ШАБЛОНА
# =========================================================

@router.message(
    MasterRepairStates.form
)
async def master_repair_form_handler(
    message: Message,
    state: FSMContext
):
    if not is_master(
        message.from_user.id
    ):
        return

    if not message.text:
        await message.answer(
            "Отправьте заполненный "
            "шаблон текстом."
        )
        return

    parsed, errors = (
        parse_master_repair(
            message.text
        )
    )

    if errors:

        error_text = "\n".join(
            f"• {error}"
            for error in errors
        )

        await message.answer(
            "❌ В шаблоне есть ошибки:\n\n"
            f"{error_text}\n\n"
            "Исправьте и отправьте "
            "шаблон заново."
        )

        await message.answer(
            MASTER_REPAIR_TEMPLATE
        )

        return

    data = await state.get_data()

    bike_number = str(
        data["bike_number"]
    ).strip()

    donor = parsed.get(
        "donor_bike_number"
    )

    if (
        donor
        and str(donor).strip()
        == bike_number
    ):
        await message.answer(
            "❌ Велосипед не может быть "
            "донором для самого себя.\n\n"
            "Исправьте номер донора."
        )
        return

    await state.update_data(
        repair_type=parsed[
            "repair_type"
        ],
        part_name=parsed[
            "part_name"
        ],
        part_quantity=parsed[
            "part_quantity"
        ],
        source_type=parsed[
            "source_type"
        ],
        donor_bike_number=parsed[
            "donor_bike_number"
        ],
        description=parsed[
            "description"
        ]
    )

    await state.set_state(
        MasterRepairStates.bike_photo
    )

    await message.answer(
        "📷 Теперь сфотографируйте "
        "номер велосипеда.\n\n"
        "Номер на фотографии должен "
        "быть хорошо виден."
    )


# =========================================================
# ФОТО ВЕЛОСИПЕДА
# =========================================================

@router.message(
    MasterRepairStates.bike_photo,
    F.photo
)
async def master_bike_photo_handler(
    message: Message,
    state: FSMContext
):
    photo_file_id = (
        message.photo[-1].file_id
    )

    await state.update_data(
        bike_photo_file_id=photo_file_id
    )

    data = await state.get_data()

    request = await get_request_by_id(
        data["request_id"]
    )

    if not request:
        await state.clear()

        await message.answer(
            "❌ Заявка больше не найдена.",
            reply_markup=master_menu()
        )
        return

    if data["repair_type"] == "part":

        source_names = {
            "warehouse": "Склад",
            "donor": "Донор"
        }

        part_text = (
            f"Запчасть: "
            f"{data['part_name']}\n"
            f"Количество: "
            f"{data['part_quantity']}\n"
            f"Источник: "
            f"{source_names.get(data['source_type'], '-')}"
        )

        if data[
            "source_type"
        ] == "donor":

            part_text += (
                f"\nНомер донора: "
                f"{data['donor_bike_number']}"
            )

    else:
        part_text = (
            "Без использования запчасти"
        )

    await state.set_state(
        MasterRepairStates.confirm
    )

    await message.answer(
        "📋 ПРОВЕРЬТЕ РЕМОНТ\n\n"

        f"Заявка: "
        f"{request['request_code']}\n"

        f"🚲 Велосипед: "
        f"№{request['bike_number']}\n\n"

        f"💳 Оплата:\n"
        f"{payment_text(request)}\n\n"

        f"🔧 Работа:\n"
        f"{part_text}\n\n"

        f"📝 Описание:\n"
        f"{data['description']}\n\n"

        "📷 Фото номера велосипеда: "
        "добавлено",

        reply_markup=(
            master_repair_confirmation_keyboard()
        )
    )


@router.message(
    MasterRepairStates.bike_photo
)
async def master_bike_photo_invalid(
    message: Message
):
    await message.answer(
        "📷 Нужно отправить фотографию "
        "номера велосипеда."
    )


# =========================================================
# СОХРАНЕНИЕ РЕМОНТА
# =========================================================

@router.callback_query(
    MasterRepairStates.confirm,
    F.data == "master_repair_save"
)
async def master_repair_save_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    if not is_master(
        callback.from_user.id
    ):
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    data = await state.get_data()

    request = await get_request_by_id(
        data["request_id"]
    )

    if not request:
        await state.clear()

        await callback.message.answer(
            "❌ Заявка не найдена.",
            reply_markup=master_menu()
        )

        await callback.answer()
        return

    # Проверяем актуальный статус.
    if (
        request.get(
            "assigned_master_id"
        )
        != callback.from_user.id
        or request.get("status")
        != "in_work"
    ):
        await state.clear()

        await callback.message.answer(
            "❌ Заявка уже изменила статус "
            "или принадлежит другому мастеру.",
            reply_markup=master_menu()
        )

        await callback.answer()
        return

    try:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    result = await create_repair_from_request(
        request_id=data[
            "request_id"
        ],
        master_telegram_id=(
            callback.from_user.id
        ),
        master_name=(
            callback.from_user.full_name
        ),
        repair_type=data[
            "repair_type"
        ],
        description=data[
            "description"
        ],
        bike_photo_file_id=data[
            "bike_photo_file_id"
        ],
        part_name=data.get(
            "part_name"
        ),
        part_quantity=data.get(
            "part_quantity"
        ),
        source_type=data.get(
            "source_type"
        ),
        donor_bike_number=data.get(
            "donor_bike_number"
        )
    )

    if not result:
        await state.clear()

        await callback.message.answer(
            "❌ Не удалось сохранить ремонт.\n\n"
            "Возможно, заявка уже была "
            "обработана.",
            reply_markup=master_menu()
        )

        await callback.answer()
        return

    await state.clear()

    await callback.message.answer(
        "✅ РЕМОНТ ЗАВЕРШЕН\n\n"

        f"Ремонт: "
        f"{result['repair_code']}\n"

        f"Заявка: "
        f"{result['request_code']}\n"

        f"🚲 Велосипед: "
        f"№{result['bike_number']}\n\n"

        "⏳ Отправлено администратору "
        "на подтверждение.",

        reply_markup=master_menu()
    )

    # =====================================================
    # УВЕДОМЛЕНИЕ АДМИНИСТРАТОРОВ
    # =====================================================

    updated_request = (
        await get_request_by_id(
            data["request_id"]
        )
    )

    admin_text = (
        "🔔 РЕМОНТ НА ПОДТВЕРЖДЕНИЕ\n\n"

        f"Ремонт: "
        f"{result['repair_code']}\n"

        f"Заявка: "
        f"{result['request_code']}\n"

        f"🚲 Велосипед: "
        f"№{result['bike_number']}\n\n"

        f"👨‍🔧 Мастер:\n"
        f"{callback.from_user.full_name}\n\n"

        f"💳 Оплата:\n"
        f"{payment_text(updated_request)}\n\n"

        f"📝 Работа:\n"
        f"{data['description']}"
    )

    for admin_id in ADMIN_IDS:

        try:
            await callback.bot.send_photo(
                chat_id=admin_id,
                photo=data[
                    "bike_photo_file_id"
                ],
                caption=admin_text
            )

        except Exception:
            try:
                await callback.bot.send_message(
                    chat_id=admin_id,
                    text=admin_text
                )
            except Exception:
                pass

    await callback.answer()


# =========================================================
# ОТМЕНА ЗАПОЛНЕНИЯ
# =========================================================

@router.callback_query(
    F.data == "master_repair_cancel"
)
async def master_repair_cancel_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    if not is_master(
        callback.from_user.id
    ):
        return

    data = await state.get_data()

    await state.clear()

    try:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    await callback.message.answer(
        "❌ Заполнение ремонта прервано.\n\n"
        "Сама заявка остается за вами "
        "в разделе «🔧 Мои ремонты».\n"
        "Позже нажмите "
        "«▶️ Продолжить ремонт».",
        reply_markup=master_menu()
    )

    await callback.answer()