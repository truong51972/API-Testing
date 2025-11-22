import uuid
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from pydantic import (
    ConfigDict,
)
from sqlalchemy import Column
from sqlmodel import Field, Session, SQLModel

from src.base.service.base_embedding_service import BaseEmbeddingService
from src.settings import EMBEDDING_DIM, get_engine


class DocumentContentRepository(SQLModel, table=True):
    __tablename__ = "document_content"

    content_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="document external ID, must be unique.",
        max_length=64,
        primary_key=True,
    )

    doc_id: str = Field(
        description="doc ID, must be unique.",
        max_length=64,
        foreign_key="document_metadata.doc_id",
    )

    heading: str = Field(
        default_factory=str,
        description="heading for the content, used for displaying document information.",
        max_length=512,
    )

    text: Optional[str] = Field(
        default_factory=str,
        description="text for context, used for displaying document information.",
    )

    vector: list[float] = Field(
        sa_column=Column(Vector(EMBEDDING_DIM)),
        description="embedding vector for the document, must be a list of floats.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content_id": "123e4567-e89b-12d3-a456-426614174000",
                "doc_id": "doc_001",
                "text": "This is a sample document content.",
                "vector": [
                    0.1,
                    0.2,
                    0.3,
                    ...,
                    0.3072,
                ],  # Example vector with 3072 dimensions
            }
        }
    )

    @classmethod
    def create_records(
        cls,
        data: List["DocumentContentRepository"],
    ) -> List["DocumentContentRepository"]:

        embedding = BaseEmbeddingService()

        vectors = embedding.embed_documents([item.text for item in data])

        # insert vectors into the data
        for i, item in enumerate(data):
            item.vector = vectors[i]

        with Session(get_engine()) as session:
            session.add_all(data)
            session.commit()
            for record in data:
                session.refresh(record)
        return data
