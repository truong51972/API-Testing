import uuid
from typing import Optional

from pydantic import ConfigDict, model_validator
from sqlmodel import Field, Session, SQLModel, select

from src.repositories.document.document_fr_to_content_repository import (
    DocumentFRToContentRepository,
)
from src.repositories.project.project_repository import ProjectRepository
from src.settings import get_db_engine


class DocumentFRInfoRepository(SQLModel, table=True):
    __tablename__ = "document_fr_info"

    fr_info_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="document fr info external ID, must be unique.",
        max_length=64,
        primary_key=True,
    )

    project_id: str = Field(
        description="project ID, must be unique.",
        max_length=64,
        foreign_key="project.project_id",
    )

    fr_group: str = Field(
        description="group for the content, used for displaying document information.",
        max_length=128,
    )

    description: Optional[str] = Field(
        default_factory=str,
        description="description for the fr group.",
        max_length=1024,
    )

    is_selected: bool = Field(
        default=False,
        description="whether the content is selected, used for displaying document information.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fr_info_id": "123e4567-e89b-12d3-a456-426614174000",
                "project_id": "26292c94-45fd-4cb7-bdc1-368a3028ebad",
                "fr_group": "m-fr-001: Register",
            }
        }
    )

    @model_validator(mode="after")
    def check_fr_info_id(self):
        if not self.fr_info_id:
            self.fr_info_id = str(
                uuid.uuid5(uuid.NAMESPACE_DNS, f"{self.project_id}:{self.fr_group}")
            )
        return self

    @classmethod
    def get_all_by_project_id(
        cls, project_id: str, session: Optional[Session] = None
    ) -> list["DocumentFRInfoRepository"]:
        session = session or Session(get_db_engine())

        with session:
            statement = select(cls).where(cls.project_id == project_id)
            results = session.exec(statement).all()
            return results

    @classmethod
    def select_by_ids(
        cls,
        fr_info_ids: list[str],
        is_selected: bool = True,
        session: Optional[Session] = None,
    ) -> bool:
        session = session or Session(get_db_engine())

        with session:
            statement = select(cls).where(cls.fr_info_id.in_(fr_info_ids))
            results = session.exec(statement).all()
            for result in results:
                result.is_selected = is_selected
                session.add(result)
            session.commit()

        return True

    @classmethod
    def delete_by_project_id(
        cls, project_id: str, session: Optional[Session] = None
    ) -> bool:
        session = session or Session(get_db_engine())
        with session:
            statement = select(cls).where(cls.project_id == project_id)
            results = session.exec(statement).all()
            for fr_info in results:
                DocumentFRToContentRepository.delete_by_fr_info_id(fr_info.fr_info_id)
                session.delete(fr_info)
            session.commit()

    @classmethod
    def get_all_fr_groups(
        cls,
        project_id: str,
        get_selected: bool = False,
        session: Optional[Session] = None,
    ) -> list[str]:
        session = session or Session(get_db_engine())

        with session:
            statement = select(cls.fr_group).where(
                (cls.project_id == project_id) & (cls.is_selected == get_selected)
            )
            results = session.exec(statement).all()
            return results
