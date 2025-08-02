from datetime import datetime

from sqlmodel import Field

from src.models.test_suite.test_suite_model import TestSuitModel


class TestSuitRepository(TestSuitModel, table=True):
    """Repository for TestSuit operations."""

    id: int = Field(
        primary_key=True,
        description="TestSuit ID, must be unique.",
    )

    created_at: datetime = Field(
        default_factory=datetime.now(),
        description="Creation timestamp",
    )

    updated_at: datetime = Field(
        default_factory=datetime.now(),
        description="Last update timestamp",
    )
