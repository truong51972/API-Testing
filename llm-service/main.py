from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers import all_routers

app = FastAPI(
    docs_url="/llm-service/llm/api/docs",
    redoc_url="/llm-service/llm/api/redoc",
    openapi_url="/llm-service/llm/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hoặc list domain cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in all_routers:
    app.include_router(router, prefix="/llm-service/llm/api")
