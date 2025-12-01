import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, Session, SQLModel, select
from src.settings import get_db_engine


class TestCaseReportRepository(SQLModel, table=True):
    """Repository for Test Case operations."""

    __tablename__ = "test_case_report"

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

    @classmethod
    def get_all_by_test_suite_report_id(
        cls,
        test_suite_report_id: str,
        session: Optional[Session] = None,
    ) -> list["TestCaseReportRepository"]:
        session = session or Session(get_db_engine())

        with session:
            statement = select(cls).where(
                cls.test_suite_report_id == test_suite_report_id
            )
            results = session.exec(statement).all()

        return results
