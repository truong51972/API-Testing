from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src import repositories
from src.models import ProjectModel, StandardOutputModel

router = APIRouter(prefix="/projects", tags=["Project"])


class CreateProjectResponseModel(BaseModel):
    project_id: str


@router.put("/", response_model=StandardOutputModel)
def create_project(project: ProjectModel):
    project = repositories.ProjectRepository(**project.model_dump()).create()

    response = StandardOutputModel(
        result={
            "code": ["0000"],
            "description": "Project created successfully",
        },
        data={"project_id": project.project_id},
    )
    return response


class GetAllProjectsResponseModel(BaseModel):
    user_id: str
    page_no: int
    page_size: int


@router.post("/all")
def get_all_projects(
    items: GetAllProjectsResponseModel,
) -> StandardOutputModel:
    projects = repositories.ProjectRepository().get_all(user_id=items.user_id)

    response = StandardOutputModel(
        result={
            "code": ["0000"],
            "description": "Projects retrieved successfully",
        },
        data={"projects": projects},
    )
    return response


class DeleteProjectResponseModel(BaseModel):
    project_id: str


@router.delete("/")
def delete_project(items: DeleteProjectResponseModel) -> StandardOutputModel:
    if repositories.ProjectRepository.delete_by_id(items.project_id):
        response = StandardOutputModel(
            result={
                "code": ["0000"],
                "description": "Project deleted successfully",
            },
            data=items.model_dump(),
        )
        return response

    raise HTTPException(status_code=400, detail="Project not found")
