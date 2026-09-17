from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


def repair_type_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔩 Замена запчасти",
                    callback_data="repair_type_part"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛠 Без замены запчасти",
                    callback_data="repair_type_no_part"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="repair_cancel"
                )
            ]
        ]
    )


def client_repair_type_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔩 Замена запчасти",
                    callback_data="client_repair_type_part"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛠 Без замены запчасти",
                    callback_data="client_repair_type_no_part"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="client_repair_cancel"
                )
            ]
        ]
    )


def part_source_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 Со склада",
                    callback_data="part_source_warehouse"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚲 С велосипеда-донора",
                    callback_data="part_source_donor"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="repair_cancel"
                )
            ]
        ]
    )


def client_part_source_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 Со склада",
                    callback_data="client_part_source_warehouse"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚲 С велосипеда-донора",
                    callback_data="client_part_source_donor"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="client_repair_cancel"
                )
            ]
        ]
    )


def confirmation_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Сохранить",
                    callback_data="company_repair_save"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data="company_repair_cancel"
                )
            ]
        ]
    )


def client_confirmation_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Сохранить",
                    callback_data="client_repair_save"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data="client_repair_cancel"
                )
            ]
        ]
    )