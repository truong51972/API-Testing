import hashlib
from typing import List, Optional

# for validation
from pydantic import ConfigDict

#     BaseModel,
#     ConfigDict,
#     Field,
#     field_validator,
#     model_validator,
#     validate_call,
# )
from sqlmodel import Field, SQLModel


class TestSuitModel(SQLModel):
    """TestSuit model"""

    name: str = Field(
        min_length=3,
        max_length=512,
        description="TestSuit name",
    )

    description: Optional[str] = Field(
        default=None,
        max_length=1024,
        description="TestSuit description",
    )

    delete_at: Optional[str] = Field(
        default=None,
        description="The time when the TestSuit was deleted, if applicable.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Example TestSuit",
                "description": "This is an example of a TestSuit model.",
            }
        }
    )
