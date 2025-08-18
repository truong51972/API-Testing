from typing import Annotated, List

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import (
    BaseModel,
    Field,
)


class DocsPreProcessingStateModel(BaseModel):
    """
    Represents the state of an AI agent, including its name, description, and current status.
    """

    user_input: str = Field(
        description="User input text",
    )

    lang: str = Field(
        default="en",
        description="Language of the document",
    )

    messages: Annotated[List[BaseMessage], add_messages] = Field(
        default_factory=list,
        description="Messages exchanged during the conversation",
    )

    doc_name: str = Field(
        description="Name of the document",
    )

    annotation: str = Field(
        description="Annotation for the document",
    )
