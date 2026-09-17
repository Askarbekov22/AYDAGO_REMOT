from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


def admin_requests_filter_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🆕 Новые",
                    callback_data="admin_requests:new"
                ),
                InlineKeyboardButton(
                    text="🔧 В работе",
                    callback_data="admin_requests:in_work"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏳ На подтверждении",
                    callback_data="admin_requests:awaiting_approval"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Подтвержденные",
                    callback_data="admin_requests:approved"
                )
            ],
            [
                InlineKeyboardButton(
                    text="↩️ Возвращенные",
                    callback_data="admin_requests:returned"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Все",
                    callback_data="admin_requests:all"
                )
            ]
        ]
    )


def admin_request_card_keyboard(
    request_id: int,
    repair_id: int | None,
    workflow_status: str
):
    buttons = []

    if (
        workflow_status == "awaiting_approval"
        and repair_id
    ):
        buttons.append([
            InlineKeyboardButton(
                text="🔍 Открыть ремонт",
                callback_data=(
                    f"admin_open_repair:{repair_id}"
                )
            )
        ])

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    ) if buttons else None