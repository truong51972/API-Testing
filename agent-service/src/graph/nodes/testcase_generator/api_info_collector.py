# src.graph.nodes.testcase_generator.testcase_generator
import logging
from typing import Any, Dict, Optional

from langchain_core.output_parsers import JsonOutputParser
from pydantic import validate_call

from src import models
from src.base.service.base_agent_service import BaseAgentService
from src.enums.enums import LanguageEnum
from src.models import TestcasesGenStateModel


class APIInfoCollector(BaseAgentService):
    llm_model: str = "gemini-2.5-flash-lite"
    llm_temperature: float = 0.0

    llm_thinking_budget: Optional[int] = -1

    path_to_prompt: dict[LanguageEnum, str] = {
        LanguageEnum.VI: "src/graph/nodes/testcase_generator/prompts/api_info_collector_vi.md",
        LanguageEnum.EN: "src/graph/nodes/testcase_generator/prompts/api_info_collector_en.md",
    }

    def is_text_in_doc(self, text: str, document: str) -> bool:
        return text in document

    def is_header_in_doc(self, header: Dict[str, str], document: str) -> bool:
        for key, value in header.items():
            if key not in document:
                return False
            if value not in document:
                return False
        return True

    @validate_call
    def __call__(self, state: TestcasesGenStateModel) -> Dict[str, Any]:
        lang = state.lang
        all_fr_infos = state.extra_parameters["all_fr_infos"]
        current_fr_index = state.extra_parameters.get("current_fr_index", -1)
        current_fr_id = all_fr_infos[current_fr_index].fr_info_id
        standardized_documents = state.extra_parameters["standardized_documents"][
            current_fr_id
        ]

        self.set_system_lang(lang)
        json_parser = JsonOutputParser()

        no_cache = False
        api_info = None

        retry_limit = 5
        retry_count = 0

        while True:
            response = self.run(human=standardized_documents, no_cache=no_cache).content
            no_cache = True
            response = json_parser.parse(response)

            is_url_in_doc = self.is_text_in_doc(response["url"], standardized_documents)
            is_header_in_doc = self.is_header_in_doc(
                response["headers"], standardized_documents
            )

            if is_url_in_doc and is_header_in_doc:
                try:
                    api_info = models.ApiInfoModel(**response)
                    break
                except Exception as e:
                    logging.warning(f"API info validation error: {e}. Retrying...")
                    retry_count += 1
                    if retry_count >= retry_limit:
                        raise e
                    continue
            else:
                logging.warning(f"Invalid API info detected: {response}. Retrying...")
                retry_count += 1
                if retry_count >= retry_limit:
                    raise ValueError("Retry limit reached due to invalid API info.")

        state.test_case_infos.setdefault(current_fr_id, {})["api_info"] = api_info

        logging.info("API info collection completed!")
        return state


if __name__ == "__main__":
    pass
