from src.api.agent.agent_api import router as agent_router
from src.api.common.common_api import router as common_router
from src.api.test_suite.test_suite_api import router as test_suite_router

all_routers = [
    common_router,
    agent_router,
    test_suite_router,
]
