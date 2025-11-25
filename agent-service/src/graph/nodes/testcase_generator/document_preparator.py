# src.graph.nodes.testcase_generator.document_preparator
from typing import Any, Dict

from pydantic import BaseModel, validate_call
from sqlmodel import Session

from src import repositories
from src.models import TestcasesGenStateModel
from src.settings import get_db_engine


class DocumentPreparator(BaseModel):
    @validate_call
    def __call__(self, state: TestcasesGenStateModel) -> TestcasesGenStateModel:
        project_id = state.project_id
        session = Session(get_db_engine())

        all_fr_infos = repositories.DocumentFRInfoRepository.get_all_fr_groups(
            project_id=project_id,
            get_selected=True,
            session=session,
        )
        state.all_fr_groups = [
            fr_info.split(":")[1].strip() for fr_info in all_fr_infos
        ]

        docs_metadata = repositories.DocumentMetadataRepository.get_by_project_id(
            project_id=project_id,
            session=session,
        )
        all_docs_toc = "* **Table of Contents (ToC):**\n\n"

        for doc_metadata in docs_metadata:
            all_docs_toc += f"Document Name: {doc_metadata.doc_name}\n{doc_metadata.table_of_contents}\n\n"

        state.all_docs_toc = all_docs_toc
        return state


if __name__ == "__main__":
    document_preparator = DocumentPreparator()

    response = document_preparator(
        TestcasesGenStateModel(
            project_id="ae4750b9-fc21-4510-a2f4-bb7d3c47b830",
        )
    )

    print(response.all_docs_toc)
