import uuid
from datetime import datetime

from pydantic import (
    ConfigDict,
)
from sqlmodel import Field, Session, SQLModel, select

from src import repositories
from src.settings import get_engine, get_now_vn


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
        max_length=512,
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
    def get_by_project_id(cls, project_id: str) -> list["DocumentMetadataRepository"]:
        documents = []
        with Session(get_engine()) as session:
            documents = session.exec(
                select(repositories.DocumentMetadataRepository).where(
                    repositories.DocumentMetadataRepository.project_id == project_id
                )
            ).all()
        return documents

    @classmethod
    def delete_by_id(cls, doc_id: str) -> bool:
        with Session(get_engine()) as session:
            document = session.get(repositories.DocumentMetadataRepository, doc_id)
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
