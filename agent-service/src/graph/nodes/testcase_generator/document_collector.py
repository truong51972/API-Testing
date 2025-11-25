# src.graph.nodes.testcase_generator.document_collector
import json
import logging
from typing import Any, Dict, List, Optional, Union

from langchain_core.output_parsers import JsonOutputParser
from pydantic import validate_call
from sqlmodel import Session

from src import repositories
from src.base.service.base_agent_service import BaseAgentService
from src.enums.enums import LanguageEnum
from src.graph.tools.document.document_search import search_documents
from src.models import TestcasesGenStateModel
from src.settings import get_db_engine


class DocumentCollector(BaseAgentService):
    llm_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0

    llm_top_p: Optional[float] = 0.1

    llm_thinking_budget: Optional[int] = -1

    path_to_prompt: dict[LanguageEnum, str] = {
        LanguageEnum.VI: "src/graph/nodes/testcase_generator/prompts/document_collector_vi.md",
        LanguageEnum.EN: "src/graph/nodes/testcase_generator/prompts/document_collector_en.md",
    }

    @validate_call
    def __call__(self, state: TestcasesGenStateModel) -> Dict[str, Any]:
        lang = state.lang
        fr_group = state.all_fr_groups[0]
        all_docs_toc = state.all_docs_toc
        self.set_system_lang(lang)

        input_data = f"* **Function Name**: '{fr_group}'\n{all_docs_toc}"

        response = self.run(human=input_data).content

        json_parser = JsonOutputParser()
        response = json_parser.parse(response)

        collected_documents = ""

        session = Session(get_db_engine())

        for part, docs in response.items():
            collected_documents += f"{part}\n"
            if not docs:
                collected_documents += "NONE\n"

            for doc_name, headings in docs.items():
                doc_id = repositories.DocumentMetadataRepository.get_doc_id_by_doc_name(
                    project_id=state.project_id,
                    doc_name=doc_name,
                    session=session,
                )
                if not doc_id:
                    raise ValueError(
                        f"Document '{doc_name}' not found in project '{state.project_id}'"
                    )
                for heading in headings:
                    content = repositories.DocumentContentRepository.get_doc_by_heading(
                        doc_id=doc_id,
                        heading=heading,
                        session=session,
                    )
                    if not content:
                        logging.warning(
                            f"Heading '{heading}' not found in document '{doc_name}'! Searching by vector!"
                        )
                        content = search_documents(
                            query=heading,
                            project_id=state.project_id,
                            doc_id=doc_id,
                            top_k=1,
                        )

                    # remove first line if it contains the heading
                    if content and content[0].text.startswith(heading):
                        content[0].text = content[0].text[len(heading) :].strip()

                    collected_documents += f"{content[0].text}\n"

        state.extra_parameters["collected_documents"] = collected_documents
        return state


if __name__ == "__main__":
    from .document_preparator import DocumentPreparator

    document_preparator = DocumentPreparator()
    response = document_preparator(
        TestcasesGenStateModel(
            project_id="ae4750b9-fc21-4510-a2f4-bb7d3c47b830",
            lang=LanguageEnum.EN,
        )
    )

    document_collector = DocumentCollector()
    response = document_collector(response)

    print(response.extra_parameters["collected_documents"])
