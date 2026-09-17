import os

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile
)

from database.db import (
    get_excel_report_data
)

from keyboards.report_keyboards import (
    report_period_keyboard
)

from services.excel_report import (
    create_excel_report
)


router = Router()


@router.message(
    F.text == "📊 Отчет"
)
async def report_start(
    message: Message
):
    await message.answer(
        "📊 ОТЧЕТ ПО РЕМОНТАМ\n\n"
        "Выберите период:",
        reply_markup=report_period_keyboard()
    )


async def generate_and_send_report(
    callback: CallbackQuery,
    period: str
):
    await callback.answer(
        "Формирую Excel..."
    )

    await callback.message.answer(
        "📊 Формирую отчет..."
    )

    data = await get_excel_report_data(
        master_telegram_id=callback.from_user.id,
        period=period
    )

    if not data["repairs"]:
        await callback.message.answer(
            "За выбранный период ремонтов нет."
        )
        return

    file_path = create_excel_report(
        data=data,
        period=period,
        master_name=callback.from_user.full_name,
        master_telegram_id=callback.from_user.id
    )

    document = FSInputFile(
        file_path
    )

    period_names = {
        "today": "сегодня",
        "7days": "последние 7 дней",
        "month": "текущий месяц"
    }

    try:
        await callback.message.answer_document(
            document=document,
            caption=(
                "📊 AYDA GO — отчет по ремонтам\n\n"
                f"Период: "
                f"{period_names.get(period, period)}"
            )
        )

    finally:
        if os.path.exists(
            file_path
        ):
            os.remove(
                file_path
            )


@router.callback_query(
    F.data == "excel_report_today"
)
async def excel_report_today(
    callback: CallbackQuery
):
    await generate_and_send_report(
        callback,
        "today"
    )


@router.callback_query(
    F.data == "excel_report_7days"
)
async def excel_report_7days(
    callback: CallbackQuery
):
    await generate_and_send_report(
        callback,
        "7days"
    )


@router.callback_query(
    F.data == "excel_report_month"
)
async def excel_report_month(
    callback: CallbackQuery
):
    await generate_and_send_report(
        callback,
        "month"
    )