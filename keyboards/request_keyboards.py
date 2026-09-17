from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


def payment_status_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Уже оплачено",
                    callback_data="request_paid"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Не оплачено",
                    callback_data="request_unpaid"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="request_cancel"
                )
            ]
        ]
    )


def payment_method_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📱 QR",
                    callback_data="payment_qr"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💵 Наличные",
                    callback_data="payment_cash"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏦 Перевод",
                    callback_data="payment_transfer"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="request_cancel"
                )
            ]
        ]
    )


def request_confirmation_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Создать заявку",
                    callback_data="request_save"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data="request_cancel"
                )
            ]
        ]
    )