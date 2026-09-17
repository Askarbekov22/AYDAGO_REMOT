import asyncio
import os

from aiogram import (
    Router,
    F
)

from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile
)

from config import (
    MASTER_IDS
)

from keyboards.master_report_keyboards import (
    master_report_period_keyboard
)

from keyboards.main_menu import (
    master_menu
)

from services.master_report import (
    load_master_report_data,
    create_excel_report
)


router = Router()


def is_master(
    telegram_id: int
):
    return telegram_id in MASTER_IDS


@router.message(
    F.text == "📊 Отчет"
)
async def master_report_menu(
    message: Message
):
    if not is_master(
        message.from_user.id
    ):
        return

    await message.answer(
        "📊 ОТЧЕТ МАСТЕРА\n\n"
        "Выберите период:",
        reply_markup=(
            master_report_period_keyboard()
        )
    )


@router.callback_query(
    F.data.startswith(
        "master_report:"
    )
)
async def generate_master_report(
    callback: CallbackQuery
):
    if not is_master(
        callback.from_user.id
    ):
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    period = (
        callback.data
        .split(":")[1]
    )

    allowed_periods = {
        "today",
        "7days",
        "30days",
        "month",
        "all"
    }

    if period not in allowed_periods:
        await callback.answer(
            "Неизвестный период.",
            show_alert=True
        )
        return

    await callback.answer(
        "Формирую отчет..."
    )

    data = await load_master_report_data(
        master_id=callback.from_user.id,
        period=period
    )

    if not data["repairs"]:
        await callback.message.answer(
            "📊 За выбранный период "
            "у вас нет завершенных ремонтов.",
            reply_markup=master_menu()
        )
        return

    file_path = None

    try:
        file_path = await asyncio.to_thread(
            create_excel_report,
            data
        )

        safe_name = (
            callback.from_user.full_name
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
        )

        filename = (
            f"Отчет_мастера_"
            f"{safe_name}_"
            f"{period}.xlsx"
        )

        document = FSInputFile(
            file_path,
            filename=filename
        )

        total_repairs = len(
            data["repairs"]
        )

        total_parts = sum(
            int(
                part["quantity"]
                or 0
            )
            for part in data["parts"]
        )

        total_payments = sum(
            float(
                payment["amount"]
                or 0
            )
            for payment in data[
                "payments"
            ]
        )

        caption = (
            "📊 ОТЧЕТ МАСТЕРА\n\n"
            f"👨‍🔧 "
            f"{data['master_name']}\n"
            f"📅 "
            f"{data['period_title']}\n\n"
            f"🔧 Ремонтов: "
            f"{total_repairs}\n"
            f"📦 Запчастей: "
            f"{total_parts}\n"
            f"💰 Оплат: "
            f"{total_payments:,.0f} сом"
        )

        await callback.message.answer_document(
            document=document,
            caption=caption
        )

    except Exception as error:
        print(
            "[MASTER REPORT ERROR]",
            error
        )

        await callback.message.answer(
            "❌ Не удалось сформировать "
            "Excel-отчет.\n\n"
            f"Ошибка: {error}"
        )

    finally:
        if (
            file_path
            and os.path.exists(
                file_path
            )
        ):
            try:
                os.remove(
                    file_path
                )
            except Exception:
                pass