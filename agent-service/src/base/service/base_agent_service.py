from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import Field, model_validator, validate_call

from src.utils.common import split_by_size

from .base_llm_service import BaseLlmService


class BaseAgentService(BaseLlmService):
    tools: Optional[List[object]] = Field(
        default_factory=list, description="List of tools that the agent can use."
    )

    @model_validator(mode="after")
    def __after_init(self):

        if self.tools:
            self._agents = [llm.bind_tools(self.tools) for llm in self._llms]
        else:
            self._agents = self._llms

        self._prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.__system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ]
        )

        return self

    def _get_agent(self):
        return self._agents[self._get_next_model_index()]

    @validate_call
    def run(self, invoke_input: dict):
        _invoke_input = invoke_input.copy()
        _invoke_input["system_prompt"] = self.system_prompt

        response = self._get_agent().invoke(self._prompt.invoke(_invoke_input))
        return response

    @validate_call
    def load_system_prompt(self, system_prompt: str):
        self.__system_prompt = system_prompt

    @validate_call
    def runs(self, invoke_inputs: list[dict], batch_size: int = -1):
        batches = split_by_size(invoke_inputs, batch_size)
        chain = self._prompt | self._get_agent()

        responses = []
        for batch in batches:
            _responses = chain.batch(batch)
            responses.extend(_responses)

        return responses

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
            results_iterator = executor.map(self.runs, batches)
            for result in results_iterator:
                responses.extend(result)

        return responses
