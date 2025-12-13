import logging
from typing import Optional

from sqlmodel import Session, select

from src.models import TestCaseModel
from src.settings import get_db_engine


class TestCaseRepository(TestCaseModel, table=True):
    """Repository for Test Case operations."""

    __tablename__ = "test_case"

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
