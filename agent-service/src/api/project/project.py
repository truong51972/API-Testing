from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src import repositories

router = APIRouter(prefix="/project", tags=["Project"])


class FileResponseModel(BaseModel):
    file_id: str
    file_name: str


@router.post("/create")
def create_project(
    project: repositories.ProjectRepository,
) -> repositories.ProjectRepository:

    project = project.create()
    return project


@router.get("/all")
def get_all_projects() -> list[repositories.ProjectRepository]:
    projects = repositories.ProjectRepository().get_all()
    return projects


@router.post("/delete/{project_id}")
def delete_project(project_id: str) -> None:
    if repositories.ProjectRepository.delete_by_id(project_id):
        return {"message": "Project deleted successfully"}

    raise HTTPException(status_code=400, detail="Project not found")
