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
    ADMIN_IDS
)

from keyboards.admin_report_keyboards import (
    admin_report_period_keyboard
)

from keyboards.main_menu import (
    admin_menu
)

from services.admin_report import (
    load_admin_report_data,
    create_admin_excel_report
)


router = Router()


def is_admin(
    telegram_id: int
):
    return telegram_id in ADMIN_IDS


@router.message(
    F.text == "📊 Общий отчет"
)
async def admin_report_menu(
    message: Message
):
    if not is_admin(
        message.from_user.id
    ):
        return

    await message.answer(
        "📊 ОБЩИЙ ОТЧЕТ ПО РЕМОНТАМ\n\n"
        "Выберите период:",
        reply_markup=(
            admin_report_period_keyboard()
        )
    )


@router.callback_query(
    F.data.startswith(
        "admin_report:"
    )
)
async def admin_report_generate(
    callback: CallbackQuery
):
    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "Нет доступа.",
            show_alert=True
        )
        return

    try:
        period = (
            callback.data.split(":")[1]
        )

    except IndexError:
        await callback.answer(
            "Ошибка периода.",
            show_alert=True
        )
        return

    allowed = {
        "today",
        "7days",
        "30days",
        "month",
        "all"
    }

    if period not in allowed:
        await callback.answer(
            "Неизвестный период.",
            show_alert=True
        )
        return

    await callback.answer(
        "Формирую отчет..."
    )

    data = await load_admin_report_data(
        period
    )

    if (
        not data["repairs"]
        and not data["payments"]
    ):
        await callback.message.answer(
            "📊 За выбранный период "
            "данных пока нет.",
            reply_markup=admin_menu()
        )
        return

    file_path = None

    try:
        file_path = await asyncio.to_thread(
            create_admin_excel_report,
            data
        )

        filename = (
            "AYDA_REPAIR_REPORT_"
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

        total_income = sum(
            float(
                payment["amount"]
                or 0
            )
            for payment
            in data["payments"]
        )

        masters = len({
            repair[
                "master_telegram_id"
            ]
            for repair
            in data["repairs"]
            if repair[
                "master_telegram_id"
            ]
        })

        caption = (
            "📊 ОБЩИЙ ОТЧЕТ AYDA GO\n\n"
            f"📅 {data['period_title']}\n\n"
            f"🔧 Ремонтов: "
            f"{total_repairs}\n"
            f"👨‍🔧 Мастеров: "
            f"{masters}\n"
            f"📦 Запчастей: "
            f"{total_parts}\n"
            f"💰 Поступления: "
            f"{total_income:,.0f} сом"
        )

        await callback.message.answer_document(
            document=document,
            caption=caption
        )

    except Exception as error:
        print(
            "[ADMIN REPORT ERROR]",
            error
        )

        await callback.message.answer(
            "❌ Не удалось сформировать отчет.\n\n"
            f"Ошибка:\n{error}",
            reply_markup=admin_menu()
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