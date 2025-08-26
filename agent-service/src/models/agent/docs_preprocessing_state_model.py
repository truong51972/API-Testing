from typing import Annotated, List, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import (
    BaseModel,
    Field,
)

from src.enums.enums import LanguageEnum


class DocsPreProcessingStateModel(BaseModel):
    """
    Represents the state of an AI agent, including its name, description, and current status.
    """

    user_input: str = Field(
        description="User input text",
    )

    lang: LanguageEnum = Field(
        default=LanguageEnum.EN,
        description="Language of the document",
    )

    messages: Annotated[List[BaseMessage], add_messages] = Field(
        default_factory=list,
        description="Messages exchanged during the conversation",
    )

    doc_name: Optional[str] = Field(
        default_factory=str,
        description="Name of the document",
    )

    collection: Optional[str] = Field(
        default_factory=str,
        description="Collection for the document",
    )
