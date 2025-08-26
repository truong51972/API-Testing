import logging
from typing import Optional

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pydantic import Field, model_validator

from src.base.service.base_multi_api_tokens import BaseMultiApiTokens
from src.enums.enums import ModelTypeEnum
from src.settings import GOOGLE_API_KEYS


class BaseEmbeddingService(BaseMultiApiTokens):
    embedding_model: str = Field(
        default="gemini-embedding-001", min_length=5, max_length=100
    )

    embedding_dim: Optional[int] = Field(
        default=None,
        ge=1,
        description="The dimension of the embeddings, set after initialization if get_embedding_dim is True.",
    )
    model_type: str = ModelTypeEnum.embedding.value

    @model_validator(mode="after")
    def __after_init(self):
        model_params = {
            "model": self.embedding_model,
            "transport": "rest",
        }

        self._embeddings = []

        for google_api_key in GOOGLE_API_KEYS:
            _model_params = model_params.copy()
            _model_params["google_api_key"] = google_api_key

            self._embeddings.append(GoogleGenerativeAIEmbeddings(**_model_params))

        self._set_embedding_dim()
        self._reset_round_robin()
        return self

    def get_embedding(self):
        return self._embeddings[self._get_next_model_index()]

    def _set_embedding_dim(self):
        if self.embedding_dim is None:
            self.embedding_dim = len(
                self.get_embedding().embed_documents(["get embedding dimension"])[0]
            )
            logging.info(f"Embedding dimension: {self.embedding_dim}")
