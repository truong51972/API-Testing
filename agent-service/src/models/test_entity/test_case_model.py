import uuid

import regex as re
from pydantic import field_validator
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class ApiInfoModel(SQLModel):
    url: str
    method: str
    headers: dict

    @field_validator("url")
    def validate_url(cls, value):
        url_regex = re.compile(
            r"^(https?://)?"  # http:// or https://
            r"(([A-Za-z0-9-]+\.)+[A-Za-z]{2,6})"  # domain...
            r"(:\d+)?"  # optional port
            r"(/[\w./?%&=-]*)?$"  # path
        )
        result = re.match(url_regex, value) is not None
        if not result:
            raise ValueError(f"Invalid URL format: {value}")

        if not value.endswith("/"):
            value += "/"
        return value

    @field_validator("method")
    def validate_method(cls, value):
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH"}
        if value.upper() not in valid_methods:
            raise ValueError(f"Invalid HTTP method: {value}")
        return value.upper()


class ExpectedResponseModel(SQLModel):
    status_code: int
    response_mapping: dict


class TestCaseModel(SQLModel):
    """Repository for Test Case operations."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Test Case ID, must be unique.",
        max_length=64,
        primary_key=True,
    )

    test_suite_id: str = Field(
        description="Test Suite ID, must be unique.",
        max_length=64,
        foreign_key="test_suite.test_suite_id",
    )

    test_case_type: str = Field(
        description="Type of the test case.",
        max_length=128,
    )

    test_case_id: str = Field(
        description="Composite key of test case ID and name, must be unique.",
        max_length=576,
    )

    test_case: str = Field(
        description="Name of the test case.",
        max_length=512,
    )

    api_info: dict = Field(
        sa_column=Column(JSON),
        description="API information for the test case.",
    )

    request_body: dict = Field(
        sa_column=Column(JSON),
        description="Request payload for the test case.",
    )

    expected_output: dict = Field(
        sa_column=Column(JSON),
        description="Expected response for the test case.",
    )

    execute: bool = Field(
        default=False,
        description="Indicates whether the test case should be executed.",
    )
