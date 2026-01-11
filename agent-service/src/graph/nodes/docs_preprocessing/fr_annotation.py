# src.graph.nodes.docs_preprocessing.fr_annotation
import re
from typing import Any, Dict

from langchain_core.messages import AIMessage
from pydantic import validate_call
from sqlalchemy.exc import NoResultFound
from sqlmodel import Session, select

from src import repositories
from src.base.service.base_agent_service import BaseAgentService
from src.cache.cache_func_wrapper import cache_func_wrapper
from src.enums.enums import LanguageEnum
from src.settings import get_db_engine


class FrAnnotationNode(BaseAgentService):
    llm_model: str = "gemini-2.0-flash"
    llm_temperature: float = 0.0
    llm_top_p: float = 0.1
    llm_top_k: int = 3

    chunk_size: int = 1000
    batch_size: int = 10
    max_workers: int = 5

    path_to_prompt: dict[LanguageEnum, str] = {
        LanguageEnum.VI: "src/graph/nodes/docs_preprocessing/prompts/fr_annotation_vi.txt",
        LanguageEnum.EN: "src/graph/nodes/docs_preprocessing/prompts/fr_annotation_en.txt",
    }

    def call_agent(self, human: str, messages: list[AIMessage] = []) -> AIMessage:
        response = self.run(human, messages, no_cache=True)
        return response

    def analyze_tocs_documents(
        self, document_metadata_repos: list[repositories.DocumentMetadataRepository]
    ) -> str:
        tocs = ""

        toc_doc_placeholder = "<doc_{i_0}>\n{text}\n</doc_{i_1}>"
        for i, document_metadata in enumerate(document_metadata_repos):
            doc_toc = document_metadata.table_of_contents

            toc_doc = toc_doc_placeholder.format(i_0=i, i_1=i, text=doc_toc)
            tocs += toc_doc + "\n"

        response = self.call_agent(tocs)

        return response

    def extract_frs(self, text: str) -> Dict[str, Any]:
        """
        Extract functional requirements (FRs) from the given text using regular expressions.

        Args:
            text (str): The input text containing FR annotations.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing the extracted FRs.

        Code Example:
        ```
            text = "[0]1.1 - Register\\n[1]1.2 - Login\\n[2]1.3 - Logout"
            extracted_frs = extract_frs(text)
            print(extracted_frs)
            # Output: [{'group': 'm-fr-001: Register', 'frs': [{'doc': '1.1', 'heading': 'Register'}, {'doc': '1.2', 'heading': 'Login'}, {'doc': '1.3', 'heading': 'Logout'}]}]
        ```
        """
        group_regex = r"([mu]-fr-\d+\:\s*.+)\n((?:\[\d+\][^\n]+\n)+)<--->"
        fr_regex = r"\[(\d+)\]([\d\.]+)"

        groups = re.findall(group_regex, text)
        grouped_frs = {}

        for group_name, group_content in groups:
            frs = re.findall(fr_regex, group_content)
            grouped_frs[group_name] = [
                {"doc": doc, "heading": heading} for doc, heading in frs
            ]
        return grouped_frs

    @validate_call
    def __call__(self, state) -> Dict[str, Any]:
        self.set_system_lang(state.lang)
        project_id = state.project_id

        grouped_frs = {}
        with Session(get_db_engine()) as session:
            if not repositories.ProjectRepository.is_exist(
                project_id=project_id, session=session
            ):
                raise NoResultFound(f"Project with ID {project_id} does not exist.")

            # Clear existing FR info and mappings for the project
            repositories.DocumentFRInfoRepository.delete_by_project_id(
                project_id=project_id, session=session
            )

            document_metadata_repos = (
                repositories.DocumentMetadataRepository.get_by_project_id(
                    project_id=project_id, session=session
                )
            )

            if not document_metadata_repos:
                raise NoResultFound(f"No documents found for project ID {project_id}.")

            response = self.analyze_tocs_documents(document_metadata_repos)

            grouped_frs = self.extract_frs(response.content)

            for group_name, doc_infos in grouped_frs.items():
                fr_info = repositories.DocumentFRInfoRepository(
                    project_id=project_id, fr_group=group_name
                )
                session.add(fr_info)

                for doc_info in doc_infos:
                    doc_content_repo = session.exec(
                        select(repositories.DocumentContentRepository).where(
                            repositories.DocumentContentRepository.heading.like(
                                f"{doc_info['heading']} -%"
                            ),
                        )
                    ).first()
                    if doc_content_repo:
                        fr_to_content = repositories.DocumentFRToContentRepository(
                            fr_info_id=fr_info.fr_info_id,
                            content_id=doc_content_repo.content_id,
                        )
                        session.add(fr_to_content)

                session.commit()

            repositories.ProjectRepository.update_updated_at(
                project_id=project_id, session=session
            )

        return_data = AIMessage(content=[grouped_frs])

        return {
            "messages": [return_data],
        }


if __name__ == "__main__":
    node = FrAnnotationNode()

    class DummyState:
        lang = LanguageEnum.EN
        project_id = "26292c94-45fd-4cb7-bdc1-368a3028ebad"

    node(DummyState())
