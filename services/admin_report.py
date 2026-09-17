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


# =========================================================
# ПЕРИОД
# =========================================================

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
            "Сегодня — "
            + now.strftime("%d.%m.%Y")
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
            "%B %Y"
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


def db_datetime_to_local(
    value
):
    if not value:
        return ""

    if isinstance(
        value,
        datetime
    ):
        dt = value

    else:
        try:
            dt = datetime.strptime(
                str(value),
                "%Y-%m-%d %H:%M:%S"
            )

        except ValueError:
            return str(value)

    dt = dt.replace(
        tzinfo=timezone.utc
    )

    return dt.astimezone(
        BISHKEK_TIMEZONE
    )


# =========================================================
# НАЗВАНИЯ
# =========================================================

def payer_name(
    value
):
    names = {
        "client": "Клиент",
        "company": "Компания"
    }

    return names.get(
        value,
        value or "-"
    )


def repair_type_name(
    value
):
    names = {
        "part": "С запчастью",
        "no_part": "Без запчасти"
    }

    return names.get(
        value,
        value or "-"
    )


def source_name(
    value
):
    names = {
        "warehouse": "Склад",
        "donor": "Донор"
    }

    return names.get(
        value,
        value or "-"
    )


def repair_status_name(
    value
):
    names = {
        "pending": "На проверке",
        "approved": "Подтвержден",
        "rejected": "Возвращен",
        "cancelled": "Отменен"
    }

    return names.get(
        value,
        value or "-"
    )


def payment_method_name(
    value
):
    names = {
        "qr": "QR",
        "cash": "Наличные",
        "transfer": "Перевод"
    }

    return names.get(
        value,
        value or "-"
    )


# =========================================================
# ДАННЫЕ
# =========================================================

async def load_admin_report_data(
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

        db.row_factory = aiosqlite.Row

        # =================================================
        # РЕМОНТЫ
        # =================================================

        repair_sql = """
            SELECT
                r.id,
                r.repair_code,
                r.request_id,
                rr.request_code,

                r.master_telegram_id,
                u.full_name AS master_name,

                r.bike_number,
                r.payer_type,
                r.repair_type,
                r.description,
                r.company_reason,
                r.total_amount,
                r.status,

                rr.client_payment_status,
                rr.expected_amount,
                rr.paid_amount,

                r.created_at

            FROM repairs r

            LEFT JOIN repair_requests rr
                ON rr.id = r.request_id

            LEFT JOIN users u
                ON u.telegram_id =
                    r.master_telegram_id

            WHERE 1 = 1
        """

        params = []

        if (
            start is not None
            and end is not None
        ):
            repair_sql += """
                AND r.created_at >= ?
                AND r.created_at < ?
            """

            params.extend([
                start,
                end
            ])

        repair_sql += """
            ORDER BY r.created_at DESC
        """

        cursor = await db.execute(
            repair_sql,
            params
        )

        repairs = [
            dict(row)
            for row in await cursor.fetchall()
        ]

        # =================================================
        # ЗАПЧАСТИ
        # =================================================

        repair_ids = [
            repair["id"]
            for repair in repairs
        ]

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
                    r.master_telegram_id,

                    u.full_name AS master_name,

                    rp.part_name,
                    rp.quantity,
                    rp.source_type,
                    rp.donor_bike_number,

                    r.status AS repair_status,
                    r.created_at

                FROM repair_parts rp

                LEFT JOIN repairs r
                    ON r.id = rp.repair_id

                LEFT JOIN users u
                    ON u.telegram_id =
                        r.master_telegram_id

                WHERE rp.repair_id
                    IN ({placeholders})

                ORDER BY r.created_at DESC
                """,
                repair_ids
            )

            parts = [
                dict(row)
                for row in await cursor.fetchall()
            ]

        # =================================================
        # ОПЛАТЫ
        # =================================================

        payment_sql = """
            SELECT
                p.id,
                p.request_id,
                p.repair_id,

                rr.request_code,
                rr.bike_number,

                r.repair_code,
                r.master_telegram_id,

                u.full_name AS master_name,

                p.amount,
                p.payment_method,

                p.accepted_by,
                p.accepted_by_name,

                p.status,
                p.created_at

            FROM payments p

            LEFT JOIN repair_requests rr
                ON rr.id = p.request_id

            LEFT JOIN repairs r
                ON r.id = p.repair_id

            LEFT JOIN users u
                ON u.telegram_id =
                    r.master_telegram_id

            WHERE p.status = 'confirmed'
        """

        payment_params = []

        if (
            start is not None
            and end is not None
        ):
            payment_sql += """
                AND p.created_at >= ?
                AND p.created_at < ?
            """

            payment_params.extend([
                start,
                end
            ])

        payment_sql += """
            ORDER BY p.created_at DESC
        """

        cursor = await db.execute(
            payment_sql,
            payment_params
        )

        payments = [
            dict(row)
            for row in await cursor.fetchall()
        ]

        return {
            "period_title": (
                period_data["title"]
            ),
            "generated_at": datetime.now(
                BISHKEK_TIMEZONE
            ),
            "repairs": repairs,
            "parts": parts,
            "payments": payments
        }


# =========================================================
# EXCEL
# =========================================================

def create_admin_excel_report(
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

    workbook.set_properties({
        "title": (
            "AYDA GO — Общий отчет по ремонтам"
        ),
        "company": "AYDA GO"
    })

    # =====================================================
    # ЦВЕТА
    # =====================================================

    DARK_BLUE = "#16324F"
    BLUE = "#1F4E78"
    LIGHT_BLUE = "#D9EAF7"

    GREEN = "#2E7D32"
    LIGHT_GREEN = "#E2F0D9"

    ORANGE = "#E67E22"
    LIGHT_ORANGE = "#FCE4D6"

    RED = "#C62828"
    LIGHT_RED = "#F4CCCC"

    GRAY = "#F2F2F2"
    WHITE = "#FFFFFF"
    BLACK = "#222222"

    BORDER = "#D9E1F2"

    # =====================================================
    # ФОРМАТЫ
    # =====================================================

    title = workbook.add_format({
        "bold": True,
        "font_size": 20,
        "font_color": WHITE,
        "bg_color": DARK_BLUE,
        "align": "center",
        "valign": "vcenter"
    })

    info = workbook.add_format({
        "font_size": 10,
        "font_color": "#666666"
    })

    section = workbook.add_format({
        "bold": True,
        "font_color": WHITE,
        "bg_color": DARK_BLUE,
        "align": "left"
    })

    header = workbook.add_format({
        "bold": True,
        "font_color": WHITE,
        "bg_color": DARK_BLUE,
        "border": 1,
        "border_color": WHITE,
        "align": "center",
        "valign": "vcenter",
        "text_wrap": True
    })

    cell = workbook.add_format({
        "border": 1,
        "border_color": BORDER,
        "valign": "top"
    })

    cell_center = workbook.add_format({
        "border": 1,
        "border_color": BORDER,
        "align": "center",
        "valign": "vcenter"
    })

    cell_wrap = workbook.add_format({
        "border": 1,
        "border_color": BORDER,
        "valign": "top",
        "text_wrap": True
    })

    money = workbook.add_format({
        "border": 1,
        "border_color": BORDER,
        "num_format": '#,##0 "сом"',
        "align": "right"
    })

    date_format = workbook.add_format({
        "border": 1,
        "border_color": BORDER,
        "align": "center",
        "num_format": "dd.mm.yyyy hh:mm"
    })

    kpi_title = workbook.add_format({
        "bold": True,
        "font_color": WHITE,
        "bg_color": BLUE,
        "border": 1,
        "border_color": BLUE,
        "align": "center",
        "valign": "vcenter"
    })

    kpi_value = workbook.add_format({
        "bold": True,
        "font_size": 22,
        "font_color": DARK_BLUE,
        "bg_color": LIGHT_BLUE,
        "border": 1,
        "border_color": BLUE,
        "align": "center",
        "valign": "vcenter"
    })

    kpi_money_title = workbook.add_format({
        "bold": True,
        "font_color": WHITE,
        "bg_color": GREEN,
        "border": 1,
        "border_color": GREEN,
        "align": "center"
    })

    kpi_money_value = workbook.add_format({
        "bold": True,
        "font_size": 19,
        "font_color": GREEN,
        "bg_color": LIGHT_GREEN,
        "border": 1,
        "border_color": GREEN,
        "num_format": '#,##0 "сом"',
        "align": "center",
        "valign": "vcenter"
    })

    kpi_parts_title = workbook.add_format({
        "bold": True,
        "font_color": WHITE,
        "bg_color": ORANGE,
        "border": 1,
        "border_color": ORANGE,
        "align": "center"
    })

    kpi_parts_value = workbook.add_format({
        "bold": True,
        "font_size": 19,
        "font_color": ORANGE,
        "bg_color": LIGHT_ORANGE,
        "border": 1,
        "border_color": ORANGE,
        "align": "center",
        "valign": "vcenter"
    })

    total_label = workbook.add_format({
        "bold": True,
        "font_color": WHITE,
        "bg_color": DARK_BLUE,
        "border": 1,
        "border_color": DARK_BLUE
    })

    total_value = workbook.add_format({
        "bold": True,
        "font_color": WHITE,
        "bg_color": DARK_BLUE,
        "border": 1,
        "border_color": DARK_BLUE,
        "align": "center"
    })

    total_money = workbook.add_format({
        "bold": True,
        "font_color": WHITE,
        "bg_color": DARK_BLUE,
        "border": 1,
        "border_color": DARK_BLUE,
        "num_format": '#,##0 "сом"',
        "align": "right"
    })

    # =====================================================
    # ПОКАЗАТЕЛИ
    # =====================================================

    repairs = data["repairs"]
    parts = data["parts"]
    payments = data["payments"]

    total_repairs = len(
        repairs
    )

    company_repairs = sum(
        1
        for repair in repairs
        if repair.get("payer_type")
        == "company"
    )

    client_repairs = sum(
        1
        for repair in repairs
        if repair.get("payer_type")
        == "client"
    )

    with_parts = sum(
        1
        for repair in repairs
        if repair.get("repair_type")
        == "part"
    )

    without_parts = sum(
        1
        for repair in repairs
        if repair.get("repair_type")
        == "no_part"
    )

    approved = sum(
        1
        for repair in repairs
        if repair.get("status")
        == "approved"
    )

    pending = sum(
        1
        for repair in repairs
        if repair.get("status")
        == "pending"
    )

    rejected = sum(
        1
        for repair in repairs
        if repair.get("status")
        == "rejected"
    )

    total_parts = sum(
        int(
            part.get("quantity")
            or 0
        )
        for part in parts
    )

    warehouse_parts = sum(
        int(
            part.get("quantity")
            or 0
        )
        for part in parts
        if part.get("source_type")
        == "warehouse"
    )

    donor_parts = sum(
        int(
            part.get("quantity")
            or 0
        )
        for part in parts
        if part.get("source_type")
        == "donor"
    )

    total_income = sum(
        float(
            payment.get("amount")
            or 0
        )
        for payment in payments
    )

    qr_total = sum(
        float(
            payment.get("amount")
            or 0
        )
        for payment in payments
        if payment.get(
            "payment_method"
        ) == "qr"
    )

    cash_total = sum(
        float(
            payment.get("amount")
            or 0
        )
        for payment in payments
        if payment.get(
            "payment_method"
        ) == "cash"
    )

    transfer_total = sum(
        float(
            payment.get("amount")
            or 0
        )
        for payment in payments
        if payment.get(
            "payment_method"
        ) == "transfer"
    )

    unique_bikes = len({
        repair.get("bike_number")
        for repair in repairs
        if repair.get("bike_number")
    })

    # =====================================================
    # СВОДКА
    # =====================================================

    ws = workbook.add_worksheet(
        "Сводка"
    )

    ws.hide_gridlines(2)

    ws.set_column(
        "A:A",
        3
    )

    ws.set_column(
        "B:H",
        17
    )

    ws.set_row(
        1,
        38
    )

    ws.merge_range(
        "B2:H2",
        "AYDA GO — ОБЩИЙ ОТЧЕТ ПО РЕМОНТАМ",
        title
    )

    ws.write(
        "B4",
        f"Период: "
        f"{data['period_title']}",
        info
    )

    ws.write(
        "B5",
        "Дата формирования: "
        + data["generated_at"].strftime(
            "%d.%m.%Y %H:%M"
        ),
        info
    )

    # KPI
    ws.merge_range(
        "B8:C8",
        "Всего ремонтов",
        kpi_title
    )

    ws.merge_range(
        "B9:C10",
        total_repairs,
        kpi_value
    )

    ws.merge_range(
        "D8:E8",
        "За счет компании",
        kpi_title
    )

    ws.merge_range(
        "D9:E10",
        company_repairs,
        kpi_value
    )

    ws.merge_range(
        "F8:G8",
        "За счет клиентов",
        kpi_title
    )

    ws.merge_range(
        "F9:G10",
        client_repairs,
        kpi_value
    )

    ws.merge_range(
        "B13:D13",
        "Поступления",
        kpi_money_title
    )

    ws.merge_range(
        "B14:D15",
        total_income,
        kpi_money_value
    )

    ws.merge_range(
        "E13:G13",
        "Использовано запчастей",
        kpi_parts_title
    )

    ws.merge_range(
        "E14:G15",
        total_parts,
        kpi_parts_value
    )

    # Оплаты
    ws.merge_range(
        "B18:G18",
        "ОПЛАТЫ",
        section
    )

    ws.write(
        "B20",
        "QR",
        total_label
    )

    ws.write(
        "C20",
        qr_total,
        total_money
    )

    ws.write(
        "D20",
        "Наличные",
        total_label
    )

    ws.write(
        "E20",
        cash_total,
        total_money
    )

    ws.write(
        "F20",
        "Перевод",
        total_label
    )

    ws.write(
        "G20",
        transfer_total,
        total_money
    )

    # Ремонты
    ws.merge_range(
        "B23:G23",
        "РЕМОНТЫ",
        section
    )

    repair_stats = [
        (
            "С запчастью",
            with_parts
        ),
        (
            "Без запчасти",
            without_parts
        ),
        (
            "Подтверждено",
            approved
        ),
        (
            "На проверке",
            pending
        ),
        (
            "Возвращено",
            rejected
        ),
        (
            "Уникальных велосипедов",
            unique_bikes
        )
    ]

    for index, (
        label,
        value
    ) in enumerate(
        repair_stats
    ):
        row = 24 + (
            index // 3
        )

        col = 1 + (
            index % 3
        ) * 2

        ws.write(
            row,
            col,
            label,
            total_label
        )

        ws.write(
            row,
            col + 1,
            value,
            total_value
        )

    # Запчасти
    ws.merge_range(
        "B29:G29",
        "ЗАПЧАСТИ",
        section
    )

    ws.write(
        "B31",
        "Со склада",
        total_label
    )

    ws.write(
        "C31",
        warehouse_parts,
        total_value
    )

    ws.write(
        "D31",
        "С донора",
        total_label
    )

    ws.write(
        "E31",
        donor_parts,
        total_value
    )

    ws.write(
        "F31",
        "Всего",
        total_label
    )

    ws.write(
        "G31",
        total_parts,
        total_value
    )

    # =====================================================
    # РЕМОНТЫ
    # =====================================================

    ws = workbook.add_worksheet(
        "Ремонты"
    )

    ws.hide_gridlines(2)

    headers = [
        "ID ремонта",
        "Дата",
        "Мастер",
        "Telegram ID",
        "Велосипед",
        "За чей счет",
        "Тип ремонта",
        "Описание",
        "Причина компании",
        "Сумма",
        "Статус"
    ]

    for col, value in enumerate(
        headers
    ):
        ws.write(
            0,
            col,
            value,
            header
        )

    widths = [
        15,
        20,
        25,
        16,
        14,
        17,
        19,
        38,
        30,
        16,
        18
    ]

    for index, width in enumerate(
        widths
    ):
        ws.set_column(
            index,
            index,
            width
        )

    ws.set_row(
        0,
        30
    )

    for row_index, repair in enumerate(
        repairs,
        start=1
    ):
        local_date = db_datetime_to_local(
            repair.get("created_at")
        )

        ws.write(
            row_index,
            0,
            repair.get(
                "repair_code"
            ) or "-",
            cell_center
        )

        if isinstance(
            local_date,
            datetime
        ):
            ws.write_datetime(
                row_index,
                1,
                local_date.replace(
                    tzinfo=None
                ),
                date_format
            )
        else:
            ws.write(
                row_index,
                1,
                local_date,
                cell_center
            )

        ws.write(
            row_index,
            2,
            repair.get(
                "master_name"
            ) or "-",
            cell
        )

        ws.write(
            row_index,
            3,
            repair.get(
                "master_telegram_id"
            ),
            cell_center
        )

        ws.write(
            row_index,
            4,
            repair.get(
                "bike_number"
            ) or "-",
            cell_center
        )

        ws.write(
            row_index,
            5,
            payer_name(
                repair.get(
                    "payer_type"
                )
            ),
            cell_center
        )

        ws.write(
            row_index,
            6,
            repair_type_name(
                repair.get(
                    "repair_type"
                )
            ),
            cell_center
        )

        ws.write(
            row_index,
            7,
            repair.get(
                "description"
            ) or "-",
            cell_wrap
        )

        ws.write(
            row_index,
            8,
            repair.get(
                "company_reason"
            ) or "-",
            cell_wrap
        )

        ws.write_number(
            row_index,
            9,
            float(
                repair.get(
                    "total_amount"
                ) or 0
            ),
            money
        )

        ws.write(
            row_index,
            10,
            repair_status_name(
                repair.get(
                    "status"
                )
            ),
            cell_center
        )

    if repairs:
        ws.autofilter(
            0,
            0,
            len(repairs),
            len(headers) - 1
        )

    ws.freeze_panes(
        1,
        0
    )

    # =====================================================
    # ЗАПЧАСТИ
    # =====================================================

    ws = workbook.add_worksheet(
        "Запчасти"
    )

    ws.hide_gridlines(2)

    headers = [
        "ID ремонта",
        "Дата",
        "Мастер",
        "Велосипед",
        "Запчасть",
        "Количество",
        "Источник",
        "Донор",
        "Статус ремонта"
    ]

    for col, value in enumerate(
        headers
    ):
        ws.write(
            0,
            col,
            value,
            header
        )

    widths = [
        15,
        20,
        25,
        14,
        30,
        14,
        18,
        16,
        20
    ]

    for index, width in enumerate(
        widths
    ):
        ws.set_column(
            index,
            index,
            width
        )

    for row_index, part in enumerate(
        parts,
        start=1
    ):
        local_date = db_datetime_to_local(
            part.get("created_at")
        )

        ws.write(
            row_index,
            0,
            part.get(
                "repair_code"
            ) or "-",
            cell_center
        )

        if isinstance(
            local_date,
            datetime
        ):
            ws.write_datetime(
                row_index,
                1,
                local_date.replace(
                    tzinfo=None
                ),
                date_format
            )
        else:
            ws.write(
                row_index,
                1,
                local_date,
                cell_center
            )

        ws.write(
            row_index,
            2,
            part.get(
                "master_name"
            ) or "-",
            cell
        )

        ws.write(
            row_index,
            3,
            part.get(
                "bike_number"
            ) or "-",
            cell_center
        )

        ws.write(
            row_index,
            4,
            part.get(
                "part_name"
            ) or "-",
            cell
        )

        ws.write(
            row_index,
            5,
            int(
                part.get(
                    "quantity"
                ) or 0
            ),
            cell_center
        )

        ws.write(
            row_index,
            6,
            source_name(
                part.get(
                    "source_type"
                )
            ),
            cell_center
        )

        ws.write(
            row_index,
            7,
            part.get(
                "donor_bike_number"
            ) or "-",
            cell_center
        )

        ws.write(
            row_index,
            8,
            repair_status_name(
                part.get(
                    "repair_status"
                )
            ),
            cell_center
        )

    if parts:
        ws.autofilter(
            0,
            0,
            len(parts),
            len(headers) - 1
        )

    ws.freeze_panes(
        1,
        0
    )

    # =====================================================
    # ОПЛАТЫ
    # =====================================================

    ws = workbook.add_worksheet(
        "Оплаты"
    )

    ws.hide_gridlines(2)

    headers = [
        "ID платежа",
        "Дата",
        "Ремонт",
        "Велосипед",
        "Мастер",
        "Сумма",
        "Способ оплаты",
        "Принял оплату"
    ]

    for col, value in enumerate(
        headers
    ):
        ws.write(
            0,
            col,
            value,
            header
        )

    widths = [
        14,
        20,
        15,
        14,
        25,
        17,
        18,
        25
    ]

    for index, width in enumerate(
        widths
    ):
        ws.set_column(
            index,
            index,
            width
        )

    for row_index, payment in enumerate(
        payments,
        start=1
    ):
        local_date = db_datetime_to_local(
            payment.get(
                "created_at"
            )
        )

        ws.write(
            row_index,
            0,
            payment.get("id"),
            cell_center
        )

        if isinstance(
            local_date,
            datetime
        ):
            ws.write_datetime(
                row_index,
                1,
                local_date.replace(
                    tzinfo=None
                ),
                date_format
            )
        else:
            ws.write(
                row_index,
                1,
                local_date,
                cell_center
            )

        ws.write(
            row_index,
            2,
            payment.get(
                "repair_code"
            ) or "-",
            cell_center
        )

        ws.write(
            row_index,
            3,
            payment.get(
                "bike_number"
            ) or "-",
            cell_center
        )

        ws.write(
            row_index,
            4,
            payment.get(
                "master_name"
            ) or "-",
            cell
        )

        ws.write_number(
            row_index,
            5,
            float(
                payment.get(
                    "amount"
                ) or 0
            ),
            money
        )

        ws.write(
            row_index,
            6,
            payment_method_name(
                payment.get(
                    "payment_method"
                )
            ),
            cell_center
        )

        ws.write(
            row_index,
            7,
            payment.get(
                "accepted_by_name"
            ) or "-",
            cell
        )

    if payments:
        total_row = (
            len(payments) + 2
        )

        ws.merge_range(
            total_row,
            0,
            total_row,
            4,
            "ИТОГО ПО ОПЛАТАМ",
            total_label
        )

        ws.write_number(
            total_row,
            5,
            total_income,
            total_money
        )

        ws.autofilter(
            0,
            0,
            len(payments),
            len(headers) - 1
        )

    ws.freeze_panes(
        1,
        0
    )

    # =====================================================
    # МАСТЕРА
    # =====================================================

    master_stats = {}

    for repair in repairs:
        master_id = repair.get(
            "master_telegram_id"
        )

        if master_id not in master_stats:
            master_stats[master_id] = {
                "name": (
                    repair.get(
                        "master_name"
                    ) or "-"
                ),
                "telegram_id": master_id,
                "repairs": 0,
                "company": 0,
                "client": 0,
                "with_parts": 0,
                "without_parts": 0,
                "approved": 0,
                "pending": 0,
                "rejected": 0,
                "parts": 0
            }

        stats = master_stats[
            master_id
        ]

        stats["repairs"] += 1

        if repair.get(
            "payer_type"
        ) == "company":
            stats["company"] += 1

        if repair.get(
            "payer_type"
        ) == "client":
            stats["client"] += 1

        if repair.get(
            "repair_type"
        ) == "part":
            stats["with_parts"] += 1

        if repair.get(
            "repair_type"
        ) == "no_part":
            stats["without_parts"] += 1

        if repair.get(
            "status"
        ) == "approved":
            stats["approved"] += 1

        elif repair.get(
            "status"
        ) == "pending":
            stats["pending"] += 1

        elif repair.get(
            "status"
        ) == "rejected":
            stats["rejected"] += 1

    for part in parts:
        master_id = part.get(
            "master_telegram_id"
        )

        if master_id in master_stats:
            master_stats[
                master_id
            ]["parts"] += int(
                part.get(
                    "quantity"
                ) or 0
            )

    for payment in payments:
        master_id = payment.get(
            "master_telegram_id"
        )

        if master_id in master_stats:
            if "income" not in master_stats[
                master_id
            ]:
                master_stats[
                    master_id
                ]["income"] = 0

            master_stats[
                master_id
            ]["income"] += float(
                payment.get(
                    "amount"
                ) or 0
            )

    ws = workbook.add_worksheet(
        "Мастера"
    )

    ws.hide_gridlines(2)

    headers = [
        "Мастер",
        "Telegram ID",
        "Ремонтов",
        "Компания",
        "Клиенты",
        "С запчастью",
        "Без запчасти",
        "Запчастей",
        "Подтверждено",
        "На проверке",
        "Возвращено",
        "Поступления"
    ]

    for col, value in enumerate(
        headers
    ):
        ws.write(
            0,
            col,
            value,
            header
        )

    widths = [
        26,
        17,
        12,
        12,
        12,
        15,
        17,
        13,
        17,
        16,
        15,
        18
    ]

    for index, width in enumerate(
        widths
    ):
        ws.set_column(
            index,
            index,
            width
        )

    sorted_masters = sorted(
        master_stats.values(),
        key=lambda item: (
            item["repairs"]
        ),
        reverse=True
    )

    for row_index, stats in enumerate(
        sorted_masters,
        start=1
    ):
        ws.write(
            row_index,
            0,
            stats["name"],
            cell
        )

        ws.write(
            row_index,
            1,
            stats["telegram_id"],
            cell_center
        )

        ws.write(
            row_index,
            2,
            stats["repairs"],
            cell_center
        )

        ws.write(
            row_index,
            3,
            stats["company"],
            cell_center
        )

        ws.write(
            row_index,
            4,
            stats["client"],
            cell_center
        )

        ws.write(
            row_index,
            5,
            stats["with_parts"],
            cell_center
        )

        ws.write(
            row_index,
            6,
            stats["without_parts"],
            cell_center
        )

        ws.write(
            row_index,
            7,
            stats["parts"],
            cell_center
        )

        ws.write(
            row_index,
            8,
            stats["approved"],
            cell_center
        )

        ws.write(
            row_index,
            9,
            stats["pending"],
            cell_center
        )

        ws.write(
            row_index,
            10,
            stats["rejected"],
            cell_center
        )

        ws.write_number(
            row_index,
            11,
            float(
                stats.get(
                    "income",
                    0
                )
            ),
            money
        )

    if sorted_masters:
        ws.autofilter(
            0,
            0,
            len(sorted_masters),
            len(headers) - 1
        )

    ws.freeze_panes(
        1,
        0
    )

    workbook.close()

    return file_path