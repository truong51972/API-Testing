import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from src.settings import get_now_vn


class TestSuiteReportModel(SQLModel):
    """Repository for Test Suite operations."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Test Suite Report ID, must be unique.",
        max_length=64,
        primary_key=True,
    )

    test_suite_id: str = Field(
        description="Test Suite ID, must be unique.",
        max_length=64,
        foreign_key="test_suite.test_suite_id",
        # unique=True,
    )

    created_at: datetime = Field(
        default_factory=get_now_vn,
        description="Creation timestamp",
    )
