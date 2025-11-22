import logging
from typing import Optional

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pydantic import Field, model_validator

from src.base.service.base_multi_api_tokens import BaseMultiApiTokens
from src.enums.enums import ModelTypeEnum


class BaseEmbeddingService(GoogleGenerativeAIEmbeddings):
    model: str = Field(default="gemini-embedding-001", min_length=5, max_length=100)

    embedding_dim: Optional[int] = Field(
        default=None,
        ge=1,
        description="The dimension of the embeddings",
    )

    @model_validator(mode="after")
    def __after_init(self):
        return self

    def embed_query(self, text: str) -> list[float]:
        embedding = super().embed_query(text, output_dimensionality=self.embedding_dim)

        return embedding

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = super().embed_documents(
            texts, output_dimensionality=self.embedding_dim
        )

        return embeddings
