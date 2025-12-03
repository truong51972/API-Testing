from typing import Any

from src.exception import ApiValidationException


def check_empty(value: Any, field_name: str) -> None:
    if value is None or (isinstance(value, str) and len(value.strip()) == 0):
        raise ApiValidationException(
            code=["1001"], description=f"{field_name} cannot be empty."
        )


def check_type(value: Any, expected_type: type, field_name: str) -> None:
    if not isinstance(value, expected_type):
        raise ApiValidationException(
            code=["1001"],
            description=f"{field_name} must be a {expected_type.__name__}.",
        )


def check_length(value: str, max_length: int, field_name: str) -> None:
    if len(value) > max_length:
        raise ApiValidationException(
            code=["1001"],
            description=f"{field_name} must be at most {max_length} characters long.",
        )
