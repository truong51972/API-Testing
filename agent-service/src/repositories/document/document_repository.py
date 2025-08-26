# src.repositories.document.document_repository
import logging
from typing import List

import langchain
from langchain_milvus import Milvus
from pydantic import model_validator, validate_call
from pymilvus import (
    Collection,
    CollectionSchema,
)

from src.base.service.base_embedding_service import BaseEmbeddingService
from src.base.service.base_llm_service import BaseLlmService
from src.base.service.base_milvus_service import BaseMilvusService
from src.models.document.document_model import DocumentModel
from src.utils.generate_milvus_field_schemas_from_pydantic import (
    generate_milvus_field_schemas_from_pydantic,
)


class DocumentRepository(BaseLlmService, BaseEmbeddingService, BaseMilvusService):
    collection_name: str = "document"

    @model_validator(mode="after")
    def __after_init(self):

        if not self.is_collection_exists():
            logging.info(
                f"Collection '{self.collection_name}' does not exist. Creating a new collection..."
            )

            fields = generate_milvus_field_schemas_from_pydantic(
                pydantic_model=DocumentModel, embedding_dim=self.embedding_dim
            )

            # create collection with schema
            schema = CollectionSchema(
                fields, description="Document collection with scalar fields"
            )
            self._collection = Collection(name=self.collection_name, schema=schema)

            # Create index for searching
            index_params = {
                "metric_type": "COSINE",
                "index_type": "HNSW",
                "params": {"M": 8, "efConstruction": 64},
            }
            self._collection.create_index(
                field_name="vector", index_params=index_params
            )

            self._collection.load()

        else:
            logging.info(f"Using '{self.collection_name}' collection.")
            self._collection = Collection(name=self.collection_name)

        return self

    @validate_call
    def embed_data(self, data: List[DocumentModel]) -> List[DocumentModel]:
        """Embed data using the configured embeddings model."""
        vectors = self.get_embedding().embed_documents([item.text for item in data])

        # insert vectors into the data
        for i, item in enumerate(data):
            item.vector = vectors[i]

        return data

    @validate_call
    def is_ids_exists(self, ids: List[int]) -> bool:
        """Check if all ids exist in the collection"""
        results = self._collection.query(f"id in {ids}")
        return len(results) > 0

    @validate_call
    def create_records(self, data: List[DocumentModel]):
        """Add records to the collection."""

        if self.is_ids_exists([item.id for item in data]):
            raise ValueError("Contains existing ids.")

        # Embed data
        data = self.embed_data(data)

        # Insert records into the collection
        self._collection.insert([item.model_dump() for item in data])
        self._collection.load()
        logging.info("Records added successfully.")

    @validate_call
    def update_records(self, data: List[DocumentModel]):
        """Edit existing records in the collection."""

        if not self.is_ids_exists([item.id for item in data if item.id is not None]):
            raise ValueError("Contains non-existing ids.")

        # Embed data
        data = self.embed_data(data)

        # Insert records into the collection
        self._collection.insert([item.model_dump() for item in data])
        self._collection.load()
        logging.info("Records edited successfully.")

    @validate_call
    def read_records(self, ids: List[int]) -> List[DocumentModel]:
        """Get records by ids."""

        if not self.is_ids_exists(ids):
            raise ValueError("Contains non-existing ids.")

        results = self._collection.query(
            expr=f"id IN {ids}",
            output_fields=[
                field.name
                for field in self._collection.schema.fields
                if field.name not in ["vector"]  # Exclude vector field
            ],
        )
        return results

    @validate_call
    def delete_records(self, id: List[int]) -> int:
        """delete_record by id

        Args:
            id (int): record id to delete

        Returns:
            int: total number of deleted records
        """
        return self._collection.delete(expr=f"id IN {id}")

    def search_by_text(
        self,
        query: str,
        document_amount: int = 1,
        document_offset: int = 0,
        doc_name: str = None,
        annotations: str = None,
    ):
        milvus = Milvus(
            embedding_function=self.get_embedding(),
            collection_name=self.collection_name,
            connection_args={"uri": self.milvus_uri, "token": self.milvus_token},
        )
        exprs = []

        if doc_name:
            exprs.append(f"doc_name == '{doc_name}'")
        if annotations:
            exprs.append(f"annotations == '{annotations}'")

        expr = " AND ".join(exprs) if exprs else None

        result = milvus.similarity_search(
            query=query, k=document_amount + document_offset, expr=expr
        )

        return result[document_offset : document_offset + document_amount]


if __name__ == "__main__":
    langchain.debug = True

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s:[%(levelname)-4s] [%(module)s] [%(funcName)s]: %(message)s",
    )

    data = [
        {
            "doc_name": "Document Name",
            "annotations": "Document Annotations",
            "text": "Document Text",
        }
    ]

    document_actions = DocumentRepository()

    print(
        document_actions.search_by_text(
            "Octoparse enables automated price tracking, data collection, and lead generation for e-commerce businesses.",
            doc_name="e-commerce",
            # annotations="test",
        )
    )
