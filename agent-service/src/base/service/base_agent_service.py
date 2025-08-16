from typing import List, Optional

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import Field, model_validator, validate_call

from .base_llm_service import BaseLlmService


class BaseAgentService(BaseLlmService):

    system_prompt: str = Field(
        default="",
        description="Prompt template for the agent. If not provided, a default prompt will be used.",
    )
    tools: Optional[List[object]] = Field(
        default_factory=list, description="List of tools that the agent can use."
    )

    @model_validator(mode="after")
    def __after_init(self):

        if self.tools:
            self._agent = self._llm.bind_tools(self.tools)
        else:
            self._agent = self._llm

        return self

    @validate_call
    def run(self, invoke_input: dict):
        _prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ]
        )

        response = self._agent.invoke(_prompt.invoke(invoke_input))
        return response
