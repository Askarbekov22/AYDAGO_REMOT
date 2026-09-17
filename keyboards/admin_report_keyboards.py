from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


def admin_report_period_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Сегодня",
                    callback_data="admin_report:today"
                )
            ],
            [
                InlineKeyboardButton(
                    text="7️⃣ Последние 7 дней",
                    callback_data="admin_report:7days"
                )
            ],
            [
                InlineKeyboardButton(
                    text="3️⃣0️⃣ Последние 30 дней",
                    callback_data="admin_report:30days"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗓 Этот месяц",
                    callback_data="admin_report:month"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📚 Все время",
                    callback_data="admin_report:all"
                )
            ]
        ]
    )