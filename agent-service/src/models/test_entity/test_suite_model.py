import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from src.settings import get_now_vn


class TestSuiteModel(SQLModel):
    """Repository for Test Suite operations."""

    test_suite_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Test Suite ID, must be unique.",
        max_length=64,
        primary_key=True,
    )

    fr_info_id: str = Field(
        description="document fr info external ID, must be unique.",
        max_length=64,
        foreign_key="document_fr_info.fr_info_id",
        # unique=True,
    )

    test_suite_name: str = Field(
        description="Name of the test suite.",
        max_length=256,
    )

    created_at: datetime = Field(
        default_factory=get_now_vn,
        description="Creation timestamp",
    )
