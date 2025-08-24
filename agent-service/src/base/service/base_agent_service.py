import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Union

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAI
from pydantic import Field, model_validator, validate_call

from src.enums.enums import LanguageEnum
from src.settings import ENVIRONMENT
from src.utils.common import split_by_size

from .base_llm_service import BaseLlmService


class BaseAgentService(BaseLlmService):
    tools: Optional[List[object]] = Field(
        default_factory=list, description="List of tools that the agent can use."
    )

    path_to_prompt: dict[LanguageEnum, str] = Field(
        default_factory=dict, description="Prompts for different languages."
    )

    @model_validator(mode="after")
    def __after_init(self):

        if self.tools:
            self._agents = [llm.bind_tools(self.tools) for llm in self._llms]
        else:
            self._agents = self._llms

        self.load_system_prompt()
        return self

    def _get_agent(self) -> Union[ChatGoogleGenerativeAI, GoogleGenerativeAI]:
        return self._agents[self._get_next_model_index()]

    @validate_call
    def load_system_prompt(self):
        self.__system_prompts = {}

        for lang, path in self.path_to_prompt.items():
            with open(path, "r") as f:
                self.__system_prompts[lang] = f.read()

    @validate_call
    def set_system_prompt(self, lang: LanguageEnum):
        if ENVIRONMENT == "dev":
            logging.info("Reloading system prompt...")
            self.load_system_prompt()

        self.__system_prompt = self.__system_prompts[lang]

        self._prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.__system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ]
        )

    @validate_call
    def run(self, invoke_input: dict):
        invoked_prompt = self._prompt.invoke(invoke_input)

        agent = self._get_agent()

        response = agent.invoke(invoked_prompt)
        return response

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
