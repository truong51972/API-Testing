from fastapi import APIRouter
from fastapi.responses import RedirectResponse


router = APIRouter(prefix="/common", tags=["Common"])


@router.get("/")
def read_root():
    return RedirectResponse(url="/api/docs")


@router.get("/health")
def health_check():
    return {"status": "ok"}
