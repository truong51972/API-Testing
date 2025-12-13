from typing import Annotated, Any

from pydantic import BeforeValidator

from src.types.common import check_empty, check_length, check_type


def validate_logic(v: Any) -> str:
    # 1. Check Empty
    check_empty(v, "User ID")
    # 2. Check Type
    check_type(v, str, "User ID")
    # 3. Check Length
    check_length(v, 100, "User ID")
    return v


UserIDType = Annotated[
    str,
    BeforeValidator(validate_logic),
]
