import os
import aiosqlite

from config import DATABASE_PATH


async def column_exists(
    db,
    table_name: str,
    column_name: str
):
    cursor = await db.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = await cursor.fetchall()

    return any(
        column[1] == column_name
        for column in columns
    )


async def add_column_if_missing(
    db,
    table_name: str,
    column_name: str,
    definition: str
):
    exists = await column_exists(
        db,
        table_name,
        column_name
    )

    if not exists:
        await db.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} {definition}
            """
        )


async def migrate_repair_history(db):
    cursor = await db.execute(
        "PRAGMA table_info(repair_history)"
    )

    columns = await cursor.fetchall()

    if not columns:
        return

    old_repair_id_not_null = False

    for column in columns:
        name = column[1]
        not_null = column[3]

        if name == "repair_id" and not_null == 1:
            old_repair_id_not_null = True
            break

    if not old_repair_id_not_null:
        return

    print("[DB] Миграция repair_history...")

    await db.execute("""
        CREATE TABLE repair_history_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            repair_id INTEGER,
            action TEXT NOT NULL,
            old_status TEXT,
            new_status TEXT,
            user_telegram_id INTEGER,
            user_name TEXT,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    old_columns = {
        column[1]
        for column in columns
    }

    request_id_sql = (
        "request_id"
        if "request_id" in old_columns
        else "NULL"
    )

    user_name_sql = (
        "user_name"
        if "user_name" in old_columns
        else "NULL"
    )

    await db.execute(f"""
        INSERT INTO repair_history_new (
            id,
            request_id,
            repair_id,
            action,
            old_status,
            new_status,
            user_telegram_id,
            user_name,
            reason,
            created_at
        )

        SELECT
            id,
            {request_id_sql},
            repair_id,
            action,
            old_status,
            new_status,
            user_telegram_id,
            {user_name_sql},
            reason,
            created_at

        FROM repair_history
    """)

    await db.execute(
        "DROP TABLE repair_history"
    )

    await db.execute("""
        ALTER TABLE repair_history_new
        RENAME TO repair_history
    """)

    print("[DB] repair_history обновлена")


async def init_db():
    database_directory = os.path.dirname(
        DATABASE_PATH
    )

    os.makedirs(
        database_directory,
        exist_ok=True
    )

    print(
        f"[DB] Используется база: {DATABASE_PATH}"
    )

    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        await db.execute(
            "PRAGMA foreign_keys = ON"
        )

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                full_name TEXT,
                role TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS repair_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_code TEXT UNIQUE,
                bike_number TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                creator_name TEXT,
                client_payment_status TEXT
                    NOT NULL DEFAULT 'unpaid',
                expected_amount REAL
                    NOT NULL DEFAULT 0,
                paid_amount REAL
                    NOT NULL DEFAULT 0,
                comment TEXT,
                status TEXT
                    NOT NULL DEFAULT 'new',
                assigned_master_id INTEGER,
                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS repairs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repair_code TEXT UNIQUE,
                request_id INTEGER,
                master_telegram_id INTEGER NOT NULL,
                bike_number TEXT NOT NULL,
                payer_type TEXT NOT NULL DEFAULT 'client',
                repair_type TEXT NOT NULL,
                description TEXT,
                company_reason TEXT,
                bike_photo_file_id TEXT,
                total_amount REAL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                approved_by INTEGER,
                approved_at TIMESTAMP,
                rejection_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (request_id)
                    REFERENCES repair_requests(id)
            )
        """)

        await add_column_if_missing(
            db,
            "repairs",
            "request_id",
            "INTEGER"
        )

        await db.execute("""
            CREATE TABLE IF NOT EXISTS repair_parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repair_id INTEGER NOT NULL,
                part_name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                source_type TEXT,
                donor_bike_number TEXT,
                FOREIGN KEY (repair_id)
                    REFERENCES repairs(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER,
                repair_id INTEGER,
                amount REAL NOT NULL,
                payment_method TEXT,
                accepted_by INTEGER,
                accepted_by_name TEXT,
                payment_photo_file_id TEXT,
                status TEXT NOT NULL DEFAULT 'confirmed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await add_column_if_missing(
            db,
            "payments",
            "request_id",
            "INTEGER"
        )

        await add_column_if_missing(
            db,
            "payments",
            "accepted_by",
            "INTEGER"
        )

        await add_column_if_missing(
            db,
            "payments",
            "accepted_by_name",
            "TEXT"
        )

        await db.execute("""
            CREATE TABLE IF NOT EXISTS repair_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER,
                repair_id INTEGER,
                action TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT,
                user_telegram_id INTEGER,
                user_name TEXT,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await add_column_if_missing(
            db,
            "repair_history",
            "request_id",
            "INTEGER"
        )

        await add_column_if_missing(
            db,
            "repair_history",
            "user_name",
            "TEXT"
        )

        await migrate_repair_history(
            db
        )

        await db.commit()


async def save_user(
    telegram_id: int,
    full_name: str,
    role: str
):
    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        await db.execute("""
            INSERT INTO users (
                telegram_id,
                full_name,
                role,
                is_active
            )
            VALUES (?, ?, ?, 1)

            ON CONFLICT(telegram_id)
            DO UPDATE SET
                full_name = excluded.full_name,
                role = excluded.role,
                is_active = 1
        """, (
            telegram_id,
            full_name,
            role
        ))

        await db.commit()


async def create_repair_request(
    bike_number: str,
    created_by: int,
    creator_name: str,
    payment_status: str,
    expected_amount: float = 0,
    paid_amount: float = 0,
    comment: str | None = None
):
    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        cursor = await db.execute("""
            INSERT INTO repair_requests (
                bike_number,
                created_by,
                creator_name,
                client_payment_status,
                expected_amount,
                paid_amount,
                comment,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bike_number,
            created_by,
            creator_name,
            payment_status,
            expected_amount,
            paid_amount,
            comment,
            "new"
        ))

        request_id = cursor.lastrowid

        request_code = f"Z-{request_id:06d}"

        await db.execute("""
            UPDATE repair_requests
            SET request_code = ?
            WHERE id = ?
        """, (
            request_code,
            request_id
        ))

        await db.execute("""
            INSERT INTO repair_history (
                request_id,
                repair_id,
                action,
                old_status,
                new_status,
                user_telegram_id,
                user_name,
                reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id,
            None,
            "request_created",
            None,
            "new",
            created_by,
            creator_name,
            "Создана заявка"
        ))

        await db.commit()

        return {
            "id": request_id,
            "request_code": request_code
        }


async def add_request_payment(
    request_id: int,
    amount: float,
    payment_method: str,
    accepted_by: int,
    accepted_by_name: str,
    payment_photo_file_id: str
):
    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        await db.execute("""
            INSERT INTO payments (
                request_id,
                repair_id,
                amount,
                payment_method,
                accepted_by,
                accepted_by_name,
                payment_photo_file_id,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id,
            None,
            amount,
            payment_method,
            accepted_by,
            accepted_by_name,
            payment_photo_file_id,
            "confirmed"
        ))

        await db.execute("""
            UPDATE repair_requests
            SET
                paid_amount = ?,
                client_payment_status = 'paid',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            amount,
            request_id
        ))

        await db.commit()


async def get_new_repair_requests():
    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT *
            FROM repair_requests
            WHERE status = 'new'
            ORDER BY id ASC
        """)

        rows = await cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]


async def get_request_by_id(
    request_id: int
):
    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT *
            FROM repair_requests
            WHERE id = ?
        """, (
            request_id,
        ))

        row = await cursor.fetchone()

        if not row:
            return None

        return dict(row)


async def assign_request_to_master(
    request_id: int,
    master_telegram_id: int,
    master_name: str
):
    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        cursor = await db.execute("""
            UPDATE repair_requests
            SET
                assigned_master_id = ?,
                status = 'in_work',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            AND status = 'new'
        """, (
            master_telegram_id,
            request_id
        ))

        if cursor.rowcount == 0:
            await db.rollback()
            return False

        await db.execute("""
            INSERT INTO repair_history (
                request_id,
                repair_id,
                action,
                old_status,
                new_status,
                user_telegram_id,
                user_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id,
            None,
            "assigned_to_master",
            "new",
            "in_work",
            master_telegram_id,
            master_name
        ))

        await db.commit()

        return True


async def create_repair_from_request(
    request_id: int,
    master_telegram_id: int,
    master_name: str,
    repair_type: str,
    description: str,
    bike_photo_file_id: str,
    part_name: str | None = None,
    part_quantity: int | None = None,
    source_type: str | None = None,
    donor_bike_number: str | None = None
):
    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT *
            FROM repair_requests
            WHERE id = ?
            AND assigned_master_id = ?
            AND status = 'in_work'
        """, (
            request_id,
            master_telegram_id
        ))

        request = await cursor.fetchone()

        if not request:
            return None

        cursor = await db.execute("""
            INSERT INTO repairs (
                request_id,
                master_telegram_id,
                bike_number,
                payer_type,
                repair_type,
                description,
                bike_photo_file_id,
                total_amount,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id,
            master_telegram_id,
            request["bike_number"],
            "client",
            repair_type,
            description,
            bike_photo_file_id,
            request["expected_amount"],
            "pending"
        ))

        repair_id = cursor.lastrowid

        repair_code = f"R-{repair_id:06d}"

        await db.execute("""
            UPDATE repairs
            SET repair_code = ?
            WHERE id = ?
        """, (
            repair_code,
            repair_id
        ))

        if repair_type == "part":
            await db.execute("""
                INSERT INTO repair_parts (
                    repair_id,
                    part_name,
                    quantity,
                    source_type,
                    donor_bike_number
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                repair_id,
                part_name,
                part_quantity,
                source_type,
                donor_bike_number
            ))

        await db.execute("""
            UPDATE payments
            SET repair_id = ?
            WHERE request_id = ?
            AND repair_id IS NULL
        """, (
            repair_id,
            request_id
        ))

        await db.execute("""
            UPDATE repair_requests
            SET
                status = 'awaiting_approval',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            request_id,
        ))

        await db.execute("""
            INSERT INTO repair_history (
                request_id,
                repair_id,
                action,
                old_status,
                new_status,
                user_telegram_id,
                user_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id,
            repair_id,
            "repair_completed",
            "in_work",
            "awaiting_approval",
            master_telegram_id,
            master_name
        ))

        await db.commit()

        return {
            "repair_id": repair_id,
            "repair_code": repair_code,
            "request_code": request["request_code"],
            "bike_number": request["bike_number"],
            "payment_status": request[
                "client_payment_status"
            ],
            "paid_amount": request[
                "paid_amount"
            ],
            "expected_amount": request[
                "expected_amount"
            ]
        }


async def get_master_requests(
    master_telegram_id: int
):
    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT *
            FROM repair_requests
            WHERE assigned_master_id = ?
            ORDER BY id DESC
        """, (
            master_telegram_id,
        ))

        rows = await cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]


async def get_requests_by_bike(
    bike_number: str
):
    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT *
            FROM repair_requests
            WHERE bike_number = ?
            ORDER BY id DESC
        """, (
            bike_number,
        ))

        rows = await cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

async def create_master_repair_request(
    bike_number: str,
    master_telegram_id: int,
    master_name: str,
    payer_type: str,
    payment_status: str = "unpaid",
    expected_amount: float = 0,
    company_reason: str | None = None
):
    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        cursor = await db.execute("""
            INSERT INTO repair_requests (
                bike_number,
                created_by,
                creator_name,
                client_payment_status,
                expected_amount,
                paid_amount,
                comment,
                status,
                assigned_master_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bike_number,
            master_telegram_id,
            master_name,
            payment_status,
            expected_amount,
            0,
            company_reason,
            "in_work",
            master_telegram_id
        ))

        request_id = cursor.lastrowid

        request_code = (
            f"Z-{request_id:06d}"
        )

        await db.execute("""
            UPDATE repair_requests
            SET request_code = ?
            WHERE id = ?
        """, (
            request_code,
            request_id
        ))

        await db.execute("""
            INSERT INTO repair_history (
                request_id,
                repair_id,
                action,
                old_status,
                new_status,
                user_telegram_id,
                user_name,
                reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id,
            None,
            "master_request_created",
            None,
            "in_work",
            master_telegram_id,
            master_name,
            (
                "Ремонт создан мастером. "
                f"Плательщик: {payer_type}"
            )
        ))

        await db.commit()

        return {
            "id": request_id,
            "request_code": request_code
        }