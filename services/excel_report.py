import os
from datetime import datetime

import xlsxwriter


def payer_name(value):
    if value == "company":
        return "Компания"

    if value == "client":
        return "Клиент"

    return value or ""


def repair_type_name(value):
    if value == "part":
        return "С запчастью"

    if value == "no_part":
        return "Без запчасти"

    return value or ""


def source_name(value):
    if value == "warehouse":
        return "Склад"

    if value == "donor":
        return "Донор"

    return ""


def status_name(value):
    statuses = {
        "pending": "На проверке",
        "approved": "Подтвержден",
        "rejected": "Отклонен",
        "cancelled": "Отменен"
    }

    return statuses.get(
        value,
        value or ""
    )


def period_name(period):
    names = {
        "today": "Сегодня",
        "7days": "Последние 7 дней",
        "month": "Текущий месяц"
    }

    return names.get(
        period,
        "Отчет"
    )


def create_excel_report(
    data: dict,
    period: str,
    master_name: str,
    master_telegram_id: int
):
    os.makedirs(
        "reports",
        exist_ok=True
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    file_path = os.path.join(
        "reports",
        f"AYDA_REPAIR_REPORT_{timestamp}.xlsx"
    )

    workbook = xlsxwriter.Workbook(
        file_path
    )

    workbook.set_properties({
        "title": "AYDA GO — отчет по ремонтам",
        "subject": "Учет ремонтов",
        "author": "AYDA GO",
        "company": "AYDA GO"
    })

    # =====================================================
    # ФОРМАТЫ
    # =====================================================

    title_format = workbook.add_format({
        "bold": True,
        "font_size": 22,
        "font_color": "#FFFFFF",
        "bg_color": "#111827",
        "align": "left",
        "valign": "vcenter"
    })

    subtitle_format = workbook.add_format({
        "font_size": 11,
        "font_color": "#4B5563"
    })

    section_format = workbook.add_format({
        "bold": True,
        "font_size": 13,
        "font_color": "#FFFFFF",
        "bg_color": "#1F2937",
        "align": "left",
        "valign": "vcenter"
    })

    header_format = workbook.add_format({
        "bold": True,
        "font_color": "#FFFFFF",
        "bg_color": "#374151",
        "border": 1,
        "border_color": "#D1D5DB",
        "align": "center",
        "valign": "vcenter",
        "text_wrap": True
    })

    normal_format = workbook.add_format({
        "border": 1,
        "border_color": "#E5E7EB",
        "valign": "top"
    })

    wrap_format = workbook.add_format({
        "border": 1,
        "border_color": "#E5E7EB",
        "valign": "top",
        "text_wrap": True
    })

    center_format = workbook.add_format({
        "border": 1,
        "border_color": "#E5E7EB",
        "align": "center",
        "valign": "vcenter"
    })

    money_format = workbook.add_format({
        "border": 1,
        "border_color": "#E5E7EB",
        "num_format": '#,##0 "сом"',
        "align": "right"
    })

    date_format = workbook.add_format({
        "border": 1,
        "border_color": "#E5E7EB",
        "num_format": "dd.mm.yyyy hh:mm",
        "align": "center"
    })

    kpi_label_format = workbook.add_format({
        "bold": True,
        "font_color": "#4B5563",
        "bg_color": "#F3F4F6",
        "border": 1,
        "border_color": "#D1D5DB",
        "align": "center",
        "valign": "vcenter"
    })

    kpi_value_format = workbook.add_format({
        "bold": True,
        "font_size": 20,
        "font_color": "#111827",
        "bg_color": "#FFFFFF",
        "border": 1,
        "border_color": "#D1D5DB",
        "align": "center",
        "valign": "vcenter"
    })

    kpi_money_format = workbook.add_format({
        "bold": True,
        "font_size": 20,
        "font_color": "#111827",
        "bg_color": "#FFFFFF",
        "border": 1,
        "border_color": "#D1D5DB",
        "align": "center",
        "valign": "vcenter",
        "num_format": '#,##0 "сом"'
    })

    # =====================================================
    # ДАННЫЕ
    # =====================================================

    repairs = data.get(
        "repairs",
        []
    )

    parts = data.get(
        "parts",
        []
    )

    payments = data.get(
        "payments",
        []
    )

    total_repairs = len(
        repairs
    )

    company_repairs = sum(
        1
        for item in repairs
        if item["payer_type"] == "company"
    )

    client_repairs = sum(
        1
        for item in repairs
        if item["payer_type"] == "client"
    )

    approved_repairs = sum(
        1
        for item in repairs
        if item["status"] == "approved"
    )

    pending_repairs = sum(
        1
        for item in repairs
        if item["status"] == "pending"
    )

    total_payments = sum(
        float(item["amount"] or 0)
        for item in payments
    )

    total_parts = sum(
        int(item["quantity"] or 0)
        for item in parts
    )

    # =====================================================
    # ЛИСТ СВОДКА
    # =====================================================

    summary = workbook.add_worksheet(
        "Сводка"
    )

    summary.hide_gridlines(2)

    summary.set_column(
        "A:A",
        3
    )

    summary.set_column(
        "B:H",
        18
    )

    summary.set_row(
        1,
        36
    )

    summary.merge_range(
        "B2:H2",
        "AYDA GO — ОТЧЕТ ПО РЕМОНТАМ",
        title_format
    )

    summary.write(
        "B4",
        f"Период: {period_name(period)}",
        subtitle_format
    )

    summary.write(
        "B5",
        f"Мастер: {master_name}",
        subtitle_format
    )

    summary.write(
        "B6",
        f"Telegram ID: {master_telegram_id}",
        subtitle_format
    )

    summary.write(
        "B7",
        "Дата формирования: "
        + datetime.now().strftime(
            "%d.%m.%Y %H:%M"
        ),
        subtitle_format
    )

    # KPI 1

    summary.merge_range(
        "B10:C10",
        "Всего ремонтов",
        kpi_label_format
    )

    summary.merge_range(
        "B11:C12",
        total_repairs,
        kpi_value_format
    )

    # KPI 2

    summary.merge_range(
        "D10:E10",
        "За счет компании",
        kpi_label_format
    )

    summary.merge_range(
        "D11:E12",
        company_repairs,
        kpi_value_format
    )

    # KPI 3

    summary.merge_range(
        "F10:G10",
        "За счет клиентов",
        kpi_label_format
    )

    summary.merge_range(
        "F11:G12",
        client_repairs,
        kpi_value_format
    )

    # KPI деньги

    summary.merge_range(
        "B15:D15",
        "Поступления",
        kpi_label_format
    )

    summary.merge_range(
        "B16:D17",
        total_payments,
        kpi_money_format
    )

    # KPI детали

    summary.merge_range(
        "E15:G15",
        "Использовано запчастей",
        kpi_label_format
    )

    summary.merge_range(
        "E16:G17",
        total_parts,
        kpi_value_format
    )

    # Статусы

    summary.merge_range(
        "B20:G20",
        "СТАТУСЫ РЕМОНТОВ",
        section_format
    )

    summary.write(
        "B22",
        "На проверке",
        kpi_label_format
    )

    summary.write(
        "C22",
        pending_repairs,
        kpi_value_format
    )

    summary.write(
        "E22",
        "Подтверждено",
        kpi_label_format
    )

    summary.write(
        "F22",
        approved_repairs,
        kpi_value_format
    )

    # ТОП ЗАПЧАСТЕЙ

    part_totals = {}

    for part in parts:
        name = (
            part["part_name"]
            or "Без названия"
        )

        part_totals[name] = (
            part_totals.get(
                name,
                0
            )
            + int(
                part["quantity"]
                or 0
            )
        )

    summary.merge_range(
        "B25:G25",
        "ИСПОЛЬЗОВАННЫЕ ЗАПЧАСТИ",
        section_format
    )

    summary.write(
        "B27",
        "Запчасть",
        header_format
    )

    summary.write(
        "C27",
        "Количество",
        header_format
    )

    row = 27

    for part_name, quantity in sorted(
        part_totals.items(),
        key=lambda item: item[1],
        reverse=True
    ):
        summary.write(
            row,
            1,
            part_name,
            normal_format
        )

        summary.write(
            row,
            2,
            quantity,
            center_format
        )

        row += 1

    # =====================================================
    # ЛИСТ РЕМОНТЫ
    # =====================================================

    repair_sheet = workbook.add_worksheet(
        "Ремонты"
    )

    repair_sheet.hide_gridlines(2)

    headers = [
        "ID ремонта",
        "Дата",
        "Мастер ID",
        "Велосипед",
        "За чей счет",
        "Тип ремонта",
        "Описание",
        "Причина компании",
        "Сумма",
        "Статус"
    ]

    for col, header in enumerate(
        headers
    ):
        repair_sheet.write(
            0,
            col,
            header,
            header_format
        )

    for row_index, repair in enumerate(
        repairs,
        start=1
    ):
        repair_sheet.write(
            row_index,
            0,
            repair["repair_code"],
            center_format
        )

        created_at = repair[
            "created_at"
        ]

        if created_at:
            try:
                dt = datetime.strptime(
                    created_at,
                    "%Y-%m-%d %H:%M:%S"
                )

                repair_sheet.write_datetime(
                    row_index,
                    1,
                    dt,
                    date_format
                )

            except ValueError:
                repair_sheet.write(
                    row_index,
                    1,
                    created_at,
                    normal_format
                )

        repair_sheet.write(
            row_index,
            2,
            repair[
                "master_telegram_id"
            ],
            center_format
        )

        repair_sheet.write(
            row_index,
            3,
            repair[
                "bike_number"
            ],
            center_format
        )

        repair_sheet.write(
            row_index,
            4,
            payer_name(
                repair[
                    "payer_type"
                ]
            ),
            center_format
        )

        repair_sheet.write(
            row_index,
            5,
            repair_type_name(
                repair[
                    "repair_type"
                ]
            ),
            center_format
        )

        repair_sheet.write(
            row_index,
            6,
            repair[
                "description"
            ] or "",
            wrap_format
        )

        repair_sheet.write(
            row_index,
            7,
            repair[
                "company_reason"
            ] or "",
            wrap_format
        )

        repair_sheet.write_number(
            row_index,
            8,
            float(
                repair[
                    "total_amount"
                ] or 0
            ),
            money_format
        )

        repair_sheet.write(
            row_index,
            9,
            status_name(
                repair[
                    "status"
                ]
            ),
            center_format
        )

    last_repair_row = max(
        len(repairs),
        1
    )

    repair_sheet.autofilter(
        0,
        0,
        last_repair_row,
        len(headers) - 1
    )

    repair_sheet.freeze_panes(
        1,
        0
    )

    repair_sheet.set_column(
        "A:A",
        14
    )

    repair_sheet.set_column(
        "B:B",
        18
    )

    repair_sheet.set_column(
        "C:C",
        16
    )

    repair_sheet.set_column(
        "D:D",
        12
    )

    repair_sheet.set_column(
        "E:F",
        18
    )

    repair_sheet.set_column(
        "G:H",
        34
    )

    repair_sheet.set_column(
        "I:I",
        15
    )

    repair_sheet.set_column(
        "J:J",
        16
    )

    # Условное форматирование статусов

    if repairs:
        repair_sheet.conditional_format(
            1,
            9,
            len(repairs),
            9,
            {
                "type": "text",
                "criteria": "containing",
                "value": "Подтвержден",
                "format": workbook.add_format({
                    "bg_color": "#DCFCE7",
                    "font_color": "#166534"
                })
            }
        )

        repair_sheet.conditional_format(
            1,
            9,
            len(repairs),
            9,
            {
                "type": "text",
                "criteria": "containing",
                "value": "На проверке",
                "format": workbook.add_format({
                    "bg_color": "#FEF3C7",
                    "font_color": "#92400E"
                })
            }
        )

        repair_sheet.conditional_format(
            1,
            9,
            len(repairs),
            9,
            {
                "type": "text",
                "criteria": "containing",
                "value": "Отклонен",
                "format": workbook.add_format({
                    "bg_color": "#FEE2E2",
                    "font_color": "#991B1B"
                })
            }
        )

    # =====================================================
    # ЛИСТ ЗАПЧАСТИ
    # =====================================================

    part_sheet = workbook.add_worksheet(
        "Запчасти"
    )

    part_sheet.hide_gridlines(2)

    part_headers = [
        "ID ремонта",
        "Дата",
        "Велосипед",
        "Запчасть",
        "Количество",
        "Источник",
        "Велосипед-донор",
        "Статус ремонта"
    ]

    for col, header in enumerate(
        part_headers
    ):
        part_sheet.write(
            0,
            col,
            header,
            header_format
        )

    for row_index, part in enumerate(
        parts,
        start=1
    ):
        part_sheet.write(
            row_index,
            0,
            part[
                "repair_code"
            ],
            center_format
        )

        part_sheet.write(
            row_index,
            1,
            part[
                "created_at"
            ],
            center_format
        )

        part_sheet.write(
            row_index,
            2,
            part[
                "bike_number"
            ],
            center_format
        )

        part_sheet.write(
            row_index,
            3,
            part[
                "part_name"
            ],
            normal_format
        )

        part_sheet.write(
            row_index,
            4,
            part[
                "quantity"
            ],
            center_format
        )

        part_sheet.write(
            row_index,
            5,
            source_name(
                part[
                    "source_type"
                ]
            ),
            center_format
        )

        part_sheet.write(
            row_index,
            6,
            part[
                "donor_bike_number"
            ] or "-",
            center_format
        )

        part_sheet.write(
            row_index,
            7,
            status_name(
                part[
                    "status"
                ]
            ),
            center_format
        )

    part_last_row = max(
        len(parts),
        1
    )

    part_sheet.autofilter(
        0,
        0,
        part_last_row,
        len(part_headers) - 1
    )

    part_sheet.freeze_panes(
        1,
        0
    )

    part_sheet.set_column(
        "A:A",
        14
    )

    part_sheet.set_column(
        "B:B",
        19
    )

    part_sheet.set_column(
        "C:C",
        13
    )

    part_sheet.set_column(
        "D:D",
        28
    )

    part_sheet.set_column(
        "E:E",
        12
    )

    part_sheet.set_column(
        "F:F",
        15
    )

    part_sheet.set_column(
        "G:G",
        18
    )

    part_sheet.set_column(
        "H:H",
        18
    )

    # =====================================================
    # ЛИСТ ОПЛАТЫ
    # =====================================================

    payment_sheet = workbook.add_worksheet(
        "Оплаты"
    )

    payment_sheet.hide_gridlines(2)

    payment_headers = [
        "ID платежа",
        "ID ремонта",
        "Дата платежа",
        "Велосипед",
        "Сумма",
        "Способ оплаты",
        "Статус платежа",
        "Статус ремонта"
    ]

    for col, header in enumerate(
        payment_headers
    ):
        payment_sheet.write(
            0,
            col,
            header,
            header_format
        )

    for row_index, payment in enumerate(
        payments,
        start=1
    ):
        payment_sheet.write(
            row_index,
            0,
            payment[
                "payment_id"
            ],
            center_format
        )

        payment_sheet.write(
            row_index,
            1,
            payment[
                "repair_code"
            ],
            center_format
        )

        payment_sheet.write(
            row_index,
            2,
            payment[
                "created_at"
            ],
            center_format
        )

        payment_sheet.write(
            row_index,
            3,
            payment[
                "bike_number"
            ],
            center_format
        )

        payment_sheet.write_number(
            row_index,
            4,
            float(
                payment[
                    "amount"
                ] or 0
            ),
            money_format
        )

        payment_sheet.write(
            row_index,
            5,
            payment[
                "payment_method"
            ] or "",
            center_format
        )

        payment_sheet.write(
            row_index,
            6,
            status_name(
                payment[
                    "payment_status"
                ]
            ),
            center_format
        )

        payment_sheet.write(
            row_index,
            7,
            status_name(
                payment[
                    "repair_status"
                ]
            ),
            center_format
        )

    payment_last_row = max(
        len(payments),
        1
    )

    payment_sheet.autofilter(
        0,
        0,
        payment_last_row,
        len(payment_headers) - 1
    )

    payment_sheet.freeze_panes(
        1,
        0
    )

    payment_sheet.set_column(
        "A:A",
        14
    )

    payment_sheet.set_column(
        "B:B",
        15
    )

    payment_sheet.set_column(
        "C:C",
        20
    )

    payment_sheet.set_column(
        "D:D",
        13
    )

    payment_sheet.set_column(
        "E:E",
        16
    )

    payment_sheet.set_column(
        "F:H",
        18
    )

    workbook.close()

    return file_path