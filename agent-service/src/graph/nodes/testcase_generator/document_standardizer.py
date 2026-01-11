# src.graph.nodes.testcase_generator.document_standardizer
import json
import re
from typing import Optional

from pydantic import validate_call

from src import models
from src.base.service.base_agent_service import BaseAgentService
from src.enums.enums import LanguageEnum
from src.models import TestcasesGenStateModel
from src.settings import logger


def extract_api_info(text: str):
    """
    Extract HTTP Method, Endpoint, and Request Headers from standardized document text.
    Returns: dict with keys "method", "endpoint", "headers"
    """

    # Patterns
    method_pattern = r"\*\*HTTP Method:\*\*\s*`?([A-Z]+)`?"
    endpoint_pattern = r"\*\*Endpoint:\*\*\s*`?([^\n`]+)`?"

    # Cố gắng bắt cả endpoint dạng URL lẫn path
    url_pattern = r"(https?://[^\s`]+|/[a-zA-Z0-9\-_/.]+)"
    headers_pattern = r"\*\*Request Headers:\*\*\s*```json\s*(\{.*?\})\s*```"

    method_match = re.search(method_pattern, text)
    endpoint_match = re.search(endpoint_pattern, text)
    if not endpoint_match:
        endpoint_match = re.search(url_pattern, text)
    headers_match = re.search(headers_pattern, text, re.DOTALL)

    method = method_match.group(1) if method_match else None
    endpoint = endpoint_match.group(1) if endpoint_match else None
    headers = {}
    if headers_match:
        try:
            headers = json.loads(headers_match.group(1))
        except Exception as e:
            logger.warning(f"Error parsing headers JSON: {e}")

    logger.info(
        f"Extracted API Info - Method: {method}, Endpoint: {endpoint}, Headers: {headers}"
    )
    return models.ApiInfoModel(method=method, url=endpoint, headers=headers)


class DocumentStandardizer(BaseAgentService):
    llm_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0

    llm_thinking_budget: Optional[int] = -1

    path_to_prompt: dict[LanguageEnum, str] = {
        LanguageEnum.VI: "src/graph/nodes/testcase_generator/prompts/document_standardizer_vi.md",
        LanguageEnum.EN: "src/graph/nodes/testcase_generator/prompts/document_standardizer_en.md",
    }

    @validate_call
    def __call__(self, state: TestcasesGenStateModel) -> TestcasesGenStateModel:
        collected_documents = state.extra_parameters.get("collected_documents", None)

        all_fr_infos = state.extra_parameters["all_fr_infos"]
        current_fr_index = state.extra_parameters.get("current_fr_index", -1)
        current_fr_id = all_fr_infos[current_fr_index].fr_info_id

        if not collected_documents:
            raise ValueError("No collected documents found in state.extra_parameters")
        lang = state.lang
        self.set_system_lang(lang)

        no_cache = False
        retry_count = 0
        while True:
            standardized_documents = self.run(
                human=f"<Raw Data>{collected_documents[current_fr_id]}</Raw Data>",
                no_cache=no_cache,
            ).content
            logger.debug(f"Standardized Documents: \n{standardized_documents}")
            try:
                api_info = extract_api_info(standardized_documents)
                break
            except Exception as e:
                no_cache = True
                retry_count += 1

                if retry_count > 3:
                    raise e

                logger.warning(f"API info extraction error: {e}. Retrying...")
                continue

        state.extra_parameters["standardized_documents"][
            current_fr_id
        ] = standardized_documents
        state.test_case_infos.setdefault(current_fr_id, {})["api_info"] = api_info
        logger.info("Document standardization completed!")
        return state


if __name__ == "__main__":
    from .document_collector import DocumentCollector
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

    document_standardizer = DocumentStandardizer()
    response = document_standardizer(response)

    print(response.extra_parameters.get("standardized_documents"))
