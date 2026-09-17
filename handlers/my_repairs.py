from aiogram import Router, F
from aiogram.types import Message

from database.db import get_master_repairs


router = Router()


def get_status_text(status: str):
    statuses = {
        "pending": "⏳ На проверке",
        "approved": "✅ Подтвержден",
        "rejected": "❌ Отклонен",
        "cancelled": "🚫 Отменен"
    }

    return statuses.get(
        status,
        status
    )


def get_payer_text(payer_type: str):
    if payer_type == "company":
        return "🏢 Компания"

    return "💰 Клиент"


@router.message(
    F.text == "📋 Мои ремонты"
)
async def my_repairs_handler(
    message: Message
):
    repairs = await get_master_repairs(
        master_telegram_id=message.from_user.id,
        limit=10
    )

    if not repairs:
        await message.answer(
            "📋 У вас пока нет сохраненных ремонтов."
        )
        return

    await message.answer(
        "📋 ВАШИ ПОСЛЕДНИЕ РЕМОНТЫ\n\n"
        "Показываю последние 10 записей."
    )

    for repair in repairs:
        text = (
            f"🔧 {repair['repair_code']}\n\n"
            f"🚲 Велосипед: №"
            f"{repair['bike_number']}\n"
            f"💳 Оплата: "
            f"{get_payer_text(repair['payer_type'])}\n"
            f"📌 Статус: "
            f"{get_status_text(repair['status'])}\n"
        )

        if repair["repair_type"] == "part":
            text += (
                "\n🔩 Запчасть:\n"
                f"{repair['part_name']} × "
                f"{repair['quantity']}\n"
            )

            if (
                repair["source_type"]
                == "warehouse"
            ):
                text += (
                    "Источник: 📦 Склад\n"
                )

            elif (
                repair["source_type"]
                == "donor"
            ):
                text += (
                    "Источник: 🚲 Донор\n"
                    f"Донор: №"
                    f"{repair['donor_bike_number']}\n"
                )

        else:
            text += (
                "\n🛠 Без замены запчасти\n"
            )

        text += (
            f"\n📝 Работа:\n"
            f"{repair['description']}\n"
        )

        if repair["payer_type"] == "client":
            text += (
                f"\n💵 Сумма: "
                f"{repair['total_amount']:,.0f} сом\n"
            )

        if (
            repair["payer_type"] == "company"
            and repair["company_reason"]
        ):
            text += (
                f"\n📌 Причина:\n"
                f"{repair['company_reason']}\n"
            )

        created_at = repair[
            "created_at"
        ]

        if created_at:
            text += (
                f"\n🕒 {created_at}"
            )

        await message.answer(
            text
        )