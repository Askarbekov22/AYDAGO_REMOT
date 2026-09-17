from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext

from config import ADMIN_IDS

from states.repair_states import (
    CompanyRepairStates
)

from keyboards.repair_keyboards import (
    confirmation_keyboard
)

from keyboards.main_menu import (
    master_menu
)

from database.db import (
    create_company_repair
)

from utils.repair_parser import (
    parse_company_form
)


router = Router()


COMPANY_TEMPLATE = """
Скопируйте шаблон и заполните:

Номер велосипеда:
Тип ремонта: с запчастью / без запчасти
Запчасть:
Количество:
Источник: склад / донор
Номер донора:
Описание:
Причина:
""".strip()


@router.message(
    F.text == "🏢 За счет компании"
)
async def company_repair_start(
    message: Message,
    state: FSMContext
):
    await state.clear()

    await state.set_state(
        CompanyRepairStates.form
    )

    await message.answer(
        "🏢 РЕМОНТ ЗА СЧЕТ КОМПАНИИ\n\n"
        "Заполните всё одним сообщением.\n\n"
        f"{COMPANY_TEMPLATE}\n\n"
        "Если ремонт без запчасти, "
        "в ненужных полях поставьте «-».\n\n"
        "Пример:\n\n"
        "Номер велосипеда: 301\n"
        "Тип ремонта: без запчасти\n"
        "Запчасть: -\n"
        "Количество: -\n"
        "Источник: -\n"
        "Номер донора: -\n"
        "Описание: Ремонт багажника\n"
        "Причина: Естественный износ",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(
    CompanyRepairStates.form
)
async def company_form_handler(
    message: Message,
    state: FSMContext
):
    if not message.text:
        await message.answer(
            "Нужно отправить заполненный "
            "шаблон текстом."
        )
        return

    data, errors = parse_company_form(
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
            "Исправьте шаблон и отправьте "
            "его заново целиком.\n\n"
            f"{COMPANY_TEMPLATE}"
        )
        return

    await state.update_data(
        **data
    )

    await state.set_state(
        CompanyRepairStates.bike_photo
    )

    await message.answer(
        f"✅ Данные приняты.\n\n"
        f"🚲 Велосипед №"
        f"{data['bike_number']}\n\n"
        "Теперь отправьте фото номера "
        "велосипеда."
    )


@router.message(
    CompanyRepairStates.bike_photo,
    F.photo
)
async def company_bike_photo(
    message: Message,
    state: FSMContext
):
    photo = message.photo[-1]

    await state.update_data(
        bike_photo_file_id=photo.file_id
    )

    data = await state.get_data()

    text = (
        "🔧 ПРОВЕРЬТЕ РЕМОНТ\n\n"
        f"🚲 Велосипед: "
        f"№{data['bike_number']}\n"
        "🏢 За счет компании\n"
    )

    if data["repair_type"] == "part":
        text += (
            "\n🔩 С заменой запчасти\n"
            f"Запчасть: "
            f"{data['part_name']}\n"
            f"Количество: "
            f"{data['part_quantity']}\n"
        )

        if (
            data["source_type"]
            == "warehouse"
        ):
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
        f"📌 Причина:\n"
        f"{data['company_reason']}"
    )

    await state.set_state(
        CompanyRepairStates.confirm
    )

    await message.answer_photo(
        photo=data["bike_photo_file_id"],
        caption=text,
        reply_markup=confirmation_keyboard()
    )


@router.message(
    CompanyRepairStates.bike_photo
)
async def company_bike_photo_invalid(
    message: Message
):
    await message.answer(
        "📷 Нужно отправить фотографию "
        "номера велосипеда."
    )


@router.callback_query(
    CompanyRepairStates.confirm,
    F.data == "company_repair_save"
)
async def company_repair_save(
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

    result = await create_company_repair(
        master_telegram_id=(
            callback.from_user.id
        ),
        bike_number=data[
            "bike_number"
        ],
        repair_type=data[
            "repair_type"
        ],
        description=data[
            "description"
        ],
        company_reason=data[
            "company_reason"
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

    repair_code = result[
        "repair_code"
    ]

    admin_text = (
        "🔔 НОВЫЙ РЕМОНТ\n\n"
        f"🆔 {repair_code}\n"
        f"👨‍🔧 Мастер: "
        f"{callback.from_user.full_name}\n"
        f"🚲 Велосипед: "
        f"№{data['bike_number']}\n"
        "🏢 За счет компании\n"
    )

    if data["repair_type"] == "part":
        admin_text += (
            "\n🔩 С заменой запчасти\n"
            f"Запчасть: "
            f"{data['part_name']}\n"
            f"Количество: "
            f"{data['part_quantity']}\n"
        )

        if (
            data["source_type"]
            == "warehouse"
        ):
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
        f"📌 Причина:\n"
        f"{data['company_reason']}\n\n"
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

        except Exception as error:
            print(
                f"Ошибка отправки админу "
                f"{admin_id}: {error}"
            )

    await state.clear()

    await callback.message.answer(
        f"✅ Ремонт {repair_code} сохранен.\n\n"
        "⏳ Ожидает подтверждения "
        "администратора.",
        reply_markup=master_menu()
    )

    await callback.answer()


@router.callback_query(
    CompanyRepairStates.confirm,
    F.data == "company_repair_cancel"
)
async def company_repair_cancel(
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