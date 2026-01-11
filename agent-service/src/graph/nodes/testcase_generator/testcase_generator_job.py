# src.graph.nodes.testcase_generator.testcase_generator
from typing import Any, Dict

from pydantic import BaseModel, validate_call
from sqlmodel import Session

from src.models import TestcasesGenStateModel
from src.settings import get_db_engine, logger


class TestcaseGeneratorJob(BaseModel):
    @validate_call
    def __call__(self, state: TestcasesGenStateModel) -> Dict[str, Any]:
        all_fr_infos = state.extra_parameters["all_fr_infos"]
        current_fr_index = state.extra_parameters.get("current_fr_index", -1)

        if current_fr_index < len(all_fr_infos) - 1:
            current_fr_index += 1
            logger.info(
                f"Current FR group to process: {current_fr_index}/{len(all_fr_infos)}"
            )
            state.extra_parameters["progress"] = "in_progress"
        else:
            logger.info("All FR groups have been processed. Job completed.")

            with Session(get_db_engine()) as session:
                for _, test_entities in state.test_case_infos.items():
                    test_suite = test_entities.get("test_suite")
                    test_cases = test_entities.get("test_cases", [])
                    session.add(test_suite)
                    session.commit()

                    session.add_all(test_cases)
                    session.commit()

            state.extra_parameters["progress"] = "completed"

        # Ensure keys exist in extra_parameters
        state.extra_parameters["collected_documents"] = state.extra_parameters.get(
            "collected_documents", {}
        )
        state.extra_parameters["standardized_documents"] = state.extra_parameters.get(
            "standardized_documents", {}
        )

        state.extra_parameters["all_fr_infos"] = all_fr_infos
        state.extra_parameters["current_fr_index"] = current_fr_index

        return state


def orchestrate_job(state: TestcasesGenStateModel) -> str:
    return state.extra_parameters.get("progress", "completed")


if __name__ == "__main__":
    pass
