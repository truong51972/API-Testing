# src.graph.nodes.testcase_generator.testcase_generator
from typing import Any, Dict

from langchain_core.output_parsers import JsonOutputParser
from pydantic import validate_call

from src.base.service.base_agent_service import BaseAgentService
from src.enums.enums import LanguageEnum
from src.models import TestcasesGenStateModel


class TestCaseGenerator(BaseAgentService):
    llm_model: str = "vllm-QC-AI"
    llm_temperature: float = 0.1

    path_to_prompt: dict[LanguageEnum, str] = {
        LanguageEnum.VI: "src/graph/nodes/testcase_generator/prompts/testcase_generator_vi.md",
        LanguageEnum.EN: "src/graph/nodes/testcase_generator/prompts/testcase_generator_en.md",
    }

    @validate_call
    def __call__(self, state: TestcasesGenStateModel) -> Dict[str, Any]:
        lang = state.lang
        standardized_documents = state.extra_parameters["standardized_documents"]
        self.set_system_lang(lang)

        response = self.run(human=standardized_documents).content

        json_parser = JsonOutputParser()
        response = json_parser.parse(response)

        if isinstance(response, list):
            state.testcases.append(response[-1])
        elif isinstance(response, dict):
            state.testcases.append(response)

        state.all_fr_groups.pop(0)
        return state


if __name__ == "__main__":
    from .document_collector import DocumentCollector
    from .document_preparator import DocumentPreparator
    from .document_standardizer import DocumentStandardizer

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

    testcase_generator = TestCaseGenerator()
    response = testcase_generator(response)

    print(response.testcases)
