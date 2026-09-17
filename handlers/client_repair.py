from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext

from config import ADMIN_IDS

from states.repair_states import (
    ClientRepairStates
)

from keyboards.repair_keyboards import (
    client_confirmation_keyboard
)

from keyboards.main_menu import (
    master_menu
)

from database.db import (
    create_client_repair
)

from utils.repair_parser import (
    parse_client_form
)


router = Router()


CLIENT_TEMPLATE = """
Номер велосипеда:
Тип ремонта: с запчастью / без запчасти
Запчасть:
Количество:
Источник: склад / донор
Номер донора:
Описание:
Сумма оплаты:
""".strip()


@router.message(
    F.text == "💰 За счет клиента"
)
async def client_repair_start(
    message: Message,
    state: FSMContext
):
    await state.clear()

    await state.set_state(
        ClientRepairStates.form
    )

    await message.answer(
        "💰 РЕМОНТ ЗА СЧЕТ КЛИЕНТА\n\n"
        "1. Скопируйте шаблон из следующего сообщения.\n"
        "2. Заполните его одним сообщением.\n"
        "3. Если ремонт без запчасти — "
        "в ненужных полях поставьте «-».\n\n"
        "После этого бот отдельно попросит:\n"
        "📷 фото номера велосипеда\n"
        "📷 фото оплаты",
        reply_markup=ReplyKeyboardRemove()
    )

    await message.answer(
        CLIENT_TEMPLATE
    )


@router.message(
    ClientRepairStates.form
)
async def client_form_handler(
    message: Message,
    state: FSMContext
):
    if not message.text:
        await message.answer(
            "Нужно отправить заполненный "
            "шаблон текстом."
        )
        return

    data, errors = parse_client_form(
        message.text
    )

    if errors:
        error_text = "\n".join(
            f"• {error}"
            for error in errors
        )

        await message.answer(
            "❌ Есть ошибки:\n\n"
            f"{error_text}\n\n"
            "Исправьте данные и отправьте "
            "заполненный шаблон заново."
        )

        await message.answer(
            CLIENT_TEMPLATE
        )

        return

    await state.update_data(
        **data
    )

    await state.set_state(
        ClientRepairStates.bike_photo
    )

    await message.answer(
        f"✅ Данные приняты.\n\n"
        f"🚲 Велосипед №{data['bike_number']}\n"
        f"💵 Сумма: {data['amount']:,.0f} сом\n\n"
        "Теперь отправьте фото номера велосипеда."
    )


@router.message(
    ClientRepairStates.bike_photo,
    F.photo
)
async def client_bike_photo(
    message: Message,
    state: FSMContext
):
    photo = message.photo[-1]

    await state.update_data(
        bike_photo_file_id=photo.file_id
    )

    await state.set_state(
        ClientRepairStates.payment_photo
    )

    await message.answer(
        "✅ Фото велосипеда принято.\n\n"
        "Теперь отправьте 📷 фото оплаты."
    )


@router.message(
    ClientRepairStates.bike_photo
)
async def client_bike_photo_invalid(
    message: Message
):
    await message.answer(
        "📷 Нужно отправить фотографию "
        "номера велосипеда."
    )


@router.message(
    ClientRepairStates.payment_photo,
    F.photo
)
async def client_payment_photo(
    message: Message,
    state: FSMContext
):
    photo = message.photo[-1]

    await state.update_data(
        payment_photo_file_id=photo.file_id
    )

    data = await state.get_data()

    text = (
        "🔧 ПРОВЕРЬТЕ РЕМОНТ\n\n"
        f"🚲 Велосипед: №{data['bike_number']}\n"
        "💰 За счет клиента\n"
    )

    if data["repair_type"] == "part":
        text += (
            "\n🔩 С заменой запчасти\n"
            f"Запчасть: {data['part_name']}\n"
            f"Количество: {data['part_quantity']}\n"
        )

        if data["source_type"] == "warehouse":
            text += (
                "Источник: 📦 Со склада\n"
            )

        else:
            text += (
                "Источник: 🚲 Донор\n"
                f"Велосипед-донор: "
                f"№{data['donor_bike_number']}\n"
            )

    else:
        text += (
            "\n🛠 Без замены запчасти\n"
        )

    text += (
        f"\n📝 Работа:\n"
        f"{data['description']}\n\n"
        f"💵 Оплата: "
        f"{data['amount']:,.0f} сом"
    )

    await state.set_state(
        ClientRepairStates.confirm
    )

    await message.answer_photo(
        photo=data[
            "bike_photo_file_id"
        ],
        caption=text,
        reply_markup=(
            client_confirmation_keyboard()
        )
    )


@router.message(
    ClientRepairStates.payment_photo
)
async def client_payment_photo_invalid(
    message: Message
):
    await message.answer(
        "📷 Нужно отправить фотографию оплаты."
    )


@router.callback_query(
    ClientRepairStates.confirm,
    F.data == "client_repair_save"
)
async def client_repair_save(
    callback: CallbackQuery,
    state: FSMContext
):
    try:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    data = await state.get_data()

    result = await create_client_repair(
        master_telegram_id=callback.from_user.id,
        bike_number=data["bike_number"],
        repair_type=data["repair_type"],
        description=data["description"],
        bike_photo_file_id=data[
            "bike_photo_file_id"
        ],
        amount=data["amount"],
        payment_photo_file_id=data[
            "payment_photo_file_id"
        ],
        part_name=data.get("part_name"),
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

    repair_code = result[
        "repair_code"
    ]

    admin_text = (
        "🔔 НОВЫЙ КЛИЕНТСКИЙ РЕМОНТ\n\n"
        f"🆔 {repair_code}\n"
        f"👨‍🔧 Мастер: "
        f"{callback.from_user.full_name}\n"
        f"🚲 Велосипед: "
        f"№{data['bike_number']}\n"
        "💰 За счет клиента\n"
    )

    if data["repair_type"] == "part":
        admin_text += (
            "\n🔩 С заменой запчасти\n"
            f"Запчасть: {data['part_name']}\n"
            f"Количество: "
            f"{data['part_quantity']}\n"
        )

        if data["source_type"] == "warehouse":
            admin_text += (
                "Источник: 📦 Со склада\n"
            )

        else:
            admin_text += (
                "Источник: 🚲 Донор\n"
                f"Донор: №"
                f"{data['donor_bike_number']}\n"
            )

    else:
        admin_text += (
            "\n🛠 Без замены запчасти\n"
        )

    admin_text += (
        f"\n📝 Работа:\n"
        f"{data['description']}\n\n"
        f"💵 Оплата: "
        f"{data['amount']:,.0f} сом\n\n"
        "⏳ Ожидает подтверждения"
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

            await callback.bot.send_photo(
                chat_id=admin_id,
                photo=data[
                    "payment_photo_file_id"
                ],
                caption=(
                    f"💳 Фото оплаты — "
                    f"{repair_code}"
                )
            )

        except Exception as error:
            print(
                f"Ошибка отправки админу "
                f"{admin_id}: {error}"
            )

    await state.clear()

    await callback.message.answer(
        f"✅ Ремонт {repair_code} сохранен.\n\n"
        f"💵 Оплата: "
        f"{data['amount']:,.0f} сом\n"
        "⏳ Ожидает подтверждения "
        "администратора.",
        reply_markup=master_menu()
    )

    await callback.answer()


@router.callback_query(
    ClientRepairStates.confirm,
    F.data == "client_repair_cancel"
)
async def client_repair_cancel(
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
        "❌ Ремонт отменен.",
        reply_markup=master_menu()
    )

    await callback.answer()