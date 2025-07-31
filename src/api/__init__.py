from src.api.agent.agent_api import router as agent_router
from src.api.common.common_api import router as common_router
from src.api.test_suit.test_suit_api import router as test_suit_router

all_routers = [
    common_router,
    # agent_router,
    test_suit_router,
]
