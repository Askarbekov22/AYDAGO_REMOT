import os
import tempfile

from datetime import (
    datetime,
    timedelta,
    timezone
)

import aiosqlite
import xlsxwriter

from config import DATABASE_PATH


BISHKEK_TIMEZONE = timezone(
    timedelta(hours=6)
)


def get_period_dates(
    period: str
):
    now = datetime.now(
        BISHKEK_TIMEZONE
    )

    if period == "today":
        start_local = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        end_local = (
            start_local
            + timedelta(days=1)
        )

        title = (
            now.strftime(
                "%d.%m.%Y"
            )
        )

    elif period == "7days":
        start_local = (
            now - timedelta(days=6)
        ).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        end_local = (
            now + timedelta(days=1)
        ).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        title = "Последние 7 дней"

    elif period == "30days":
        start_local = (
            now - timedelta(days=29)
        ).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        end_local = (
            now + timedelta(days=1)
        ).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        title = "Последние 30 дней"

    elif period == "month":
        start_local = now.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        if now.month == 12:
            end_local = start_local.replace(
                year=now.year + 1,
                month=1
            )
        else:
            end_local = start_local.replace(
                month=now.month + 1
            )

        title = now.strftime(
            "%m.%Y"
        )

    else:
        return {
            "start": None,
            "end": None,
            "title": "Все время"
        }

    start_utc = (
        start_local
        .astimezone(timezone.utc)
        .replace(tzinfo=None)
    )

    end_utc = (
        end_local
        .astimezone(timezone.utc)
        .replace(tzinfo=None)
    )

    return {
        "start": start_utc.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "end": end_utc.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "title": title
    }


async def load_master_report_data(
    master_id: int,
    period: str
):
    period_data = get_period_dates(
        period
    )

    start = period_data["start"]
    end = period_data["end"]

    async with aiosqlite.connect(
        DATABASE_PATH
    ) as db:

        db.row_factory = (
            aiosqlite.Row
        )

        # =================================================
        # МАСТЕР
        # =================================================

        cursor = await db.execute("""
            SELECT
                full_name
            FROM users
            WHERE telegram_id = ?
        """, (
            master_id,
        ))

        master_row = (
            await cursor.fetchone()
        )

        master_name = (
            master_row["full_name"]
            if master_row
            else str(master_id)
        )

        # =================================================
        # РЕМОНТЫ
        # =================================================

        repair_sql = """
            SELECT
                r.id,
                r.repair_code,
                r.request_id,
                rr.request_code,
                r.bike_number,
                r.repair_type,
                r.description,
                r.status AS repair_status,
                rr.client_payment_status,
                rr.expected_amount,
                rr.paid_amount,
                r.created_at
            FROM repairs r

            LEFT JOIN repair_requests rr
                ON rr.id = r.request_id

            WHERE r.master_telegram_id = ?
        """

        repair_params = [
            master_id
        ]

        if (
            start is not None
            and end is not None
        ):
            repair_sql += """
                AND r.created_at >= ?
                AND r.created_at < ?
            """

            repair_params.extend([
                start,
                end
            ])

        repair_sql += """
            ORDER BY r.id DESC
        """

        cursor = await db.execute(
            repair_sql,
            repair_params
        )

        repairs = [
            dict(row)
            for row in await cursor.fetchall()
        ]

        repair_ids = [
            repair["id"]
            for repair in repairs
        ]

        request_ids = list({
            repair["request_id"]
            for repair in repairs
            if repair["request_id"]
            is not None
        })

        # =================================================
        # ЗАПЧАСТИ
        # =================================================

        parts = []

        if repair_ids:
            placeholders = ",".join(
                "?"
                for _ in repair_ids
            )

            cursor = await db.execute(
                f"""
                SELECT
                    rp.id,
                    rp.repair_id,
                    r.repair_code,
                    r.bike_number,
                    rp.part_name,
                    rp.quantity,
                    rp.source_type,
                    rp.donor_bike_number,
                    r.created_at
                FROM repair_parts rp

                LEFT JOIN repairs r
                    ON r.id = rp.repair_id

                WHERE rp.repair_id
                    IN ({placeholders})

                ORDER BY rp.id DESC
                """,
                repair_ids
            )

            parts = [
                dict(row)
                for row
                in await cursor.fetchall()
            ]

        # =================================================
        # ОПЛАТЫ
        # =================================================

        payments = []

        if request_ids:
            placeholders = ",".join(
                "?"
                for _ in request_ids
            )

            cursor = await db.execute(
                f"""
                SELECT
                    p.id,
                    p.request_id,
                    rr.request_code,
                    rr.bike_number,
                    p.repair_id,
                    r.repair_code,
                    p.amount,
                    p.payment_method,
                    p.accepted_by_name,
                    p.status,
                    p.created_at
                FROM payments p

                LEFT JOIN repair_requests rr
                    ON rr.id = p.request_id

                LEFT JOIN repairs r
                    ON r.id = p.repair_id

                WHERE p.request_id
                    IN ({placeholders})

                AND p.status = 'confirmed'

                ORDER BY p.id DESC
                """,
                request_ids
            )

            payments = [
                dict(row)
                for row
                in await cursor.fetchall()
            ]

        return {
            "master_name": master_name,
            "period_title": (
                period_data["title"]
            ),
            "repairs": repairs,
            "parts": parts,
            "payments": payments
        }


def payment_status_name(
    status
):
    names = {
        "paid": "Оплачено",
        "partial": "Частично оплачено",
        "unpaid": "Не оплачено"
    }

    return names.get(
        status,
        status or "-"
    )


def repair_status_name(
    status
):
    names = {
        "pending": "На подтверждении",
        "approved": "Подтвержден",
        "rejected": "Возвращен",
        "cancelled": "Отменен"
    }

    return names.get(
        status,
        status or "-"
    )


def repair_type_name(
    repair_type
):
    if repair_type == "part":
        return "С запчастью"

    if repair_type == "no_part":
        return "Без запчасти"

    return repair_type or "-"


def source_name(
    source
):
    names = {
        "warehouse": "Склад",
        "donor": "Донор"
    }

    return names.get(
        source,
        source or "-"
    )


def payment_method_name(
    method
):
    names = {
        "qr": "QR",
        "cash": "Наличные",
        "transfer": "Перевод"
    }

    return names.get(
        method,
        method or "-"
    )


def create_excel_report(
    data: dict
):
    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".xlsx"
    )

    temp_file.close()

    file_path = temp_file.name

    workbook = xlsxwriter.Workbook(
        file_path
    )

    # =====================================================
    # ФОРМАТЫ
    # =====================================================

    title_format = workbook.add_format({
        "bold": True,
        "font_size": 16,
        "align": "center",
        "valign": "vcenter"
    })

    subtitle_format = workbook.add_format({
        "bold": True,
        "font_size": 11
    })

    header_format = workbook.add_format({
        "bold": True,
        "border": 1,
        "align": "center",
        "valign": "vcenter",
        "text_wrap": True
    })

    cell_format = workbook.add_format({
        "border": 1,
        "valign": "top"
    })

    center_format = workbook.add_format({
        "border": 1,
        "align": "center",
        "valign": "top"
    })

    money_format = workbook.add_format({
        "border": 1,
        "num_format": '#,##0 "сом"',
        "align": "right"
    })

    summary_label = workbook.add_format({
        "bold": True,
        "border": 1
    })

    summary_value = workbook.add_format({
        "bold": True,
        "border": 1,
        "align": "center"
    })

    summary_money = workbook.add_format({
        "bold": True,
        "border": 1,
        "num_format": '#,##0 "сом"',
        "align": "right"
    })

    # =====================================================
    # ДАННЫЕ
    # =====================================================

    repairs = data["repairs"]
    parts = data["parts"]
    payments = data["payments"]

    total_repairs = len(
        repairs
    )

    repairs_with_parts = sum(
        1
        for repair in repairs
        if repair["repair_type"]
        == "part"
    )

    repairs_without_parts = sum(
        1
        for repair in repairs
        if repair["repair_type"]
        == "no_part"
    )

    unique_bikes = len({
        repair["bike_number"]
        for repair in repairs
    })

    total_parts = sum(
        int(part["quantity"] or 0)
        for part in parts
    )

    total_payments = sum(
        float(
            payment["amount"]
            or 0
        )
        for payment in payments
    )

    cash_total = sum(
        float(payment["amount"] or 0)
        for payment in payments
        if payment["payment_method"]
        == "cash"
    )

    qr_total = sum(
        float(payment["amount"] or 0)
        for payment in payments
        if payment["payment_method"]
        == "qr"
    )

    transfer_total = sum(
        float(payment["amount"] or 0)
        for payment in payments
        if payment["payment_method"]
        == "transfer"
    )

    paid_requests = sum(
        1
        for repair in repairs
        if repair[
            "client_payment_status"
        ] == "paid"
    )

    partial_requests = sum(
        1
        for repair in repairs
        if repair[
            "client_payment_status"
        ] == "partial"
    )

    unpaid_requests = sum(
        1
        for repair in repairs
        if repair[
            "client_payment_status"
        ] == "unpaid"
    )

    # =====================================================
    # ЛИСТ СВОДКА
    # =====================================================

    worksheet = workbook.add_worksheet(
        "Сводка"
    )

    worksheet.set_column(
        "A:A",
        32
    )

    worksheet.set_column(
        "B:B",
        22
    )

    worksheet.merge_range(
        "A1:B1",
        "AYDA GO — ОТЧЕТ МАСТЕРА",
        title_format
    )

    worksheet.write(
        "A3",
        "Мастер",
        summary_label
    )

    worksheet.write(
        "B3",
        data["master_name"],
        summary_value
    )

    worksheet.write(
        "A4",
        "Период",
        summary_label
    )

    worksheet.write(
        "B4",
        data["period_title"],
        summary_value
    )

    summary_rows = [
        (
            "Количество ремонтов",
            total_repairs,
            False
        ),
        (
            "Уникальных велосипедов",
            unique_bikes,
            False
        ),
        (
            "Ремонтов с запчастью",
            repairs_with_parts,
            False
        ),
        (
            "Ремонтов без запчасти",
            repairs_without_parts,
            False
        ),
        (
            "Использовано запчастей",
            total_parts,
            False
        ),
        (
            "Оплаченных ремонтов",
            paid_requests,
            False
        ),
        (
            "Частично оплаченных",
            partial_requests,
            False
        ),
        (
            "Неоплаченных",
            unpaid_requests,
            False
        ),
        (
            "Всего оплат",
            total_payments,
            True
        ),
        (
            "QR",
            qr_total,
            True
        ),
        (
            "Наличные",
            cash_total,
            True
        ),
        (
            "Перевод",
            transfer_total,
            True
        )
    ]

    start_row = 6

    for index, (
        label,
        value,
        is_money
    ) in enumerate(
        summary_rows,
        start=start_row
    ):
        worksheet.write(
            index,
            0,
            label,
            summary_label
        )

        if is_money:
            worksheet.write_number(
                index,
                1,
                float(value),
                summary_money
            )
        else:
            worksheet.write(
                index,
                1,
                value,
                summary_value
            )

    # =====================================================
    # ЛИСТ РЕМОНТЫ
    # =====================================================

    worksheet = workbook.add_worksheet(
        "Ремонты"
    )

    headers = [
        "№",
        "Ремонт",
        "Заявка",
        "Велосипед",
        "Тип ремонта",
        "Описание",
        "Статус ремонта",
        "Статус оплаты",
        "Ожидаемая сумма",
        "Оплачено",
        "Дата"
    ]

    for column, header in enumerate(
        headers
    ):
        worksheet.write(
            0,
            column,
            header,
            header_format
        )

    worksheet.freeze_panes(
        1,
        0
    )

    worksheet.autofilter(
        0,
        0,
        max(
            len(repairs),
            1
        ),
        len(headers) - 1
    )

    worksheet.set_column(
        "A:A",
        6
    )
    worksheet.set_column(
        "B:C",
        15
    )
    worksheet.set_column(
        "D:D",
        13
    )
    worksheet.set_column(
        "E:E",
        18
    )
    worksheet.set_column(
        "F:F",
        42
    )
    worksheet.set_column(
        "G:H",
        20
    )
    worksheet.set_column(
        "I:J",
        18
    )
    worksheet.set_column(
        "K:K",
        20
    )

    for row_index, repair in enumerate(
        repairs,
        start=1
    ):
        worksheet.write(
            row_index,
            0,
            row_index,
            center_format
        )

        worksheet.write(
            row_index,
            1,
            repair[
                "repair_code"
            ] or "-",
            cell_format
        )

        worksheet.write(
            row_index,
            2,
            repair[
                "request_code"
            ] or "-",
            cell_format
        )

        worksheet.write(
            row_index,
            3,
            repair[
                "bike_number"
            ],
            center_format
        )

        worksheet.write(
            row_index,
            4,
            repair_type_name(
                repair[
                    "repair_type"
                ]
            ),
            cell_format
        )

        worksheet.write(
            row_index,
            5,
            repair[
                "description"
            ] or "-",
            cell_format
        )

        worksheet.write(
            row_index,
            6,
            repair_status_name(
                repair[
                    "repair_status"
                ]
            ),
            cell_format
        )

        worksheet.write(
            row_index,
            7,
            payment_status_name(
                repair[
                    "client_payment_status"
                ]
            ),
            cell_format
        )

        worksheet.write_number(
            row_index,
            8,
            float(
                repair[
                    "expected_amount"
                ] or 0
            ),
            money_format
        )

        worksheet.write_number(
            row_index,
            9,
            float(
                repair[
                    "paid_amount"
                ] or 0
            ),
            money_format
        )

        worksheet.write(
            row_index,
            10,
            repair[
                "created_at"
            ] or "-",
            cell_format
        )

    # =====================================================
    # ЛИСТ ЗАПЧАСТИ
    # =====================================================

    worksheet = workbook.add_worksheet(
        "Запчасти"
    )

    headers = [
        "№",
        "Ремонт",
        "Велосипед",
        "Запчасть",
        "Количество",
        "Источник",
        "Номер донора",
        "Дата ремонта"
    ]

    for column, header in enumerate(
        headers
    ):
        worksheet.write(
            0,
            column,
            header,
            header_format
        )

    worksheet.freeze_panes(
        1,
        0
    )

    worksheet.autofilter(
        0,
        0,
        max(
            len(parts),
            1
        ),
        len(headers) - 1
    )

    worksheet.set_column(
        "A:A",
        6
    )
    worksheet.set_column(
        "B:B",
        15
    )
    worksheet.set_column(
        "C:C",
        13
    )
    worksheet.set_column(
        "D:D",
        30
    )
    worksheet.set_column(
        "E:E",
        12
    )
    worksheet.set_column(
        "F:F",
        15
    )
    worksheet.set_column(
        "G:G",
        16
    )
    worksheet.set_column(
        "H:H",
        20
    )

    for row_index, part in enumerate(
        parts,
        start=1
    ):
        worksheet.write(
            row_index,
            0,
            row_index,
            center_format
        )

        worksheet.write(
            row_index,
            1,
            part[
                "repair_code"
            ] or "-",
            cell_format
        )

        worksheet.write(
            row_index,
            2,
            part[
                "bike_number"
            ],
            center_format
        )

        worksheet.write(
            row_index,
            3,
            part[
                "part_name"
            ],
            cell_format
        )

        worksheet.write(
            row_index,
            4,
            part[
                "quantity"
            ],
            center_format
        )

        worksheet.write(
            row_index,
            5,
            source_name(
                part[
                    "source_type"
                ]
            ),
            cell_format
        )

        worksheet.write(
            row_index,
            6,
            part[
                "donor_bike_number"
            ] or "-",
            cell_format
        )

        worksheet.write(
            row_index,
            7,
            part[
                "created_at"
            ] or "-",
            cell_format
        )

    # =====================================================
    # ЛИСТ ОПЛАТЫ
    # =====================================================

    worksheet = workbook.add_worksheet(
        "Оплаты"
    )

    headers = [
        "№",
        "Заявка",
        "Ремонт",
        "Велосипед",
        "Сумма",
        "Способ оплаты",
        "Принял",
        "Статус",
        "Дата оплаты"
    ]

    for column, header in enumerate(
        headers
    ):
        worksheet.write(
            0,
            column,
            header,
            header_format
        )

    worksheet.freeze_panes(
        1,
        0
    )

    worksheet.autofilter(
        0,
        0,
        max(
            len(payments),
            1
        ),
        len(headers) - 1
    )

    worksheet.set_column(
        "A:A",
        6
    )
    worksheet.set_column(
        "B:C",
        15
    )
    worksheet.set_column(
        "D:D",
        13
    )
    worksheet.set_column(
        "E:E",
        18
    )
    worksheet.set_column(
        "F:F",
        18
    )
    worksheet.set_column(
        "G:G",
        25
    )
    worksheet.set_column(
        "H:H",
        15
    )
    worksheet.set_column(
        "I:I",
        20
    )

    for row_index, payment in enumerate(
        payments,
        start=1
    ):
        worksheet.write(
            row_index,
            0,
            row_index,
            center_format
        )

        worksheet.write(
            row_index,
            1,
            payment[
                "request_code"
            ] or "-",
            cell_format
        )

        worksheet.write(
            row_index,
            2,
            payment[
                "repair_code"
            ] or "-",
            cell_format
        )

        worksheet.write(
            row_index,
            3,
            payment[
                "bike_number"
            ] or "-",
            center_format
        )

        worksheet.write_number(
            row_index,
            4,
            float(
                payment[
                    "amount"
                ] or 0
            ),
            money_format
        )

        worksheet.write(
            row_index,
            5,
            payment_method_name(
                payment[
                    "payment_method"
                ]
            ),
            cell_format
        )

        worksheet.write(
            row_index,
            6,
            payment[
                "accepted_by_name"
            ] or "-",
            cell_format
        )

        worksheet.write(
            row_index,
            7,
            (
                "Подтвержден"
                if payment[
                    "status"
                ] == "confirmed"
                else payment[
                    "status"
                ]
            ),
            cell_format
        )

        worksheet.write(
            row_index,
            8,
            payment[
                "created_at"
            ] or "-",
            cell_format
        )

    workbook.close()

    return file_path