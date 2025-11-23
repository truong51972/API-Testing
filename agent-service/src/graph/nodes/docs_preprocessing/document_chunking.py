# src.graph.nodes.docs_preprocessing.section_based_chunking
from typing import Any, Dict

from pydantic import BaseModel, validate_call
from sqlmodel import Session

from src import repositories
from src.common.common import split_by_size
from src.common.preprocessing import section_preprocessing
from src.models import DocsPreProcessingStateModel
from src.settings import get_db_engine


class DocumentChunkingNode(BaseModel):
    batch_size: int = 10
    max_workers: int = 2

    @validate_call
    def __call__(self, state: DocsPreProcessingStateModel) -> Dict[str, Any]:
        normalized_text = state.extra_parameters["normalized_text"]
        described_doc = state.extra_parameters["described_doc"]

        doc_name = state.doc_name
        doc_url = state.doc_url
        project_id = state.project_id

        table_of_contents, heading_to_contents = (
            section_preprocessing.get_table_and_contents(normalized_text)
        )

        doc_metadata_repo = repositories.DocumentMetadataRepository(
            project_id=project_id,
            doc_name=doc_name,
            table_of_contents=described_doc,
            raw_doc_path=doc_url,
        )
        doc_id = doc_metadata_repo.doc_id

        with Session(get_db_engine()) as session:
            session.add(doc_metadata_repo)
            session.commit()

        chunked_docs = []

        for heading, content in heading_to_contents.items():
            if content.strip() == "":
                continue
            text = f"{heading}\n{content}"
            chunked_docs.append(
                repositories.DocumentContentRepository(
                    doc_id=doc_id,
                    heading=heading,
                    text=text,
                )
            )

        batches = split_by_size(chunked_docs, self.batch_size)
        for batch in batches:
            repositories.DocumentContentRepository.create_records(data=batch)

        state.extra_parameters["chunked_doc"] = chunked_docs

        state.extra_parameters["doc_id"] = doc_id
        state.last_extra_parameter = "doc_id"

        return state
