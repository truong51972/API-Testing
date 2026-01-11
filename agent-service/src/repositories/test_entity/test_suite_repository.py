from typing import Optional

from sqlmodel import Session, select

from src import repositories
from src.models import TestSuiteModel
from src.settings import get_db_engine


class TestSuiteRepository(TestSuiteModel, table=True):
    """Repository for Test Suite operations."""

    __tablename__ = "test_suite"

    @classmethod
    def get_all_by_project_id(
        cls,
        project_id: str,
        session: Optional[Session] = None,
    ) -> list["TestSuiteRepository"]:
        session = session or Session(get_db_engine())

        with session:

            statement = (
                select(cls)
                .join(
                    repositories.DocumentFRInfoRepository,
                    cls.fr_info_id == repositories.DocumentFRInfoRepository.fr_info_id,
                )
                .join(
                    repositories.ProjectRepository,
                    repositories.DocumentFRInfoRepository.project_id
                    == repositories.ProjectRepository.project_id,
                )
                .where(repositories.ProjectRepository.project_id == project_id)
                .order_by(cls.created_at.desc())
            )
            results = session.exec(statement).all()
            return results
