import aiosqlite

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
    ADMIN_IDS,
    DATABASE_PATH
)

from states.master_create_repair_states import (
    MasterCreateRepairStates
)

from keyboards.master_create_repair_keyboards import (
    master_create_confirmation_keyboard
)

from keyboards.main_menu import (
    master_menu
)

from database.db import (
    create_master_repair_request,
    add_request_payment,
    create_repair_from_request
)

from utils.master_create_repair_parser import (
    parse_master_created_repair
)


router = Router()


# =========================================================
# ШАБЛОН
# =========================================================

MASTER_CREATE_TEMPLATE = """Номер велосипеда:
За чей счет: клиент / компания
Тип ремонта: с запчастью / без запчасти
Запчасть:
Количество:
Источник: склад / донор
Номер донора:
Описание:
Сумма оплаты:
Способ оплаты: QR / наличные / перевод
Причина ремонта:"""


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


def source_text(
    value
):
    names = {
        "warehouse": "📦 Со склада",
        "donor": "🚲 С донора"
    }

    return names.get(
        value,
        "-"
    )


def payment_method_text(
    value
):
    names = {
        "qr": "📱 QR",
        "cash": "💵 Наличные",
        "transfer": "🏦 Перевод"
    }

    return names.get(
        value,
        "-"
    )


# =========================================================
# ПРИВОДИМ REPAIRS К ПРАВИЛЬНОМУ PAYER_TYPE
# =========================================================

async def update_created_repair_financing(
    repair_id: int,
    payer_type: str,
    company_reason: str | None
):
    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        await db.execute("""
            UPDATE repairs

            SET
                payer_type = ?,
                company_reason = ?,
                updated_at = CURRENT_TIMESTAMP

            WHERE id = ?
        """, (
            payer_type,
            company_reason,
            repair_id
        ))

        await db.commit()


# =========================================================
# КАРТОЧКА
# =========================================================

def build_confirmation_text(
    data: dict
):
    if data["payer_type"] == "company":

        payer = (
            "🏢 За счет компании"
        )

        payment = (
            "Оплата клиента не требуется"
        )

    else:

        payer = (
            "👤 За счет клиента"
        )

        if data[
            "payment_amount"
        ] > 0:

            payment = (
                f"💵 Оплата: "
                f"{format_money(data['payment_amount'])} сом\n"
                f"Способ: "
                f"{payment_method_text(data['payment_method'])}"
            )

        else:
            payment = (
                "🔴 Не оплачено"
            )

    if (
        data["repair_type"]
        == "part"
    ):

        repair_text = (
            "🔩 С заменой запчасти\n"
            f"Запчасть: "
            f"{data['part_name']}\n"
            f"Количество: "
            f"{data['part_quantity']}\n"
            f"Источник: "
            f"{source_text(data['source_type'])}"
        )

        if (
            data["source_type"]
            == "donor"
        ):
            repair_text += (
                "\nНомер донора: "
                f"№{data['donor_bike_number']}"
            )

    else:
        repair_text = (
            "🔧 Без замены запчасти"
        )

    company_reason_text = ""

    if data["payer_type"] == "company":
        company_reason_text = (
            "\n\n🏢 Причина ремонта:\n"
            f"{data['company_reason']}"
        )

    return (
        "🔧 ПРОВЕРЬТЕ РЕМОНТ\n\n"

        f"🚲 Велосипед: "
        f"№{data['bike_number']}\n"

        f"💰 {payer}\n\n"

        f"{repair_text}\n\n"

        f"📝 Работа:\n"
        f"{data['description']}\n\n"

        f"{payment}"
        f"{company_reason_text}"
    )


# =========================================================
# НАЧАЛО
# =========================================================

@router.message(
    F.text == "➕ Создать ремонт"
)
async def master_create_start(
    message: Message,
    state: FSMContext
):
    if not is_master(
        message.from_user.id
    ):
        return

    await state.clear()

    await state.set_state(
        MasterCreateRepairStates.form
    )

    await message.answer(
        "➕ СОЗДАНИЕ РЕМОНТА\n\n"
        "Заполните всю карточку "
        "ОДНИМ сообщением.\n\n"

        "Если поле не требуется — "
        "поставьте «-».\n\n"

        "Если клиент НЕ оплатил ремонт:\n"
        "• Сумма оплаты: 0\n"
        "• Способ оплаты: -\n\n"

        "Если ремонт за счет компании:\n"
        "• Сумма оплаты: -\n"
        "• Способ оплаты: -\n"
        "• обязательно укажите "
        "причину ремонта.",

        reply_markup=ReplyKeyboardRemove()
    )

    # Отдельное сообщение,
    # чтобы мастер мог легко скопировать.
    await message.answer(
        MASTER_CREATE_TEMPLATE
    )


# =========================================================
# ПРИНИМАЕМ ВЕСЬ ШАБЛОН
# =========================================================

@router.message(
    MasterCreateRepairStates.form
)
async def master_form_handler(
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
        parse_master_created_repair(
            message.text
        )
    )

    if errors:

        error_text = "\n".join(
            f"• {error}"
            for error in errors
        )

        await message.answer(
            "❌ В карточке есть ошибки:\n\n"
            f"{error_text}\n\n"
            "Исправьте карточку и "
            "отправьте ее снова."
        )

        await message.answer(
            MASTER_CREATE_TEMPLATE
        )

        return

    # =====================================================
    # ПРОВЕРКА ДОНОРА
    # =====================================================

    if (
        parsed.get(
            "donor_bike_number"
        )
        and str(
            parsed[
                "donor_bike_number"
            ]
        ).strip()
        == str(
            parsed["bike_number"]
        ).strip()
    ):
        await message.answer(
            "❌ Велосипед не может "
            "быть донором для самого себя."
        )
        return

    await state.update_data(
        **parsed
    )

    await state.set_state(
        MasterCreateRepairStates.bike_photo
    )

    # =====================================================
    # КОРОТКОЕ ПОДТВЕРЖДЕНИЕ
    # =====================================================

    if (
        parsed["payer_type"]
        == "client"
    ):
        amount_text = (
            f"{format_money(parsed['payment_amount'])} сом"
            if parsed[
                "payment_amount"
            ] > 0
            else "Не оплачено"
        )

    else:
        amount_text = (
            "За счет компании"
        )

    await message.answer(
        "✅ Данные приняты.\n\n"

        f"🚲 Велосипед "
        f"№{parsed['bike_number']}\n"

        f"💵 {amount_text}\n\n"

        "Теперь отправьте 📷 "
        "фото номера велосипеда."
    )


# =========================================================
# ФОТО ВЕЛОСИПЕДА
# =========================================================

@router.message(
    MasterCreateRepairStates.bike_photo,
    F.photo
)
async def master_bike_photo(
    message: Message,
    state: FSMContext
):
    bike_photo_file_id = (
        message.photo[-1].file_id
    )

    await state.update_data(
        bike_photo_file_id=(
            bike_photo_file_id
        )
    )

    data = await state.get_data()

    # =====================================================
    # ЕСЛИ КЛИЕНТ ОПЛАТИЛ —
    # НУЖНО ФОТО ОПЛАТЫ
    # =====================================================

    if (
        data["payer_type"]
        == "client"
        and float(
            data.get(
                "payment_amount",
                0
            )
        ) > 0
    ):

        await state.set_state(
            MasterCreateRepairStates.payment_photo
        )

        await message.answer(
            "✅ Фото велосипеда принято.\n\n"
            "Теперь отправьте 📷 "
            "фото оплаты."
        )

        return

    # =====================================================
    # ЕСЛИ ОПЛАТЫ НЕТ ИЛИ ПЛАТИТ КОМПАНИЯ
    # =====================================================

    await state.set_state(
        MasterCreateRepairStates.confirm
    )

    await message.answer_photo(
        photo=bike_photo_file_id,
        caption=build_confirmation_text(
            data
        ),
        reply_markup=(
            master_create_confirmation_keyboard()
        )
    )


@router.message(
    MasterCreateRepairStates.bike_photo
)
async def master_bike_photo_invalid(
    message: Message
):
    await message.answer(
        "📷 Нужно отправить "
        "фотографию номера велосипеда."
    )


# =========================================================
# ФОТО ОПЛАТЫ
# =========================================================

@router.message(
    MasterCreateRepairStates.payment_photo,
    F.photo
)
async def master_payment_photo(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        payment_photo_file_id=(
            message.photo[-1].file_id
        )
    )

    data = await state.get_data()

    await state.set_state(
        MasterCreateRepairStates.confirm
    )

    # Показываем именно фотографию
    # велосипеда + карточку ремонта.
    await message.answer_photo(
        photo=data[
            "bike_photo_file_id"
        ],
        caption=build_confirmation_text(
            data
        ),
        reply_markup=(
            master_create_confirmation_keyboard()
        )
    )


@router.message(
    MasterCreateRepairStates.payment_photo
)
async def master_payment_photo_invalid(
    message: Message
):
    await message.answer(
        "📷 Нужно отправить "
        "фотографию оплаты."
    )


# =========================================================
# СОХРАНЕНИЕ
# =========================================================

@router.callback_query(
    MasterCreateRepairStates.confirm,
    F.data == "master_create:save"
)
async def save_master_repair(
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

    try:
        # =================================================
        # 1. СОЗДАЕМ ЗАЯВКУ
        # =================================================

        request_result = (
            await create_master_repair_request(
                bike_number=data[
                    "bike_number"
                ],
                master_telegram_id=(
                    callback.from_user.id
                ),
                master_name=(
                    callback.from_user.full_name
                ),
                payer_type=data[
                    "payer_type"
                ],
                payment_status=data[
                    "payment_status"
                ],
                expected_amount=data[
                    "payment_amount"
                ],
                company_reason=data.get(
                    "company_reason"
                )
            )
        )

        request_id = (
            request_result["id"]
        )

        # =================================================
        # 2. ОПЛАТА
        # =================================================

        if (
            data["payer_type"]
            == "client"
            and data[
                "payment_status"
            ] == "paid"
        ):

            await add_request_payment(
                request_id=request_id,
                amount=data[
                    "payment_amount"
                ],
                payment_method=data[
                    "payment_method"
                ],
                accepted_by=(
                    callback.from_user.id
                ),
                accepted_by_name=(
                    callback.from_user.full_name
                ),
                payment_photo_file_id=data[
                    "payment_photo_file_id"
                ]
            )

        # =================================================
        # 3. СОЗДАЕМ РЕМОНТ
        # =================================================

        repair_result = (
            await create_repair_from_request(
                request_id=request_id,

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
        )

        if not repair_result:
            raise RuntimeError(
                "Не удалось создать ремонт"
            )

        # =================================================
        # 4. ИСПРАВЛЯЕМ PAYER_TYPE
        # =================================================

        await update_created_repair_financing(
            repair_id=repair_result[
                "repair_id"
            ],
            payer_type=data[
                "payer_type"
            ],
            company_reason=data.get(
                "company_reason"
            )
        )

        try:
            await callback.message.edit_reply_markup(
                reply_markup=None
            )
        except Exception:
            pass

        await state.clear()

        # =================================================
        # 5. МАСТЕРУ
        # =================================================

        await callback.message.answer(
            "✅ РЕМОНТ СОХРАНЕН\n\n"

            f"🔧 "
            f"{repair_result['repair_code']}\n"

            f"🚲 Велосипед "
            f"№{data['bike_number']}\n\n"

            "⏳ Отправлен администратору "
            "на подтверждение.",

            reply_markup=master_menu()
        )

        # =================================================
        # 6. АДМИНИСТРАТОРУ
        # =================================================

        admin_text = (
            "🔔 НОВЫЙ РЕМОНТ "
            "НА ПОДТВЕРЖДЕНИЕ\n\n"

            f"🔧 "
            f"{repair_result['repair_code']}\n"

            f"🚲 Велосипед: "
            f"№{data['bike_number']}\n"

            f"👨‍🔧 Мастер: "
            f"{callback.from_user.full_name}\n\n"

            f"{build_confirmation_text(data)}"
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
                    "[ADMIN NOTIFICATION ERROR]",
                    error
                )

        await callback.answer(
            "Ремонт сохранен."
        )

    except Exception as error:
        print(
            "[MASTER CREATE ERROR]",
            error
        )

        await callback.message.answer(
            "❌ Не удалось сохранить ремонт.\n\n"
            f"Ошибка:\n{error}"
        )

        await callback.answer()


# =========================================================
# ОТМЕНА
# =========================================================

@router.callback_query(
    F.data == "master_create:cancel"
)
async def cancel_master_repair(
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
        "❌ Создание ремонта отменено.",
        reply_markup=master_menu()
    )

    await callback.answer()