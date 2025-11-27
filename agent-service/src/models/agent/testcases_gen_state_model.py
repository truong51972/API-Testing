from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.enums.enums import LanguageEnum


class TestcasesGenStateModel(BaseModel):
    """
    Represents the state of an AI agent, including its name, description, and current status.
    """

    project_id: str = Field(
        description="Project ID, must be unique.",
    )

    lang: LanguageEnum = Field(
        default=LanguageEnum.EN,
        description="Language of the document",
    )

    test_case_infos: dict[str, Any] = Field(
        default_factory=dict,
        description="List of generated test cases mapped by functional requirement",
    )

    extra_parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional parameters for processing",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "00000000-0000-0000-0000-000000000000",
                "lang": "en",
            }
        }
    )
