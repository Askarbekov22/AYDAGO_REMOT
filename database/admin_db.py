import aiosqlite

from config import DATABASE_PATH


# =========================================================
# РЕМОНТЫ НА ПОДТВЕРЖДЕНИЕ
# =========================================================

async def get_pending_repairs():
    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT
                r.id,
                r.repair_code,
                r.request_id,
                r.master_telegram_id,
                r.bike_number,
                r.payer_type,
                r.repair_type,
                r.description,
                r.company_reason,
                r.bike_photo_file_id,
                r.total_amount,
                r.status,
                r.created_at,

                rr.request_code,
                rr.client_payment_status,
                rr.expected_amount,
                rr.paid_amount,
                rr.comment,

                u.full_name AS master_name

            FROM repairs r

            LEFT JOIN repair_requests rr
                ON rr.id = r.request_id

            LEFT JOIN users u
                ON u.telegram_id =
                    r.master_telegram_id

            WHERE r.status = 'pending'
            AND rr.status = 'awaiting_approval'

            ORDER BY r.created_at ASC
        """)

        rows = await cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]


# =========================================================
# РЕМОНТ ДЛЯ АДМИНИСТРАТОРА
# =========================================================

async def get_repair_for_admin(
    repair_id: int
):
    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT
                r.id,
                r.repair_code,
                r.request_id,
                r.master_telegram_id,
                r.bike_number,
                r.payer_type,
                r.repair_type,
                r.description,
                r.company_reason,
                r.bike_photo_file_id,
                r.total_amount,
                r.status,
                r.rejection_reason,
                r.created_at,

                rr.request_code,
                rr.client_payment_status,
                rr.expected_amount,
                rr.paid_amount,
                rr.comment,
                rr.status AS request_status,

                u.full_name AS master_name

            FROM repairs r

            LEFT JOIN repair_requests rr
                ON rr.id = r.request_id

            LEFT JOIN users u
                ON u.telegram_id =
                    r.master_telegram_id

            WHERE r.id = ?
        """, (
            repair_id,
        ))

        row = await cursor.fetchone()

        if not row:
            return None

        repair = dict(row)

        cursor = await db.execute("""
            SELECT
                part_name,
                quantity,
                source_type,
                donor_bike_number

            FROM repair_parts

            WHERE repair_id = ?

            ORDER BY id ASC
        """, (
            repair_id,
        ))

        repair["parts"] = [
            dict(row)
            for row in await cursor.fetchall()
        ]

        cursor = await db.execute("""
            SELECT
                id,
                amount,
                payment_method,
                accepted_by,
                accepted_by_name,
                payment_photo_file_id,
                status,
                created_at

            FROM payments

            WHERE request_id = ?
            AND status = 'confirmed'

            ORDER BY id ASC
        """, (
            repair["request_id"],
        ))

        repair["payments"] = [
            dict(row)
            for row in await cursor.fetchall()
        ]

        return repair


# =========================================================
# ВСЕ ЗАЯВКИ ДЛЯ АДМИНИСТРАТОРА
# =========================================================

async def get_admin_requests(
    status_filter: str = "all",
    limit: int = 50
):
    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        sql = """
            SELECT
                rr.id,
                rr.request_code,
                rr.bike_number,
                rr.created_by,
                rr.creator_name,

                rr.client_payment_status,
                rr.expected_amount,
                rr.paid_amount,

                rr.comment,
                rr.status,
                rr.assigned_master_id,
                rr.created_at,
                rr.updated_at,

                u.full_name AS master_name,

                (
                    SELECT r.id
                    FROM repairs r
                    WHERE r.request_id = rr.id
                    ORDER BY r.id DESC
                    LIMIT 1
                ) AS latest_repair_id,

                (
                    SELECT r.repair_code
                    FROM repairs r
                    WHERE r.request_id = rr.id
                    ORDER BY r.id DESC
                    LIMIT 1
                ) AS latest_repair_code,

                (
                    SELECT r.status
                    FROM repairs r
                    WHERE r.request_id = rr.id
                    ORDER BY r.id DESC
                    LIMIT 1
                ) AS latest_repair_status,

                (
                    SELECT r.rejection_reason
                    FROM repairs r
                    WHERE r.request_id = rr.id
                    ORDER BY r.id DESC
                    LIMIT 1
                ) AS rejection_reason

            FROM repair_requests rr

            LEFT JOIN users u
                ON u.telegram_id =
                    rr.assigned_master_id

            WHERE 1 = 1
        """

        params = []

        if status_filter == "new":
            sql += """
                AND rr.status = 'new'
            """

        elif status_filter == "in_work":
            sql += """
                AND rr.status = 'in_work'

                AND NOT EXISTS (
                    SELECT 1
                    FROM repairs rx
                    WHERE rx.request_id = rr.id
                    AND rx.status = 'rejected'
                    AND rx.id = (
                        SELECT MAX(rxx.id)
                        FROM repairs rxx
                        WHERE rxx.request_id = rr.id
                    )
                )
            """

        elif status_filter == "awaiting_approval":
            sql += """
                AND rr.status = 'awaiting_approval'
            """

        elif status_filter == "approved":
            sql += """
                AND rr.status = 'approved'
            """

        elif status_filter == "returned":
            sql += """
                AND rr.status = 'in_work'

                AND EXISTS (
                    SELECT 1
                    FROM repairs rx
                    WHERE rx.request_id = rr.id
                    AND rx.status = 'rejected'
                    AND rx.id = (
                        SELECT MAX(rxx.id)
                        FROM repairs rxx
                        WHERE rxx.request_id = rr.id
                    )
                )
            """

        sql += """
            ORDER BY rr.updated_at DESC, rr.id DESC
            LIMIT ?
        """

        params.append(
            limit
        )

        cursor = await db.execute(
            sql,
            params
        )

        rows = await cursor.fetchall()

        result = []

        for row in rows:
            item = dict(row)

            if (
                item["status"] == "in_work"
                and item[
                    "latest_repair_status"
                ] == "rejected"
            ):
                item[
                    "workflow_status"
                ] = "returned"

            else:
                item[
                    "workflow_status"
                ] = item["status"]

            result.append(
                item
            )

        return result


# =========================================================
# ПОДТВЕРЖДЕНИЕ РЕМОНТА
# =========================================================

async def approve_repair(
    repair_id: int,
    admin_id: int,
    admin_name: str
):
    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT
                id,
                request_id,
                status,
                master_telegram_id

            FROM repairs

            WHERE id = ?
        """, (
            repair_id,
        ))

        repair = await cursor.fetchone()

        if not repair:
            return {
                "success": False,
                "reason": "not_found"
            }

        if repair["status"] != "pending":
            return {
                "success": False,
                "reason": "already_processed"
            }

        request_id = repair["request_id"]

        await db.execute("""
            UPDATE repairs

            SET
                status = 'approved',
                approved_by = ?,
                approved_at = CURRENT_TIMESTAMP,
                rejection_reason = NULL,
                updated_at = CURRENT_TIMESTAMP

            WHERE id = ?
            AND status = 'pending'
        """, (
            admin_id,
            repair_id
        ))

        await db.execute("""
            UPDATE repair_requests

            SET
                status = 'approved',
                updated_at = CURRENT_TIMESTAMP,
                closed_at = CURRENT_TIMESTAMP

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
                user_name,
                reason
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id,
            repair_id,
            "repair_approved",
            "awaiting_approval",
            "approved",
            admin_id,
            admin_name,
            "Ремонт подтвержден администратором"
        ))

        await db.commit()

        return {
            "success": True,
            "request_id": request_id,
            "master_telegram_id": (
                repair["master_telegram_id"]
            )
        }


# =========================================================
# ВОЗВРАТ РЕМОНТА МАСТЕРУ
# =========================================================

async def reject_repair(
    repair_id: int,
    admin_id: int,
    admin_name: str,
    reason: str
):
    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
            SELECT
                id,
                request_id,
                status,
                master_telegram_id

            FROM repairs

            WHERE id = ?
        """, (
            repair_id,
        ))

        repair = await cursor.fetchone()

        if not repair:
            return {
                "success": False,
                "reason": "not_found"
            }

        if repair["status"] != "pending":
            return {
                "success": False,
                "reason": "already_processed"
            }

        request_id = repair["request_id"]

        await db.execute("""
            UPDATE repairs

            SET
                status = 'rejected',
                rejection_reason = ?,
                updated_at = CURRENT_TIMESTAMP

            WHERE id = ?
        """, (
            reason,
            repair_id
        ))

        await db.execute("""
            UPDATE repair_requests

            SET
                status = 'in_work',
                updated_at = CURRENT_TIMESTAMP,
                closed_at = NULL

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
                user_name,
                reason
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id,
            repair_id,
            "repair_returned",
            "awaiting_approval",
            "in_work",
            admin_id,
            admin_name,
            reason
        ))

        await db.commit()

        return {
            "success": True,
            "request_id": request_id,
            "master_telegram_id": (
                repair["master_telegram_id"]
            )
        }