import re


EMPTY_VALUES = {
    "",
    "-",
    "—",
    "нет",
    "не используется",
    "не требуется"
}


def clean_value(value: str) -> str:
    return value.strip()


def is_empty_value(value: str) -> bool:
    return value.strip().lower() in EMPTY_VALUES


def normalize_repair_type(value: str):
    value = value.strip().lower()

    if value in {
        "с запчастью",
        "с заменой запчасти",
        "запчасть",
        "замена запчасти"
    }:
        return "part"

    if value in {
        "без запчасти",
        "без замены запчасти",
        "ремонт без запчасти"
    }:
        return "no_part"

    return None


def normalize_source(value: str):
    value = value.strip().lower()

    if value in {
        "склад",
        "со склада"
    }:
        return "warehouse"

    if value in {
        "донор",
        "с донора",
        "велосипед-донор",
        "с велосипеда-донора"
    }:
        return "donor"

    return None


def parse_number(value: str):
    value = (
        value.strip()
        .replace(" ", "")
        .replace(",", ".")
    )

    try:
        number = float(value)

        if number <= 0:
            return None

        return number

    except ValueError:
        return None


def parse_integer(value: str):
    value = value.strip()

    try:
        number = int(value)

        if number <= 0:
            return None

        return number

    except ValueError:
        return None


def extract_fields(text: str, labels: list[str]):
    result = {}

    escaped_labels = [
        re.escape(label)
        for label in labels
    ]

    labels_pattern = "|".join(
        escaped_labels
    )

    for label in labels:
        pattern = (
            rf"{re.escape(label)}\s*:\s*"
            rf"(.*?)"
            rf"(?=\s*(?:{labels_pattern})\s*:|$)"
        )

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE | re.DOTALL
        )

        if match:
            result[label] = clean_value(
                match.group(1)
            )
        else:
            result[label] = ""

    return result


def parse_company_form(text: str):
    labels = [
        "Номер велосипеда",
        "Тип ремонта",
        "Запчасть",
        "Количество",
        "Источник",
        "Номер донора",
        "Описание",
        "Причина"
    ]

    fields = extract_fields(
        text,
        labels
    )

    errors = []

    bike_number = fields[
        "Номер велосипеда"
    ].strip()

    if not bike_number:
        errors.append(
            "Не указан номер велосипеда."
        )

    repair_type = normalize_repair_type(
        fields["Тип ремонта"]
    )

    if not repair_type:
        errors.append(
            "Тип ремонта должен быть: "
            "«с запчастью» или «без запчасти»."
        )

    part_name = fields[
        "Запчасть"
    ].strip()

    quantity = None
    source_type = None
    donor_bike_number = None

    if repair_type == "part":
        if (
            not part_name
            or is_empty_value(part_name)
        ):
            errors.append(
                "Укажите название запчасти."
            )

        quantity = parse_integer(
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
                "Источник должен быть: "
                "«склад» или «донор»."
            )

        if source_type == "donor":
            donor_bike_number = fields[
                "Номер донора"
            ].strip()

            if (
                not donor_bike_number
                or is_empty_value(
                    donor_bike_number
                )
            ):
                errors.append(
                    "Укажите номер "
                    "велосипеда-донора."
                )

            elif donor_bike_number == bike_number:
                errors.append(
                    "Велосипед-донор не может "
                    "совпадать с ремонтируемым."
                )

    description = fields[
        "Описание"
    ].strip()

    if (
        not description
        or is_empty_value(description)
        or len(description) < 3
    ):
        errors.append(
            "Укажите описание работы."
        )

    reason = fields[
        "Причина"
    ].strip()

    if (
        not reason
        or is_empty_value(reason)
        or len(reason) < 3
    ):
        errors.append(
            "Укажите причину ремонта "
            "за счет компании."
        )

    if errors:
        return None, errors

    return {
        "bike_number": bike_number,
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
        "company_reason": reason
    }, []


def parse_client_form(text: str):
    labels = [
        "Номер велосипеда",
        "Тип ремонта",
        "Запчасть",
        "Количество",
        "Источник",
        "Номер донора",
        "Описание",
        "Сумма оплаты"
    ]

    fields = extract_fields(
        text,
        labels
    )

    errors = []

    bike_number = fields[
        "Номер велосипеда"
    ].strip()

    if not bike_number:
        errors.append(
            "Не указан номер велосипеда."
        )

    repair_type = normalize_repair_type(
        fields["Тип ремонта"]
    )

    if not repair_type:
        errors.append(
            "Тип ремонта должен быть: "
            "«с запчастью» или «без запчасти»."
        )

    part_name = fields[
        "Запчасть"
    ].strip()

    quantity = None
    source_type = None
    donor_bike_number = None

    if repair_type == "part":
        if (
            not part_name
            or is_empty_value(part_name)
        ):
            errors.append(
                "Укажите название запчасти."
            )

        quantity = parse_integer(
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
                "Источник должен быть: "
                "«склад» или «донор»."
            )

        if source_type == "donor":
            donor_bike_number = fields[
                "Номер донора"
            ].strip()

            if (
                not donor_bike_number
                or is_empty_value(
                    donor_bike_number
                )
            ):
                errors.append(
                    "Укажите номер "
                    "велосипеда-донора."
                )

            elif donor_bike_number == bike_number:
                errors.append(
                    "Велосипед-донор не может "
                    "совпадать с ремонтируемым."
                )

    description = fields[
        "Описание"
    ].strip()

    if (
        not description
        or is_empty_value(description)
        or len(description) < 3
    ):
        errors.append(
            "Укажите описание работы."
        )

    amount = parse_number(
        fields["Сумма оплаты"]
    )

    if amount is None:
        errors.append(
            "Сумма оплаты должна быть "
            "числом больше 0."
        )

    if errors:
        return None, errors

    return {
        "bike_number": bike_number,
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
        "amount": amount
    }, []