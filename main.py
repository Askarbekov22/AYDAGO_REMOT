import asyncio
import logging

from aiogram import (
    Bot,
    Dispatcher
)

from config import (
    BOT_TOKEN,
    DATABASE_PATH
)

from database.db import (
    init_db
)

from handlers.start import (
    router as start_router
)

from handlers.common import (
    router as common_router
)

from handlers.create_request import (
    router as create_request_router
)

from handlers.master_requests import (
    router as master_requests_router
)

from handlers.master_create_repair import (
    router as master_create_repair_router
)

from handlers.master_reports import (
    router as master_reports_router
)

from handlers.admin_repairs import (
    router as admin_repairs_router
)

from handlers.admin_reports import (
    router as admin_reports_router
)

from handlers.admin_requests import (
    router as admin_requests_router
)


async def main():
    logging.basicConfig(
        level=logging.INFO
    )

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN не найден в .env"
        )

    await init_db()

    print("")
    print("=" * 60)
    print("AYDA Repair Bot запущен")
    print(
        f"База данных: "
        f"{DATABASE_PATH}"
    )
    print("=" * 60)
    print("")

    bot = Bot(
        token=BOT_TOKEN
    )

    dp = Dispatcher()

    dp.include_router(
        start_router
    )

    dp.include_router(
        common_router
    )

    dp.include_router(
        create_request_router
    )

    dp.include_router(
        master_create_repair_router
    )

    dp.include_router(
        master_requests_router
    )

    dp.include_router(
        master_reports_router
    )

    dp.include_router(
        admin_repairs_router
    )

    dp.include_router(
        admin_reports_router
    )

    dp.include_router(
        admin_requests_router
    )

    await dp.start_polling(
        bot
    )


if __name__ == "__main__":
    asyncio.run(
        main()
    )