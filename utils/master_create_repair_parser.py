import re


EMPTY_VALUES = {
    "",
    "-",
    "—",
    "нет",
    "не требуется",
    "не оплачено"
}


FIELDS = [
    "Номер велосипеда",
    "За чей счет",
    "Тип ремонта",
    "Запчасть",
    "Количество",
    "Источник",
    "Номер донора",
    "Описание",
    "Сумма оплаты",
    "Способ оплаты",
    "Причина ремонта"
]


def is_empty(
    value: str
):
    return (
        value.strip().lower()
        in EMPTY_VALUES
    )


def extract_fields(
    text: str
):
    result = {}

    labels_pattern = "|".join(
        re.escape(label)
        for label in FIELDS
    )

    for label in FIELDS:
        pattern = (
            rf"{re.escape(label)}"
            rf"\s*:\s*"
            rf"(.*?)"
            rf"(?=\s*(?:{labels_pattern})\s*:|$)"
        )

        match = re.search(
            pattern,
            text,
            flags=(
                re.IGNORECASE
                | re.DOTALL
            )
        )

        if match:
            result[label] = (
                match.group(1).strip()
            )
        else:
            result[label] = ""

    return result


def normalize_payer_type(
    value: str
):
    value = value.strip().lower()

    if value in {
        "клиент",
        "клиента",
        "за счет клиента",
        "за счёт клиента"
    }:
        return "client"

    if value in {
        "компания",
        "компании",
        "за счет компании",
        "за счёт компании"
    }:
        return "company"

    return None


def normalize_repair_type(
    value: str
):
    value = value.strip().lower()

    if value in {
        "с запчастью",
        "с заменой запчасти",
        "замена запчасти",
        "запчасть"
    }:
        return "part"

    if value in {
        "без запчасти",
        "без замены запчасти",
        "ремонт без запчасти"
    }:
        return "no_part"

    return None


def normalize_source(
    value: str
):
    value = value.strip().lower()

    if value in {
        "склад",
        "со склада"
    }:
        return "warehouse"

    if value in {
        "донор",
        "с донора"
    }:
        return "donor"

    return None


def normalize_payment_method(
    value: str
):
    value = value.strip().lower()

    if value in {
        "qr",
        "куар",
        "qr-код",
        "qr код"
    }:
        return "qr"

    if value in {
        "наличные",
        "нал",
        "наличка"
    }:
        return "cash"

    if value in {
        "перевод",
        "переводом"
    }:
        return "transfer"

    return None


def parse_quantity(
    value: str
):
    try:
        quantity = int(
            value.strip()
        )

        if quantity <= 0:
            return None

        return quantity

    except ValueError:
        return None


def parse_amount(
    value: str
):
    if is_empty(value):
        return 0

    raw = (
        value
        .strip()
        .replace(" ", "")
        .replace(",", ".")
        .replace("сом", "")
    )

    try:
        amount = float(raw)

        if amount < 0:
            return None

        return amount

    except ValueError:
        return None


def parse_master_created_repair(
    text: str
):
    fields = extract_fields(
        text
    )

    errors = []

    # =====================================================
    # ВЕЛОСИПЕД
    # =====================================================

    bike_number = (
        fields[
            "Номер велосипеда"
        ].strip()
    )

    if not bike_number:
        errors.append(
            "Укажите номер велосипеда."
        )

    # =====================================================
    # ПЛАТЕЛЬЩИК
    # =====================================================

    payer_type = normalize_payer_type(
        fields["За чей счет"]
    )

    if not payer_type:
        errors.append(
            "Поле «За чей счет» должно быть "
            "«клиент» или «компания»."
        )

    # =====================================================
    # ТИП РЕМОНТА
    # =====================================================

    repair_type = normalize_repair_type(
        fields["Тип ремонта"]
    )

    if not repair_type:
        errors.append(
            "Тип ремонта должен быть "
            "«с запчастью» или "
            "«без запчасти»."
        )

    # =====================================================
    # ЗАПЧАСТЬ
    # =====================================================

    part_name = (
        fields["Запчасть"].strip()
    )

    quantity = None
    source_type = None
    donor_bike_number = None

    if repair_type == "part":

        if (
            not part_name
            or is_empty(part_name)
        ):
            errors.append(
                "Укажите название запчасти."
            )

        quantity = parse_quantity(
            fields["Количество"]
        )

        if quantity is None:
            errors.append(
                "Количество должно быть "
                "целым числом больше 0."
            )

        source_type = normalize_source(
            fields["Источник"]
        )

        if not source_type:
            errors.append(
                "Источник должен быть "
                "«склад» или «донор»."
            )

        if source_type == "donor":

            donor_bike_number = (
                fields[
                    "Номер донора"
                ].strip()
            )

            if (
                not donor_bike_number
                or is_empty(
                    donor_bike_number
                )
            ):
                errors.append(
                    "Укажите номер "
                    "велосипеда-донора."
                )

    # =====================================================
    # ОПИСАНИЕ
    # =====================================================

    description = (
        fields["Описание"].strip()
    )

    if (
        not description
        or is_empty(description)
        or len(description) < 3
    ):
        errors.append(
            "Укажите описание "
            "проделанной работы."
        )

    # =====================================================
    # ОПЛАТА
    # =====================================================

    amount = parse_amount(
        fields["Сумма оплаты"]
    )

    if amount is None:
        errors.append(
            "Некорректная сумма оплаты."
        )
        amount = 0

    payment_method = None

    # Если платит клиент и сумма > 0,
    # способ оплаты обязателен.
    if (
        payer_type == "client"
        and amount > 0
    ):
        payment_method = (
            normalize_payment_method(
                fields[
                    "Способ оплаты"
                ]
            )
        )

        if not payment_method:
            errors.append(
                "Укажите способ оплаты: "
                "QR, наличные или перевод."
            )

    # =====================================================
    # ПРИЧИНА КОМПАНИИ
    # =====================================================

    company_reason = (
        fields[
            "Причина ремонта"
        ].strip()
    )

    if payer_type == "company":

        if (
            not company_reason
            or is_empty(
                company_reason
            )
        ):
            errors.append(
                "Для ремонта за счет компании "
                "укажите причину ремонта."
            )

        # Для компании клиентская оплата
        # не используется.
        amount = 0
        payment_method = None

    if errors:
        return None, errors

    return {
        "bike_number": bike_number,
        "payer_type": payer_type,
        "repair_type": repair_type,

        "part_name": (
            part_name
            if repair_type == "part"
            else None
        ),

        "part_quantity": (
            quantity
            if repair_type == "part"
            else None
        ),

        "source_type": (
            source_type
            if repair_type == "part"
            else None
        ),

        "donor_bike_number": (
            donor_bike_number
            if repair_type == "part"
            else None
        ),

        "description": description,

        "payment_amount": amount,

        "payment_method": (
            payment_method
        ),

        "payment_status": (
            "paid"
            if (
                payer_type == "client"
                and amount > 0
            )
            else "unpaid"
        ),

        "company_reason": (
            company_reason
            if payer_type == "company"
            else None
        )
    }, []