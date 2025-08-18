import logging
from random import choice
from typing import Optional

# for validation
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pydantic import BaseModel, Field, model_validator

from src.settings import GOOGLE_API_KEYS


class BaseEmbeddingService(BaseModel):
    embedding_model: str = Field(
        default="gemini-embedding-001", min_length=5, max_length=100
    )

    embedding_dim: Optional[int] = Field(
        default=None,
        ge=1,
        description="The dimension of the embeddings, set after initialization if get_embedding_dim is True.",
    )

    @model_validator(mode="after")
    def __after_init(self):
        random_api_key = choice(GOOGLE_API_KEYS)
        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=self.embedding_model, google_api_key=random_api_key, transport="rest"
        )

        if self.embedding_dim is None:
            self.embedding_dim = len(
                self._embeddings.embed_documents(["get embedding dimension"])[0]
            )
            logging.info(f"Embedding dimension: {self.embedding_dim}")

        return self
