# src.graph.nodes.testcase_generator.document_preparator
from pydantic import BaseModel, validate_call
from sqlmodel import Session

from src import repositories
from src.models import TestcasesGenStateModel
from src.settings import get_db_engine, logger


class DocumentPreparator(BaseModel):
    @validate_call
    def __call__(self, state: TestcasesGenStateModel) -> TestcasesGenStateModel:
        project_id = state.project_id
        session = Session(get_db_engine())

        all_fr_infos = repositories.DocumentFRInfoRepository.get_all_by_project_id(
            project_id=project_id,
            is_selected=True,
            session=session,
        )

        docs_metadata = repositories.DocumentMetadataRepository.get_by_project_id(
            project_id=project_id,
            session=session,
        )
        all_docs_toc = ""

        for doc_metadata in docs_metadata:
            all_docs_toc += f"<Document: {doc_metadata.doc_name}>"
            all_docs_toc += f"\n{doc_metadata.table_of_contents}\n"
            all_docs_toc += f"</Document: {doc_metadata.doc_name}>\n"

        state.extra_parameters["all_docs_toc"] = all_docs_toc
        state.extra_parameters["all_fr_infos"] = all_fr_infos

        logger.info("Preparing documents completed!")
        logger.debug(f"All Docs ToC: \n{all_docs_toc}")
        logger.debug(f"All FR Infos: \n{all_fr_infos}")
        return state


if __name__ == "__main__":
    document_preparator = DocumentPreparator()

    response = document_preparator(
        TestcasesGenStateModel(
            project_id="ae4750b9-fc21-4510-a2f4-bb7d3c47b830",
        )
    )

    print(response.all_docs_toc)
