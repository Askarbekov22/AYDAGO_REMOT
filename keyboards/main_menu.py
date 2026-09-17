from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton
)


def master_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="➕ Создать ремонт"
                )
            ],
            [
                KeyboardButton(
                    text="🆕 Новые заявки"
                )
            ],
            [
                KeyboardButton(
                    text="🔧 Мои ремонты"
                )
            ],
            [
                KeyboardButton(
                    text="🔎 Проверить велосипед"
                )
            ],
            [
                KeyboardButton(
                    text="📊 Отчет"
                )
            ],
            [
                KeyboardButton(
                    text="🏠 Главное меню"
                )
            ]
        ],
        resize_keyboard=True
    )


def rental_staff_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="➕ Создать заявку на ремонт"
                )
            ],
            [
                KeyboardButton(
                    text="💳 Добавить оплату"
                )
            ],
            [
                KeyboardButton(
                    text="🔎 Найти велосипед"
                )
            ],
            [
                KeyboardButton(
                    text="📋 Открытые заявки"
                )
            ],
            [
                KeyboardButton(
                    text="🏠 Главное меню"
                )
            ]
        ],
        resize_keyboard=True
    )


def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="✅ На подтверждение"
                )
            ],
            [
                KeyboardButton(
                    text="📋 Все заявки"
                )
            ],
            [
                KeyboardButton(
                    text="📊 Общий отчет"
                )
            ],
            [
                KeyboardButton(
                    text="🔎 Найти велосипед"
                )
            ],
            [
                KeyboardButton(
                    text="👥 Сотрудники"
                )
            ],
            [
                KeyboardButton(
                    text="🏠 Главное меню"
                )
            ]
        ],
        resize_keyboard=True
    )