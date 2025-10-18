from fastapi import APIRouter

from src.deploy_model import deploy_model

router = APIRouter(prefix="/llm", tags=["LLM"])


@router.post("/deploy")
def deploy_model_endpoint(model_name: str):
    deploy_model(model_name)
    return {"model": model_name, "status": "Model deployment initiated"}
