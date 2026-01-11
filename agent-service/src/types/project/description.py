from typing import Annotated, Any

from pydantic import BeforeValidator

from src.types.common import check_empty, check_length, check_type


def validate_logic(v: Any) -> str:
    # 1. Check Empty
    check_empty(v, "Project description")
    # 2. Check Type
    check_type(v, str, "Project description")
    # 3. Check Length
    check_length(v, 512, "Project description")
    return v


DescriptionType = Annotated[
    str,
    BeforeValidator(validate_logic),
]
