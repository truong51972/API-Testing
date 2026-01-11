from typing import Annotated, Any

from pydantic import BeforeValidator

from src.types.common import check_empty, check_length, check_str_num, check_type


def validate_logic(v: Any) -> str:
    # 1. Check Empty
    check_empty(v, "Page number")
    # 2. Check Type
    check_type(v, str, "Page number")
    # 3. Check Length
    check_length(v, 3, "Page number")
    # 4. Check is Number and Ranges
    check_str_num(v, gt=0, field_name="Page number")
    return v


PageNo = Annotated[
    str,
    BeforeValidator(validate_logic),
]
