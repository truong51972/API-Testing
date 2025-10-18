from src.api.common import common_api as common_router
from src.api.llm import llm_api as llm_router

all_routers = [llm_router.router, common_router.router]
