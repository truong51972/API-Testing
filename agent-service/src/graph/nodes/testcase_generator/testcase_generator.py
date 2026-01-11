# src.graph.nodes.testcase_generator.testcase_generator
from typing import Any, Dict

from langchain_core.output_parsers import JsonOutputParser
from pydantic import validate_call

from src import repositories
from src.base.service.base_agent_service import BaseAgentService
from src.enums.enums import LanguageEnum
from src.models import TestcasesGenStateModel
from src.settings import logger


class TestCaseGenerator(BaseAgentService):
    llm_model: str = "vllm-QC-AI"
    llm_temperature: float = 0.0

    path_to_prompt: dict[LanguageEnum, str] = {
        LanguageEnum.VI: "src/graph/nodes/testcase_generator/prompts/testcase_generator_vi.md",
        LanguageEnum.EN: "src/graph/nodes/testcase_generator/prompts/testcase_generator_en.md",
    }

    def extract_clean_json_from_text(self, raw_text):
        """
        Clean a single text block & extract JSON test case.
        """
        json_parser = JsonOutputParser()
        data = json_parser.parse(raw_text)

        if isinstance(data, list):
            data = data[-1]
        elif isinstance(data, dict):
            pass

        return data

    @validate_call
    def __call__(self, state: TestcasesGenStateModel) -> Dict[str, Any]:
        lang = state.lang

        all_fr_infos = state.extra_parameters["all_fr_infos"]
        current_fr_index = state.extra_parameters.get("current_fr_index", -1)
        current_fr = all_fr_infos[current_fr_index]
        api_info = state.test_case_infos[current_fr.fr_info_id]["api_info"]

        standardized_documents = state.extra_parameters["standardized_documents"][
            current_fr.fr_info_id
        ]
        self.set_system_lang(lang)

        no_cache = False
        retry_count = 0
        while True:
            generated_testcases = self.run(
                human=standardized_documents, no_cache=no_cache
            ).content

            logger.debug(f"Generated Testcases Raw Output: \n{generated_testcases}")

            try:
                generated_testcases = self.extract_clean_json_from_text(
                    generated_testcases
                )
                request_body = generated_testcases.get("request_body", None)
                testcases = generated_testcases.get("testcases", None)
                if request_body is None or testcases is None:
                    raise ValueError(
                        "Generated testcases missing 'request_body' or 'testcases'"
                    )
                basic_validation_cases = testcases.get("basic_validation", None)
                business_logic_cases = testcases.get("business_logic", None)

                if basic_validation_cases is None or business_logic_cases is None:
                    raise ValueError(
                        "Generated testcases missing 'basic_validation' or 'business_logic' cases"
                    )

                break
            except Exception as e:
                no_cache = True
                retry_count += 1

                if retry_count > 3:
                    raise e

                logger.warning(f"Test case generation error: {e}. Retrying...")
                continue

        test_suite = repositories.TestSuiteRepository(
            fr_info_id=current_fr.fr_info_id,
            test_suite_name=current_fr.fr_group,
        )

        testcases = []

        for testcase in basic_validation_cases:
            _request_body = request_body.copy()

            for field, value in testcase.get("request_mapping", {}).items():
                _request_body[field] = value

            testcase = repositories.TestCaseRepository(
                test_suite_id=test_suite.test_suite_id,
                test_case_type="basic_validation",
                test_case_id=testcase.get("test_case_id", ""),
                test_case=testcase.get("test_case", ""),
                api_info=api_info.model_dump(),
                request_body=_request_body,
                expected_output=testcase.get("expected_output", {}),
            )
            testcases.append(testcase)

        for testcase in business_logic_cases:
            _request_body = request_body.copy()

            for field, value in testcase.get("request_mapping", {}).items():
                _request_body[field] = value

            testcase = repositories.TestCaseRepository(
                test_suite_id=test_suite.test_suite_id,
                test_case_type="business_logic",
                test_case_id=testcase.get("test_case_id", ""),
                test_case=testcase.get("test_case", ""),
                api_info=api_info.model_dump(),
                request_body=_request_body,
                expected_output=testcase.get("expected_output", {}),
            )
            testcases.append(testcase)

        state.test_case_infos[current_fr.fr_info_id] = {
            "test_suite": test_suite,
            "test_cases": testcases,
        }

        logger.info(
            f"Generated test cases for FR group: {current_fr.get_fr_group_name()}, total test cases: {len(testcases)}"
        )
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
