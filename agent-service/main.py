import os
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from src import exception, settings
from src.api.routers import all_routers
from src.models.api.standard_output import StandardOutputModel

settings.setup(verbose=True)


# 1. Set default header for api input (Request)
async def verify_input_header(
    x_service_name: str = Header("agent-service", alias="X-Service-Name"),
    authentication: str = Header("Basic YWRtaW46YWRtaW4=", alias="Authorization"),
):
    pass


security = HTTPBasic()


ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")


async def verify_basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Hàm xác thực Basic Auth.
    Sử dụng secrets.compare_digest để so sánh an toàn.
    """
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = ADMIN_USERNAME.encode("utf8")
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )

    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = ADMIN_PASSWORD.encode("utf8")
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# 2. Khởi tạo App với Global Dependency
app = FastAPI(
    docs_url="/agent-service/agent/api/docs",
    redoc_url="/agent-service/agent/api/redoc",
    openapi_url="/agent-service/agent/api/openapi.json",
    dependencies=[Depends(verify_input_header), Depends(verify_basic_auth)],
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


@app.exception_handler(exception.ApiValidationException)
async def custom_validation_handler(
    request: Request, exc: exception.ApiValidationException
):
    return JSONResponse(
        status_code=exc.status_code,
        content=StandardOutputModel(
            result={
                "code": exc.code,
                "description": exc.description,
            },
            data={},
        ).model_dump(),
    )


# 5. Routers
for router in all_routers:
    app.include_router(router, prefix="/api/v1")
