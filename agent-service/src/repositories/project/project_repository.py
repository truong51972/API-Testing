import uuid
from datetime import datetime

from pydantic import (
    ConfigDict,
)
from sqlmodel import Field, Session, SQLModel, select

from src.settings import get_engine, get_now_vn


class ProjectRepository(SQLModel, table=True):
    __tablename__ = "project"

    project_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        description="Project ID, must be unique.",
    )

    user_id: str = Field(
        description="User ID associated with the project.",
    )

    project_name: str = Field(
        description="Name of the project",
        max_length=256,
    )

    description: str = Field(
        default_factory=str,
        description="Description of the project",
        max_length=512,
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

    def create(self):
        """
        Add a new Project record to the database.
        Args:
            session: An initialized SQLModel session.
        Returns:
            ProjectRepository: The instance added to the database.
        """
        with Session(get_engine()) as session:
            session.add(self)
            session.commit()
            session.refresh(self)

        return self

    def get_all(self, user_id: str):
        """
        Retrieve all Project records from the database.
        Args:
            session: An initialized SQLModel session.
        Returns:
            List[ProjectRepository]: A list of all Project instances in the database.
        """
        with Session(get_engine()) as session:
            projects = session.exec(
                select(ProjectRepository).where(ProjectRepository.user_id == user_id)
            ).all()
        return projects

    @classmethod
    def delete_by_id(cls, project_id):
        """
        Delete a Project record from the database by project_id.
        Args:
            session: An initialized SQLModel session.
            project_id: The ID of the project to delete.
        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        with Session(get_engine()) as session:
            project = session.get(cls, project_id)
            if project:
                session.delete(project)
                session.commit()
                return True
            return False
