import uuid
from datetime import datetime
from typing import Optional

from pydantic import (
    ConfigDict,
)
from sqlmodel import Field, Session, SQLModel, select

from src import repositories
from src.repositories.project.project_repository import ProjectRepository
from src.settings import get_db_engine, get_now_vn


class DocumentMetadataRepository(SQLModel, table=True):
    __tablename__ = "document_metadata"

    doc_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="document external ID, must be unique.",
        max_length=64,
        primary_key=True,
    )

    project_id: str = Field(
        description="Project ID, must be unique.",
        max_length=64,
        foreign_key="project.project_id",
    )

    doc_name: str = Field(
        default_factory=str,
        min_length=3,
        max_length=512,
        description="document name",
    )

    table_of_contents: str = Field(
        default_factory=str,
        min_length=3,
        max_length=10240,
        description="document name",
    )

    raw_doc_path: str = Field(
        default_factory=str,
        min_length=3,
        description="document name",
    )

    created_at: datetime = Field(
        default_factory=get_now_vn,
        description="Creation timestamp",
    )

    created_by: str = Field(
        default="user",
        min_length=3,
        max_length=512,
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "doc_id": "123e4567-e89b-12d3-a456-426614174000",
                "doc_name": "Sample Document",
                "table_of_content": "1. Introduction\n2. Main Content\n3. Conclusion",
                "raw_doc_path": "/path/to/document.pdf",
                "created_at": "2023-10-01T12:00:00",
                "created_by": "user",
            }
        }
    )

    @classmethod
    def get_by_project_id(
        cls, project_id: str, session: Optional[Session] = None
    ) -> list["DocumentMetadataRepository"]:
        session = session or Session(get_db_engine())
        with session:
            documents = session.exec(
                select(cls).where(cls.project_id == project_id)
            ).all()
        return documents

    @classmethod
    def delete_by_id(cls, doc_id: str, session: Optional[Session] = None) -> bool:
        session = session or Session(get_db_engine())
        with session:
            document = session.get(cls, doc_id)
            document_contents = session.exec(
                select(repositories.DocumentContentRepository).where(
                    repositories.DocumentContentRepository.doc_id == doc_id
                )
            ).all()
            for content in document_contents:
                session.delete(content)
                session.commit()

            if document:
                session.delete(document)
                session.commit()
                return True
            else:
                return False

    @classmethod
    def update_document_metadata(
        cls,
        document_metadata_repos: list["DocumentMetadataRepository"],
        session: Optional[Session] = None,
    ):
        session = session or Session(get_db_engine())
        with session:
            for document_metadata in document_metadata_repos:
                session.add(document_metadata)
            session.commit()

            ProjectRepository.update_updated_at(
                document_metadata_repos[0].project_id, session=session
            )

    @classmethod
    def get_doc_id_by_doc_name(
        cls,
        project_id: str,
        doc_name: str,
        session: Optional[Session] = None,
    ) -> Optional[str]:
        session = session or Session(get_db_engine())

        with session:
            statement = select(cls.doc_id).where(
                (cls.project_id == project_id) & (cls.doc_name == doc_name)
            )
            results = session.exec(statement).first()
            return results
