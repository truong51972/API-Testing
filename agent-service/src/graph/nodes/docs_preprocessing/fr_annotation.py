# src.graph.nodes.docs_preprocessing.fr_annotation
import re
from typing import Any, Dict

from langchain_core.messages import AIMessage
from pydantic import validate_call
from sqlmodel import Session

from src import repositories
from src.base.service.base_agent_service import BaseAgentService
from src.enums.enums import LanguageEnum
from src.settings import get_engine


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

    def call_agent(self, input: str, chat_history: list[AIMessage] = []) -> AIMessage:
        response = self.run({"input": input, "chat_history": chat_history})
        return response

    def analyze_documents(
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

    def remove_existing_fr_annotations(
        self, document_metadata_repos: list[repositories.DocumentMetadataRepository]
    ) -> list[repositories.DocumentMetadataRepository]:
        fr_pattern = r"<[mu]-fr-\d+>"
        for document_metadata in document_metadata_repos:
            document_metadata.table_of_contents = re.sub(
                fr_pattern, "", document_metadata.table_of_contents
            ).strip()
        return document_metadata_repos

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

    def update_tocs(
        self,
        grouped_frs: Dict[str, Any],
        document_metadata_repos: list[repositories.DocumentMetadataRepository],
    ) -> list[repositories.DocumentMetadataRepository]:
        for group_name, frs in grouped_frs.items():
            annotation = group_name.split(":")[0]
            for fr in frs:
                doc = fr["doc"]
                heading = fr["heading"]

                document_metadata_repo = document_metadata_repos[int(doc)]

                table_of_contents = document_metadata_repo.table_of_contents
                pattern = rf"^{re.escape(heading)}\s+\-\s+.*"
                result = re.search(pattern, table_of_contents, re.MULTILINE)

                if result:
                    document_metadata_repo.table_of_contents = (
                        table_of_contents.replace(
                            result.group(0), f"{result.group(0)}<{annotation}>"
                        )
                    )

        return document_metadata_repos

    @validate_call
    def __call__(self, state) -> Dict[str, Any]:
        self.set_system_prompt(state.lang)
        project_id = state.project_id

        grouped_frs = {}
        with Session(get_engine()) as session:
            document_metadata_repos = (
                repositories.DocumentMetadataRepository.get_by_project_id(
                    project_id=project_id, session=session
                )
            )

            document_metadata_repos = self.remove_existing_fr_annotations(
                document_metadata_repos
            )

            response = self.analyze_documents(document_metadata_repos)

            grouped_frs = self.extract_frs(response.content)

            document_metadata_repos = self.update_tocs(
                grouped_frs, document_metadata_repos
            )

            repositories.DocumentMetadataRepository.update_document_metadata(
                document_metadata_repos, session=session
            )

        return_data = AIMessage(content=[grouped_frs])

        return {
            "messages": [return_data],
        }
