from aiogram import (
    Router,
    F
)

from aiogram.filters import (
    Command
)

from aiogram.types import (
    Message
)

from aiogram.fsm.context import (
    FSMContext
)

from config import (
    ADMIN_IDS,
    MASTER_IDS,
    RENTAL_STAFF_IDS
)

from keyboards.main_menu import (
    admin_menu,
    master_menu,
    rental_staff_menu
)


router = Router()


async def show_main_menu(
    message: Message,
    state: FSMContext
):
    await state.clear()

    user_id = message.from_user.id

    if user_id in ADMIN_IDS:
        await message.answer(
            "🏠 ГЛАВНОЕ МЕНЮ\n\n"
            "Роль: Администратор",
            reply_markup=admin_menu()
        )
        return

    if user_id in MASTER_IDS:
        await message.answer(
            "🏠 ГЛАВНОЕ МЕНЮ\n\n"
            "Роль: Мастер",
            reply_markup=master_menu()
        )
        return

    if user_id in RENTAL_STAFF_IDS:
        await message.answer(
            "🏠 ГЛАВНОЕ МЕНЮ\n\n"
            "Роль: Сотрудник аренды",
            reply_markup=rental_staff_menu()
        )
        return

    await message.answer(
        "⛔ Доступ не предоставлен."
    )


@router.message(
    F.text == "🏠 Главное меню"
)
async def main_menu_button(
    message: Message,
    state: FSMContext
):
    await show_main_menu(
        message,
        state
    )


@router.message(
    Command("menu")
)
async def main_menu_command(
    message: Message,
    state: FSMContext
):
    await show_main_menu(
        message,
        state
    )