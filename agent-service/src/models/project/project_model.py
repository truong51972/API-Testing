import uuid
from datetime import datetime

from pydantic import ConfigDict, field_validator
from sqlalchemy import Column, DateTime, String
from sqlmodel import Field, SQLModel

from src import exception
from src.settings import get_now_vn
from src.types.project import DescriptionType, ProjectNameType
from src.types.user import UserIDType


class ProjectModel(SQLModel):
    project_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        description="Project ID, must be unique.",
    )

    user_id: UserIDType = Field(
        description="User ID associated with the project.",
    )

    project_name: ProjectNameType = Field(
        description="Name of the project",
        sa_column=Column(
            String(128),
            nullable=False,
            unique=True,
        ),
    )

    description: DescriptionType = Field(
        default_factory=str,
        description="Description of the project",
        sa_column=Column(
            String(512),
            nullable=True,
        ),
    )

    created_at: datetime = Field(
        default_factory=get_now_vn,
        description="Creation timestamp",
    )

    updated_at: datetime = Field(
        default_factory=get_now_vn,
        description="Last update timestamp",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "0",
                "project_name": "My Project",
                "description": "This is a sample project description.",
            }
        }
    )
