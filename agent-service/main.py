from fastapi import Depends, FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware

from src import settings
from src.api.routers import all_routers

settings.setup(verbose=True)


# 1. Set default header for api input (Request)
async def verify_input_header(
    x_service_name: str = Header("agent-service", alias="X-Service-Name")
):
    pass


# 2. Khởi tạo App với Global Dependency
app = FastAPI(
    docs_url="/agent-service/agent/api/docs",
    redoc_url="/agent-service/agent/api/redoc",
    openapi_url="/agent-service/agent/api/openapi.json",
    dependencies=[Depends(verify_input_header)],
)


# add custom middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    response = await call_next(request)

    # Add custom header
    response.headers["X-Service-Name"] = "agent-service"
    return response


# 4. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Routers
for router in all_routers:
    app.include_router(router, prefix="/api/v1")
