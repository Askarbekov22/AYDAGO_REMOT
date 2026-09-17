from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


def take_request_keyboard(
    request_id: int
):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔧 Взять в работу",
                    callback_data=f"take_request:{request_id}"
                )
            ]
        ]
    )


def resume_request_keyboard(
    request_id: int
):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="▶️ Продолжить ремонт",
                    callback_data=f"resume_request:{request_id}"
                )
            ]
        ]
    )


def master_repair_confirmation_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Завершить ремонт",
                    callback_data="master_repair_save"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data="master_repair_cancel"
                )
            ]
        ]
    )