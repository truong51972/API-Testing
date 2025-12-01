import logging
import uuid
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, Session, SQLModel, select

from src.settings import get_db_engine


class ApiInfoModel(SQLModel):
    url: str
    method: str
    headers: dict


class ExpectedResponseModel(SQLModel):
    status_code: int
    response_mapping: dict


class TestCaseRepository(SQLModel, table=True):
    """Repository for Test Case operations."""

    __tablename__ = "test_case"

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

    @classmethod
    def get_all_by_test_suite_id(
        cls,
        test_suite_id: str,
        execute: Optional[bool] = None,
        session: Optional[Session] = None,
    ) -> list["TestCaseRepository"]:
        session = session or Session(get_db_engine())

        with session:
            statement = select(cls).where(
                (cls.test_suite_id == test_suite_id)
                & ((cls.execute == execute) if execute is not None else True)
            )
            results = session.exec(statement).all()
        return results

    @classmethod
    def select_for_execution(
        cls, test_case_ids: list[str], execute: bool, session: Optional[Session] = None
    ) -> list["TestCaseRepository"]:
        session = session or Session(get_db_engine())
        with session:

            session.exec(
                cls.__table__.update()
                .where(cls.id.in_(test_case_ids))
                .values(execute=execute)
            )
            session.commit()

            statement = select(cls.id).where(cls.id.in_(test_case_ids))
            results = session.exec(statement).all()
            logging.info(f"Selecting {len(results)} test cases for execution={execute}")

            return results
