from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from src import models, repositories
from src.graph.workflows import TestCaseGenerationWorkflow

router = APIRouter(prefix="/test-entities", tags=["Test Entities"])


@router.post("/generate")
def docs_preprocessing(
    item: models.TestcasesGenStateModel, background_tasks: BackgroundTasks
) -> models.StandardOutputModel:
    workflow = TestCaseGenerationWorkflow()

    background_tasks.add_task(
        workflow.invoke,
        input_data=item,
    )

    return {
        "result": {"code": ["0000"], "description": "Work in progress!"},
        "data": {},
    }


@router.get("/test-suites/{project_id}")
def get_test_suites_by_project_id(
    project_id: str,
) -> models.StandardOutputModel:
    test_suites = repositories.TestSuiteRepository.get_all_by_project_id(
        project_id=project_id,
    )

    return models.StandardOutputModel(
        result={"code": ["0000"], "description": "Success"},
        data={"test_suites": test_suites},
    )


@router.get("/test-cases/{test_suite_id}")
def get_test_cases_by_test_suite_id(
    test_suite_id: str,
) -> models.StandardOutputModel:
    test_cases = repositories.TestCaseRepository.get_all_by_test_suite_id(
        test_suite_id=test_suite_id,
    )

    return models.StandardOutputModel(
        result={"code": ["0000"], "description": "Success"},
        data={"test_cases": test_cases},
    )


class SelectTestCasesForExecutionModel(BaseModel):
    test_case_ids: list[str]
    execute: bool


@router.post("/test-cases/select")
def select_test_cases_for_execution(
    item: SelectTestCasesForExecutionModel,
) -> models.StandardOutputModel:
    test_cases = repositories.TestCaseRepository.select_for_execution(
        test_case_ids=item.test_case_ids,
        execute=item.execute,
    )

    return models.StandardOutputModel(
        result={"code": ["0000"], "description": "Success"},
        data={"test_cases": test_cases},
    )
