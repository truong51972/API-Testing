from src.api.agent.agent_api import router as agent_router
from src.api.common.common_api import router as common_router
from src.api.document.document_api import router as document_router
from src.api.feature_selection.feature_selection_api import (
    router as feature_selection_router,
)
from src.api.file.file import router as router_file
from src.api.project.project import router as project_router
from src.api.test_suite.test_suite_api import router as test_suite_router

all_routers = [
    common_router,
    agent_router,
    test_suite_router,
    router_file,
    document_router,
    project_router,
    feature_selection_router,
]
