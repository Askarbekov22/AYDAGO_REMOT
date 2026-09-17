from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


def master_create_confirmation_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Сохранить ремонт",
                    callback_data=(
                        "master_create:save"
                    )
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=(
                        "master_create:cancel"
                    )
                )
            ]
        ]
    )