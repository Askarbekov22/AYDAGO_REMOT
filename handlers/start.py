from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from config import (
    ADMIN_IDS,
    MASTER_IDS,
    RENTAL_STAFF_IDS
)

from database.db import save_user

from keyboards.main_menu import (
    admin_menu,
    master_menu,
    rental_staff_menu
)


router = Router()


@router.message(CommandStart())
async def start_handler(
    message: Message
):
    user_id = message.from_user.id
    full_name = message.from_user.full_name

    # =====================================================
    # АДМИНИСТРАТОР
    # =====================================================

    if user_id in ADMIN_IDS:

        await save_user(
            telegram_id=user_id,
            full_name=full_name,
            role="admin"
        )

        await message.answer(
            "AYDA GO — РЕМОНТ\n\n"
            f"👤 {full_name}\n"
            "Роль: Администратор",
            reply_markup=admin_menu()
        )

        return

    # =====================================================
    # МАСТЕР
    # =====================================================

    if user_id in MASTER_IDS:

        await save_user(
            telegram_id=user_id,
            full_name=full_name,
            role="master"
        )

        await message.answer(
            "AYDA GO — РЕМОНТ\n\n"
            f"👨‍🔧 {full_name}\n"
            "Роль: Мастер",
            reply_markup=master_menu()
        )

        return

    # =====================================================
    # СОТРУДНИК АРЕНДЫ
    # =====================================================

    if user_id in RENTAL_STAFF_IDS:

        await save_user(
            telegram_id=user_id,
            full_name=full_name,
            role="rental_staff"
        )

        await message.answer(
            "AYDA GO — РЕМОНТ\n\n"
            f"👤 {full_name}\n"
            "Роль: Сотрудник аренды",
            reply_markup=rental_staff_menu()
        )

        return

    # =====================================================
    # НЕТ ДОСТУПА
    # =====================================================

    await message.answer(
        "⛔ Доступ к боту не предоставлен.\n\n"
        f"Ваш Telegram ID:\n"
        f"`{user_id}`\n\n"
        "Передайте этот ID администратору.",
        parse_mode="Markdown"
    )