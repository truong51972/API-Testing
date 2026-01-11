import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel

from .test_case_model import TestCaseModel


class TestCaseReportModel(SQLModel):
    """Repository for Test Case operations."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Test Case Report ID, must be unique.",
        max_length=64,
        primary_key=True,
    )

    test_suite_report_id: str = Field(
        description="Test Suite Report ID, must be unique.",
        max_length=64,
        foreign_key="test_suite_report.id",
    )

    test_case_id: str = Field(
        description="Test Case Report ID, must be unique.",
        max_length=64,
        foreign_key="test_case.id",
    )

    request_header: dict = Field(
        sa_column=Column(JSON),
        description="Request header information.",
    )

    request_body: dict = Field(
        sa_column=Column(JSON),
        description="Request body information.",
    )

    response_header: dict = Field(
        sa_column=Column(JSON),
        description="Response header information.",
    )

    response_body: dict = Field(
        sa_column=Column(JSON),
        description="Response body information.",
    )

    response_status_code: int = Field(
        description="HTTP status code of the response.",
    )

    status: str = Field(
        description="Status of the test case execution. (e.g., passed, failed, skipped)",
        max_length=128,
    )

    start_time: datetime = Field(
        description="Start time of the test case execution.",
    )

    end_time: datetime = Field(
        description="End time of the test case execution.",
    )


class TestCaseReportReadModel(TestCaseReportModel):

    test_case: Optional[TestCaseModel] = None
