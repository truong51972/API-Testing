from typing import Annotated, List, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field

from src.enums.enums import LanguageEnum


class DocsPreProcessingStateModel(BaseModel):
    """
    Represents the state of an AI agent, including its name, description, and current status.
    """

    doc_url: str = Field(
        description="URL of the document",
    )

    project_id: str = Field(
        description="Project ID, must be unique.",
    )

    lang: LanguageEnum = Field(
        default=LanguageEnum.EN,
        description="Language of the document",
    )

    doc_name: Optional[str] = Field(
        default_factory=str,
        description="Name of the document",
    )

    messages: Annotated[List[BaseMessage], add_messages] = Field(
        default_factory=list,
        description="Messages exchanged during the conversation",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "doc_url": "https://example.com/document.pdf",
                "project_id": "00000000-0000-0000-0000-000000000000",
            }
        }
    )
