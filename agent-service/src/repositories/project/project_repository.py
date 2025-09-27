import uuid
from datetime import datetime

from pydantic import (
    ConfigDict,
)
from sqlmodel import Field, Session, SQLModel, select

from src.settings import get_engine


class ProjectRepository(SQLModel, table=True):
    __tablename__ = "project"

    project_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        description="Project ID, must be unique.",
    )

    project_name: str = Field(
        description="Name of the project",
        max_length=256,
    )

    created_at: datetime = Field(
        default=datetime.now(),
        description="Creation timestamp",
    )

    updated_at: datetime = Field(
        default=datetime.now(),
        description="Last update timestamp",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_name": "My Project",
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

    def get_all(self):
        """
        Retrieve all Project records from the database.
        Args:
            session: An initialized SQLModel session.
        Returns:
            List[ProjectRepository]: A list of all Project instances in the database.
        """
        with Session(get_engine()) as session:
            projects = session.exec(select(ProjectRepository)).all()
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
