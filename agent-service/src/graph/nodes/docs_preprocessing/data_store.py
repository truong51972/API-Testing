# src.graph.nodes.docs_preprocessing.data_cleaning
from typing import Any, Dict

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import model_validator, validate_call

from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel
from src.models.document.document_model import DocumentModel
from src.registry.nodes import register_node
from src.repositories.document.document_repository import DocumentRepository
from src.utils.common import split_by_size


@register_node("docs_preprocessing.data_store")
class DataStore(DocumentRepository):
    chunk_size: int = 1000
    chunk_overlap: int = 200
    batch_size: int = 10

    @model_validator(mode="after")
    def __after_init__(self):
        self.__text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=0,
            length_function=len,
        )
        return self

    @validate_call
    def __call__(self, state: DocsPreProcessingStateModel) -> Dict[str, Any]:
        data = state.messages[-1].content
        doc_name = state.doc_name
        doc_annotation = state.annotation

        chunks = self.__text_splitter.split_text(data)
        docs = [
            DocumentModel(
                text=chunk,
                doc_name=doc_name,
                annotations=doc_annotation,
            )
            for chunk in chunks
        ]

        batches = split_by_size(docs, self.batch_size)
        for batch in batches:
            self.create_records(batch)

        return {
            "messages": [],
        }
