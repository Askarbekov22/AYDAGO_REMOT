from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


def report_period_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Сегодня",
                    callback_data="excel_report_today"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Последние 7 дней",
                    callback_data="excel_report_7days"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Этот месяц",
                    callback_data="excel_report_month"
                )
            ]
        ]
    )