from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


def admin_repair_keyboard(
    repair_id: int
):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=(
                        f"admin_approve:{repair_id}"
                    )
                )
            ],
            [
                InlineKeyboardButton(
                    text="↩️ Вернуть мастеру",
                    callback_data=(
                        f"admin_reject:{repair_id}"
                    )
                )
            ]
        ]
    )


def admin_rejection_cancel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=(
                        "admin_rejection_cancel"
                    )
                )
            ]
        ]
    )