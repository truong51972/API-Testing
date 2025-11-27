import uuid
from datetime import datetime
from typing import Optional

from pydantic import (
    ConfigDict,
)
from sqlmodel import Field, Session, SQLModel, select

from src.settings import get_db_engine, get_now_vn


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
        with Session(get_db_engine()) as session:
            session.add(self)
            session.commit()
            session.refresh(self)

        return self

    @classmethod
    def is_exist(cls, project_id: str, session: Optional[Session] = None) -> bool:
        """
        Check if a Project record exists in the database by project_id.
        Args:
            session: An initialized SQLModel session.
            project_id: The ID of the project to check.
        Returns:
            bool: True if the project exists, False otherwise.
        """
        session = session or Session(get_db_engine())
        with session:
            project = session.get(cls, project_id)
            return project is not None

    @classmethod
    def get_all(
        cls, user_id: str, session: Optional[Session] = None
    ) -> list["ProjectRepository"]:
        """
        Retrieve all Project records from the database.
        Args:
            session: An initialized SQLModel session.
        Returns:
            List[ProjectRepository]: A list of all Project instances in the database.
        """
        session = session or Session(get_db_engine())
        with session:
            projects = session.exec(
                select(cls)
                .where(cls.user_id == user_id)
                .order_by(cls.created_at.desc())
            ).all()
        return projects

    @classmethod
    def delete_by_id(cls, project_id, session: Optional[Session] = None) -> bool:
        """
        Delete a Project record from the database by project_id.
        Args:
            session: An initialized SQLModel session.
            project_id: The ID of the project to delete.
        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        session = session or Session(get_db_engine())
        with session:
            project = session.get(cls, project_id)
            if project:
                session.delete(project)
                session.commit()
                return True
            return False

    @classmethod
    def update_updated_at(
        cls, project_id: str, session: Optional[Session] = None
    ) -> bool:
        """
        Update the 'updated_at' timestamp of a Project record.
        Args:
            session: An initialized SQLModel session.
            project_id: The ID of the project to update.
        Returns:
            bool: True if update was successful, False otherwise.
        """
        session = session or Session(get_db_engine())
        with session:
            project = session.get(cls, project_id)
            if project:
                project.updated_at = get_now_vn()
                session.add(project)
                session.commit()
                return True
            return False
