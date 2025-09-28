# src.graph.nodes.docs_preprocessing.section_based_chunking
from typing import Any, Dict

from langchain_core.messages import AIMessage
from pydantic import BaseModel, validate_call
from sqlmodel import Session

from src import repositories
from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel
from src.models.document.document_model import DocumentModel
from src.repositories.document.document_repository import DocumentRepository
from src.settings import get_engine
from src.utils.common import split_by_size
from src.utils.preprocessing import section_preprocessing


class DocumentProcessingNode(BaseModel):
    batch_size: int = 10
    max_workers: int = 2

    @validate_call
    def __call__(self, state: DocsPreProcessingStateModel) -> Dict[str, Any]:
        data = state.messages[-1].content
        doc_name = state.doc_name
        doc_url = state.doc_url
        project_id = state.project_id

        table_and_contents, heading_to_contents = (
            section_preprocessing.get_table_and_contents(data)
        )

        doc_metadata_repo = repositories.DocumentMetadataRepository(
            project_id=project_id,
            doc_name=doc_name,
            table_of_contents=table_and_contents,
            raw_doc_path=doc_url,
        )
        doc_id = doc_metadata_repo.doc_id

        with Session(get_engine()) as session:
            session.add(doc_metadata_repo)
            session.commit()

        docs = []

        for heading, content in heading_to_contents.items():
            if content.strip() == "":
                continue
            text = f"{heading}\n{content}"
            docs.append(
                DocumentModel(
                    doc_id=doc_id,
                    text=text,
                )
            )

        batches = split_by_size(docs, self.batch_size)
        for batch in batches:
            DocumentRepository().create_records(data=batch, overwrite=True)

        return_data = AIMessage(
            content=doc_id,
        )

        return {
            "messages": [return_data],
        }
