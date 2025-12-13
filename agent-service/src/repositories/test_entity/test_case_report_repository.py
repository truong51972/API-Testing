from typing import Optional

from sqlalchemy.orm import joinedload
from sqlmodel import Relationship, Session, select

from src.models import TestCaseReportModel, TestCaseReportReadModel
from src.repositories.test_entity.test_case_repository import TestCaseRepository
from src.settings import get_db_engine


class TestCaseReportRepository(TestCaseReportModel, table=True):
    """Repository for Test Case operations."""

    __tablename__ = "test_case_report"

    test_case: TestCaseRepository = Relationship()

    @classmethod
    def get_all_by_test_suite_report_id(
        cls,
        test_suite_report_id: str,
        session: Optional[Session] = None,
    ) -> list["TestCaseReportReadModel"]:
        session = session or Session(get_db_engine())

        with session:
            statement = (
                select(cls)
                .options(joinedload(cls.test_case))
                .where(cls.test_suite_report_id == test_suite_report_id)
            )
            results_set = session.exec(statement).all()

        results = []

        for result in results_set:
            results.append(TestCaseReportReadModel.model_validate(result))
        return results
