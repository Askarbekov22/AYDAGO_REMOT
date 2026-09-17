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

from states.request_states import (
    RepairRequestStates
)

from keyboards.request_keyboards import (
    payment_status_keyboard,
    payment_method_keyboard,
    request_confirmation_keyboard
)

from keyboards.main_menu import (
    rental_staff_menu
)

from database.db import (
    create_repair_request,
    add_request_payment
)


router = Router()


# =========================================================
# СТАРТ
# =========================================================

@router.message(
    F.text == "➕ Создать заявку на ремонт"
)
async def create_request_start(
    message: Message,
    state: FSMContext
):
    await state.clear()

    await state.set_state(
        RepairRequestStates.bike_number
    )

    await message.answer(
        "➕ НОВАЯ ЗАЯВКА НА РЕМОНТ\n\n"
        "Введите номер велосипеда:",
        reply_markup=ReplyKeyboardRemove()
    )


# =========================================================
# НОМЕР ВЕЛОСИПЕДА
# =========================================================

@router.message(
    RepairRequestStates.bike_number
)
async def request_bike_number(
    message: Message,
    state: FSMContext
):
    if not message.text:
        await message.answer(
            "Введите номер велосипеда."
        )

        return

    bike_number = (
        message.text.strip()
    )

    if not bike_number:
        await message.answer(
            "Номер велосипеда пустой."
        )

        return

    await state.update_data(
        bike_number=bike_number
    )

    await state.set_state(
        RepairRequestStates.payment_status
    )

    await message.answer(
        f"🚲 Велосипед №{bike_number}\n\n"
        "Клиент уже оплатил ремонт?",
        reply_markup=payment_status_keyboard()
    )


# =========================================================
# ОПЛАЧЕНО
# =========================================================

@router.callback_query(
    RepairRequestStates.payment_status,
    F.data == "request_paid"
)
async def request_paid(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.update_data(
        payment_status="paid"
    )

    await state.set_state(
        RepairRequestStates.amount
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        "💵 Введите сумму оплаты:"
    )

    await callback.answer()


# =========================================================
# НЕ ОПЛАЧЕНО
# =========================================================

@router.callback_query(
    RepairRequestStates.payment_status,
    F.data == "request_unpaid"
)
async def request_unpaid(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.update_data(
        payment_status="unpaid",
        amount=0,
        payment_method=None,
        payment_photo_file_id=None
    )

    await state.set_state(
        RepairRequestStates.comment
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        "📝 Комментарий для мастера.\n\n"
        "Если комментария нет — отправьте «-»."
    )

    await callback.answer()


# =========================================================
# СУММА
# =========================================================

@router.message(
    RepairRequestStates.amount
)
async def request_amount(
    message: Message,
    state: FSMContext
):
    if not message.text:
        await message.answer(
            "Введите сумму числом."
        )

        return

    raw = (
        message.text
        .replace(" ", "")
        .replace(",", ".")
    )

    try:
        amount = float(raw)

        if amount <= 0:
            raise ValueError

    except ValueError:
        await message.answer(
            "Введите корректную сумму.\n"
            "Например: 700"
        )

        return

    await state.update_data(
        amount=amount
    )

    await state.set_state(
        RepairRequestStates.payment_method
    )

    await message.answer(
        "Выберите способ оплаты:",
        reply_markup=payment_method_keyboard()
    )


# =========================================================
# СПОСОБ ОПЛАТЫ
# =========================================================

async def choose_payment_method(
    callback: CallbackQuery,
    state: FSMContext,
    method: str
):
    await state.update_data(
        payment_method=method
    )

    await state.set_state(
        RepairRequestStates.payment_photo
    )

    await callback.message.edit_reply_markup(
        reply_markup=None
    )

    await callback.message.answer(
        "📷 Отправьте фото подтверждения оплаты."
    )

    await callback.answer()


@router.callback_query(
    RepairRequestStates.payment_method,
    F.data == "payment_qr"
)
async def payment_qr(
    callback: CallbackQuery,
    state: FSMContext
):
    await choose_payment_method(
        callback,
        state,
        "qr"
    )


@router.callback_query(
    RepairRequestStates.payment_method,
    F.data == "payment_cash"
)
async def payment_cash(
    callback: CallbackQuery,
    state: FSMContext
):
    await choose_payment_method(
        callback,
        state,
        "cash"
    )


@router.callback_query(
    RepairRequestStates.payment_method,
    F.data == "payment_transfer"
)
async def payment_transfer(
    callback: CallbackQuery,
    state: FSMContext
):
    await choose_payment_method(
        callback,
        state,
        "transfer"
    )


# =========================================================
# ФОТО ОПЛАТЫ
# =========================================================

@router.message(
    RepairRequestStates.payment_photo,
    F.photo
)
async def request_payment_photo(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        payment_photo_file_id=(
            message.photo[-1].file_id
        )
    )

    await state.set_state(
        RepairRequestStates.comment
    )

    await message.answer(
        "✅ Фото принято.\n\n"
        "Добавьте комментарий для мастера.\n"
        "Если комментария нет — отправьте «-»."
    )


@router.message(
    RepairRequestStates.payment_photo
)
async def payment_photo_invalid(
    message: Message
):
    await message.answer(
        "📷 Отправьте именно фотографию."
    )


# =========================================================
# КОММЕНТАРИЙ
# =========================================================

@router.message(
    RepairRequestStates.comment
)
async def request_comment(
    message: Message,
    state: FSMContext
):
    if not message.text:
        await message.answer(
            "Введите комментарий или «-»."
        )

        return

    comment = message.text.strip()

    if comment == "-":
        comment = ""

    await state.update_data(
        comment=comment
    )

    data = await state.get_data()

    if data["payment_status"] == "paid":

        methods = {
            "qr": "📱 QR",
            "cash": "💵 Наличные",
            "transfer": "🏦 Перевод"
        }

        payment_text = (
            "✅ ОПЛАЧЕНО\n"
            f"Сумма: "
            f"{data['amount']:,.0f} сом\n"
            f"Способ: "
            f"{methods.get(data['payment_method'], '-')}"
        )

    else:
        payment_text = (
            "🔴 НЕ ОПЛАЧЕНО"
        )

    await state.set_state(
        RepairRequestStates.confirm
    )

    await message.answer(
        "📋 ПРОВЕРЬТЕ ЗАЯВКУ\n\n"
        f"🚲 Велосипед: "
        f"№{data['bike_number']}\n\n"
        f"💳 {payment_text}\n\n"
        f"📝 Комментарий:\n"
        f"{comment or 'Нет комментария'}",
        reply_markup=request_confirmation_keyboard()
    )


# =========================================================
# СОХРАНЕНИЕ
# =========================================================

@router.callback_query(
    RepairRequestStates.confirm,
    F.data == "request_save"
)
async def save_request(
    callback: CallbackQuery,
    state: FSMContext
):
    data = await state.get_data()

    try:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    try:
        print("")
        print(
            "[REQUEST] Начинаем сохранение заявки"
        )

        result = await create_repair_request(
            bike_number=data["bike_number"],
            created_by=callback.from_user.id,
            creator_name=callback.from_user.full_name,
            payment_status=data["payment_status"],
            expected_amount=data.get(
                "amount",
                0
            ),
            paid_amount=0,
            comment=data.get(
                "comment"
            )
        )

        if not result:
            raise RuntimeError(
                "create_repair_request "
                "не вернул результат"
            )

        request_id = result["id"]
        request_code = (
            result["request_code"]
        )

        print(
            f"[REQUEST] Заявка создана: "
            f"{request_code}"
        )

        if data["payment_status"] == "paid":

            await add_request_payment(
                request_id=request_id,
                amount=data["amount"],
                payment_method=data[
                    "payment_method"
                ],
                accepted_by=callback.from_user.id,
                accepted_by_name=(
                    callback.from_user.full_name
                ),
                payment_photo_file_id=data[
                    "payment_photo_file_id"
                ]
            )

        await state.clear()

        if data["payment_status"] == "paid":

            payment_text = (
                "✅ ОПЛАЧЕНО\n"
                f"{data['amount']:,.0f} сом"
            )

        else:
            payment_text = (
                "🔴 НЕ ОПЛАЧЕНО"
            )

        await callback.message.answer(
            f"✅ Заявка {request_code} создана.\n\n"
            f"🚲 Велосипед: "
            f"№{data['bike_number']}\n\n"
            f"{payment_text}\n\n"
            "Заявка доступна мастерам.",
            reply_markup=rental_staff_menu()
        )

    except Exception as error:

        print(
            f"[REQUEST] ❌ Ошибка: "
            f"{error}"
        )

        await callback.message.answer(
            "❌ Не удалось сохранить заявку.\n\n"
            f"Ошибка:\n{error}\n\n"
            "Заявка НЕ создана."
        )

    await callback.answer()


# =========================================================
# ОТМЕНА
# =========================================================

@router.callback_query(
    F.data == "request_cancel"
)
async def cancel_request(
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
        "❌ Создание заявки отменено.",
        reply_markup=rental_staff_menu()
    )

    await callback.answer()