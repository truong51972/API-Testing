from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import Field, model_validator, validate_call

from src.utils.common import split_by_size

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

    @validate_call
    def runs(
        self, invoke_inputs: list[dict], batch_size: int = -1, api_key_index: int = -1
    ):
        _prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ]
        )

        batches = split_by_size(invoke_inputs, batch_size)
        chain = _prompt | self._agent

        responses = []
        for batch in batches:
            responses.extend(chain.batch(batch))

        return responses

    def _thread_target_runner(self, batch: list[dict]):
        current_class = self.__class__
        config_data = self.model_dump()
        manual_instance = current_class(**config_data)
        return manual_instance.runs(batch)

    @validate_call
    def runs_parallel(
        self,
        invoke_inputs: list[dict],
        batch_size: int,
        max_workers: int = 3,
    ):
        batches = split_by_size(invoke_inputs, batch_size)

        responses = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results_iterator = executor.map(self._thread_target_runner, batches)
            for result in results_iterator:
                responses.extend(result)

        return responses
