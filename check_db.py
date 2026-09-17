import asyncio
import aiosqlite

from config import DATABASE_PATH


async def main():
    print(f"\nБаза данных:\n{DATABASE_PATH}\n")

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Количество заявок
        cursor = await db.execute("""
            SELECT COUNT(*) AS count
            FROM repair_requests
        """)

        row = await cursor.fetchone()

        print(
            f"Всего заявок в repair_requests: "
            f"{row['count']}"
        )

        print("=" * 60)

        # Все заявки
        cursor = await db.execute("""
            SELECT
                id,
                request_code,
                bike_number,
                created_by,
                creator_name,
                client_payment_status,
                expected_amount,
                paid_amount,
                status,
                assigned_master_id,
                created_at

            FROM repair_requests

            ORDER BY id DESC
        """)

        requests = await cursor.fetchall()

        if not requests:
            print(
                "❌ ЗАЯВОК В БАЗЕ НЕТ"
            )
            return

        for request in requests:
            print()
            print(
                f"ID: {request['id']}"
            )

            print(
                f"Заявка: {request['request_code']}"
            )

            print(
                f"Велосипед: №{request['bike_number']}"
            )

            print(
                f"Создал: {request['creator_name']}"
            )

            print(
                f"Оплата: "
                f"{request['client_payment_status']}"
            )

            print(
                f"Сумма: "
                f"{request['expected_amount']}"
            )

            print(
                f"Оплачено: "
                f"{request['paid_amount']}"
            )

            print(
                f"СТАТУС: {request['status']}"
            )

            print(
                f"МАСТЕР ID: "
                f"{request['assigned_master_id']}"
            )

            print(
                f"Дата: {request['created_at']}"
            )

            print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())