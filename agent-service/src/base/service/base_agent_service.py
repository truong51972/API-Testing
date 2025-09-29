import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Union

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAI
from pydantic import Field, model_validator, validate_call

from src.base.service.base_multi_api_tokens import BaseMultiApiTokens
from src.enums.enums import LanguageEnum, ModelTypeEnum
from src.settings import ENVIRONMENT, GOOGLE_API_KEYS
from src.utils.common import split_by_size


class BaseAgentService(BaseMultiApiTokens):
    llm_model: str = Field(default="gemini-2.0-flash", min_length=5, max_length=100)

    llm_temperature: Optional[float] = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature for the LLM, controls randomness in responses.",
    )
    llm_top_p: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Top-p sampling for the LLM, controls diversity in responses.",
    )
    llm_top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=1000,
        description="Top-k sampling for the LLM, controls the number of highest probability tokens to consider.",
    )

    tools: Optional[List[object]] = Field(
        default_factory=list, description="List of tools that the agent can use."
    )

    path_to_prompt: dict[LanguageEnum, str] = Field(
        default_factory=dict, description="Prompts for different languages."
    )

    model_type: str = ModelTypeEnum.embedding.value

    # Private attributes with type hints
    _agents: list[Union[ChatGoogleGenerativeAI, GoogleGenerativeAI]]
    _system_prompts: dict[LanguageEnum, str]
    _prompt: ChatPromptTemplate

    @model_validator(mode="after")
    def __after_init(self):
        models = {"gemini": ChatGoogleGenerativeAI, "gemma": GoogleGenerativeAI}

        model_params = {
            "model": self.llm_model,
            "temperature": self.llm_temperature,
            "top_p": self.llm_top_p,
            "top_k": self.llm_top_k,
            "transport": "rest",
        }

        llms: list[Union[ChatGoogleGenerativeAI, GoogleGenerativeAI]] = []

        model_type = self.llm_model.split("-")[0]
        for google_api_key in GOOGLE_API_KEYS:
            _model_params = model_params.copy()
            _model_params["google_api_key"] = google_api_key

            llms.append(models[model_type](**_model_params))

        self._reset_round_robin()

        if self.tools:
            self._agents = [llm.bind_tools(self.tools) for llm in llms]
        else:
            self._agents = llms

        self.load_system_prompt()
        return self

    def _get_agent(self) -> Union[ChatGoogleGenerativeAI, GoogleGenerativeAI]:
        return self._agents[self._get_next_model_index()]

    @validate_call
    def load_system_prompt(self):
        self._system_prompts = {}

        for lang, path in self.path_to_prompt.items():
            try:
                with open(path, "r") as f:
                    self._system_prompts[lang] = f.read()
            except Exception as e:
                logging.error(f"Failed to load prompt for {lang} from {path}: {e}")

    @validate_call
    def set_system_prompt(self, lang: LanguageEnum):
        if ENVIRONMENT == "dev":
            logging.info("Reloading system prompt...")
            self.load_system_prompt()

        if lang not in self._system_prompts:
            raise ValueError(f"System prompt for language {lang} not loaded.")

        system_prompt = self._system_prompts[lang]

        self._prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
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
        # Handle batch_size = -1 as "all in one batch"
        if batch_size == -1:
            batches = [invoke_inputs]
        else:
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
