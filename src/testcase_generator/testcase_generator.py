import json
import random
import re
import string

import pandas as pd


def random_invalid_strings(regex, n, min_length=1, max_length=10):
    """
    Sinh n string random (bao gồm chữ, số, ký tự đặc biệt, khoảng trắng)
    nhưng chắc chắn không match với regex cho trước.

    Args:
        regex (str): Biểu thức chính quy cần kiểm tra.
        n (int): Số lượng string cần lấy.
        min_length (int): Độ dài tối thiểu của string.
        max_length (int): Độ dài tối đa của string.

    Returns:
        list: Danh sách các string KHÔNG match với regex.
    """
    chars = string.ascii_letters + string.digits + string.punctuation + " "
    result = []
    pattern = re.compile(regex)

    while len(result) < n:
        length = random.randint(min_length, max_length)
        s = "".join(random.choices(chars, k=length))
        if not pattern.fullmatch(s):
            result.append(s)
    return result


with open("data.json.example", "r") as file:
    data = json.load(file)

# Print the loaded data

field_names = ["TestCase"]
field_names.extend(data.keys())

df = pd.DataFrame(columns=field_names)


success_testcase_placeholder = "[Basic][Success] <{field_name}> = {value}{condition}"
fail_testcase_placeholder = "[Basic][Fail] <{field_name}> {value}{condition}"

conditional_testcase_placeholder = ", <{field_name}> = {value}"


default_values = {
    field_name: (
        "ABSENT"
        if field_data.get("required") == "O"
        else (
            "CONDITION"
            if field_data.get("required") == "C"
            else field_data.get("default_value", "")
        )
    )
    for field_name, field_data in data.items()
}

print("Default Values:" + json.dumps(default_values, indent=4))


def remove_conditional_values(
    row, current_field_name, current_value, condition_field_name=None
):
    """
    Remove conditional values from the row based on the field name.
    """
    for _field_name, _properties in data.items():
        if (_field_name == current_field_name) or (_properties.get("required") != "C"):
            continue
        if (current_value in _properties["condition"]["values"]) or (
            condition_field_name == _field_name
        ):
            row[_field_name] = _properties.get("default_value", "")
        else:
            row[_field_name] = "ABSENT"

    return row


for field_name, properties in data.items():
    row = default_values.copy()
    for enum_value in properties.get("enum", []):
        condition = ""
        if properties.get("required") == "M":

            row = remove_conditional_values(
                row=row, current_field_name=field_name, current_value=enum_value
            )

            row["TestCase"] = success_testcase_placeholder.format(
                field_name=field_name, value=enum_value, condition=condition
            )
            row[field_name] = enum_value
            df.loc[len(df)] = row

        elif properties.get("required") == "C":
            condition_depend_on = properties["condition"]["depend_on"]
            condition_values = properties["condition"].get("values", [])
            for condition_value in condition_values:
                row[condition_depend_on] = condition_value

                condition = conditional_testcase_placeholder.format(
                    field_name=condition_depend_on, value=condition_value
                )
                row["TestCase"] = success_testcase_placeholder.format(
                    field_name=field_name, value=enum_value, condition=condition
                )
                row[field_name] = enum_value

                row = remove_conditional_values(
                    row=row,
                    current_field_name=field_name,
                    current_value=condition_value,
                    condition_field_name=condition_depend_on,
                )
                df.loc[len(df)] = row


def add_check_empty(row, field_name, condition_value=None, condition_depend_on=None):
    """
    Add a check for empty values in the row.
    """
    condition = ""

    if condition_value is not None and condition_depend_on is not None:
        condition = conditional_testcase_placeholder.format(
            field_name=condition_depend_on, value=condition_value
        )
        row[condition_depend_on] = condition_value

    row["TestCase"] = fail_testcase_placeholder.format(
        field_name=field_name, value="is EMPTY", condition=condition
    )

    row[field_name] = "EMPTY"

    row = remove_conditional_values(
        row=row,
        current_field_name=field_name,
        current_value=(
            condition_value if condition_value else data[field_name]["default_value"]
        ),
        condition_field_name=condition_depend_on,
    )

    df.loc[len(df)] = row


def add_check_absent(row, field_name, condition_value=None, condition_depend_on=None):
    """
    Add a check for absent values in the row.
    """
    condition = ""

    if condition_value is not None and condition_depend_on is not None:
        condition = conditional_testcase_placeholder.format(
            field_name=condition_depend_on, value=condition_value
        )
        row[condition_depend_on] = condition_value

    row["TestCase"] = fail_testcase_placeholder.format(
        field_name=field_name, value="is ABSENT", condition=condition
    )

    row[field_name] = "ABSENT"

    row = remove_conditional_values(
        row=row,
        current_field_name=field_name,
        current_value=(
            condition_value if condition_value else data[field_name]["default_value"]
        ),
        condition_field_name=condition_depend_on,
    )

    df.loc[len(df)] = row


def add_check_null(row, field_name, condition_value=None, condition_depend_on=None):
    """
    Add a check for null values in the row.
    """

    condition = ""

    if condition_value is not None and condition_depend_on is not None:
        condition = conditional_testcase_placeholder.format(
            field_name=condition_depend_on, value=condition_value
        )
        row[condition_depend_on] = condition_value

    row["TestCase"] = fail_testcase_placeholder.format(
        field_name=field_name, value="is NULL", condition=condition
    )

    row[field_name] = "NULL"

    row = remove_conditional_values(
        row=row,
        current_field_name=field_name,
        current_value=(
            condition_value if condition_value else data[field_name]["default_value"]
        ),
        condition_field_name=condition_depend_on,
    )

    df.loc[len(df)] = row


def add_check_special_characters(
    row, field_name, condition_value=None, condition_depend_on=None
):
    """
    Add a check for special characters in the row.
    """
    condition = ""
    if condition_value is not None and condition_depend_on is not None:
        condition = conditional_testcase_placeholder.format(
            field_name=condition_depend_on, value=condition_value
        )
        row[condition_depend_on] = condition_value

    row["TestCase"] = fail_testcase_placeholder.format(
        field_name=field_name, value="contains SPECIAL_CHARACTERS", condition=condition
    )

    if properties.get("max_length"):
        row[field_name] = "@!#$%^&*()_+"[: properties["max_length"]]
    else:
        row[field_name] = "@!#$%^&*()_+"

    row = remove_conditional_values(
        row=row,
        current_field_name=field_name,
        current_value=(
            condition_value if condition_value else data[field_name]["default_value"]
        ),
        condition_field_name=condition_depend_on,
    )

    df.loc[len(df)] = row


def add_check_max_length(
    row, field_name, condition_value=None, condition_depend_on=None
):
    condition = ""

    if condition_value is not None and condition_depend_on is not None:
        condition = conditional_testcase_placeholder.format(
            field_name=condition_depend_on, value=condition_value
        )
        row[condition_depend_on] = condition_value
    row["TestCase"] = fail_testcase_placeholder.format(
        field_name=field_name, value="exceeds max length", condition=condition
    )

    row[field_name] = (
        properties["default_value"] if properties["default_value"] != "" else "A"
    )[0] * (properties["max_length"] + 1)

    row = remove_conditional_values(
        row=row,
        current_field_name=field_name,
        current_value=(
            condition_value if condition_value else data[field_name]["default_value"]
        ),
        condition_field_name=condition_depend_on,
    )

    df.loc[len(df)] = row


def add_check_regex(row, field_name, condition_value=None, condition_depend_on=None):
    """
    Add a check for regex validation in the row.
    """
    condition = ""

    if condition_value is not None and condition_depend_on is not None:
        condition = conditional_testcase_placeholder.format(
            field_name=condition_depend_on, value=condition_value
        )
        row[condition_depend_on] = condition_value

    row["TestCase"] = fail_testcase_placeholder.format(
        field_name=field_name, value="is invalid string value", condition=condition
    )

    invalid_strings = random_invalid_strings(
        properties["regex"], 5, min_length=1, max_length=10
    )
    row[field_name] = random.choice(invalid_strings)

    row = remove_conditional_values(
        row=row,
        current_field_name=field_name,
        current_value=(
            condition_value if condition_value else data[field_name]["default_value"]
        ),
        condition_field_name=condition_depend_on,
    )

    df.loc[len(df)] = row


for field_name, properties in data.items():
    row = default_values.copy()

    if properties.get("required") != "C":
        if properties["check"]["empty"]:
            add_check_empty(row, field_name)

        if properties["check"]["absent"] and properties.get("required") != "O":
            add_check_absent(row, field_name)

        if properties["check"]["null"] and properties.get("required") != "O":
            add_check_null(row, field_name)

        if properties["check"]["special_characters"]:
            add_check_special_characters(row, field_name)

        if properties.get("max_length"):
            add_check_max_length(row, field_name)

    elif properties.get("required") == "C":
        condition_depend_on = properties["condition"]["depend_on"]
        condition_values = properties["condition"].get("values", [])

        for condition_value in condition_values:
            if properties["check"]["empty"]:
                add_check_empty(
                    row=row,
                    field_name=field_name,
                    condition_value=condition_value,
                    condition_depend_on=condition_depend_on,
                )

            if properties["check"]["absent"]:
                add_check_absent(
                    row=row,
                    field_name=field_name,
                    condition_value=condition_value,
                    condition_depend_on=condition_depend_on,
                )

            if properties["check"]["null"]:
                add_check_null(
                    row=row,
                    field_name=field_name,
                    condition_value=condition_value,
                    condition_depend_on=condition_depend_on,
                )

            if properties.get("regex"):
                add_check_regex(
                    row=row,
                    field_name=field_name,
                    condition_value=condition_value,
                    condition_depend_on=condition_depend_on,
                )

            if properties["check"]["special_characters"]:
                add_check_special_characters(
                    row=row,
                    field_name=field_name,
                    condition_value=condition_value,
                    condition_depend_on=condition_depend_on,
                )

            if properties.get("max_length"):
                add_check_max_length(
                    row=row,
                    field_name=field_name,
                    condition_value=condition_value,
                    condition_depend_on=condition_depend_on,
                )
print(df)
df.to_excel("testcase_generator_output.xlsx", index=False)
