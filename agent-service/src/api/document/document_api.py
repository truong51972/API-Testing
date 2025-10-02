from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from src import repositories
from src.settings import get_engine

router = APIRouter(prefix="/document", tags=["Document"])


class CreateProjectResponseModel(BaseModel):
    project_id: str


@router.get("/all/{project_id}")
def get_all_projects(project_id: str) -> list[repositories.DocumentMetadataRepository]:
    documents = repositories.DocumentMetadataRepository.get_by_project_id(
        project_id=project_id
    )
    return documents


@router.post("/delete/{doc_id}")
def delete_document(doc_id: str) -> None:
    if repositories.DocumentMetadataRepository.delete_by_id(doc_id):
        return {"message": "Document deleted successfully"}

    raise HTTPException(status_code=400, detail="Document not found")
