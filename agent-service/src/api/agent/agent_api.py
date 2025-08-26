from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from sqlmodel import SQLModel

# from src.cache.agent_state_cache_wrapper import agent_state_cache_wrapper
from src.graph.workflows.simple_qa import SimpleQAWorkflow

# from src.models.agent.agent_state_model import AgentStateModel
from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel
from src.settings import get_engine

# Load database configuration from environment variables (Docker Compose)

ai_agent = None  # Global variable to hold the AI agent instance


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ai_agent

    SQLModel.metadata.create_all(get_engine())

    yield


router = APIRouter(lifespan=lifespan)


# @agent_state_cache_wrapper
# def agent_invoke(agent_state: AgentStateModel) -> AgentStateModel:
#     """
#     Invoke the AI agent with the provided agent state.
#     """
#     result = ai_agent.invoke(agent_state)
#     processed_state = AgentStateModel.model_validate(result)
#     return processed_state


@router.post("/ai_agent")
def ai_agent_v2_api(
    request: DocsPreProcessingStateModel,
) -> DocsPreProcessingStateModel:
    """
    Endpoint to handle AI agent requests (v2).
    """
    # Load conversation from cache

    workflow = SimpleQAWorkflow()

    return workflow.invoke(request)
