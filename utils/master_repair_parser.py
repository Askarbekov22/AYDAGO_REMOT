import re


EMPTY_VALUES = {
    "",
    "-",
    "—",
    "нет",
    "не было",
    "не требуется"
}


def is_empty(value: str):
    return value.strip().lower() in EMPTY_VALUES


def normalize_repair_type(value: str):
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
        "с велосипеда-донора"
    }:
        return "donor"

    return None


def parse_integer(value: str):
    try:
        number = int(value.strip())

        if number <= 0:
            return None

        return number

    except ValueError:
        return None


def extract_fields(text: str):
    labels = [
        "Тип ремонта",
        "Запчасть",
        "Количество",
        "Источник",
        "Номер донора",
        "Описание"
    ]

    result = {}

    labels_pattern = "|".join(
        re.escape(label)
        for label in labels
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
            result[label] = match.group(1).strip()
        else:
            result[label] = ""

    return result


def parse_master_repair(text: str):
    fields = extract_fields(text)

    errors = []

    repair_type = normalize_repair_type(
        fields["Тип ремонта"]
    )

    if not repair_type:
        errors.append(
            "Тип ремонта должен быть "
            "«с запчастью» или «без запчасти»."
        )

    part_name = fields["Запчасть"].strip()

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
                "Источник должен быть "
                "«склад» или «донор»."
            )

        if source_type == "donor":

            donor_bike_number = (
                fields["Номер донора"].strip()
            )

            if (
                not donor_bike_number
                or is_empty(donor_bike_number)
            ):
                errors.append(
                    "Укажите номер велосипеда-донора."
                )

    description = fields["Описание"].strip()

    if (
        not description
        or is_empty(description)
        or len(description) < 3
    ):
        errors.append(
            "Укажите описание проделанной работы."
        )

    if errors:
        return None, errors

    return {
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

        "description": description
    }, []