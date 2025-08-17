from random import choice
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAI

# for validation
from pydantic import BaseModel, Field, model_validator

from src.settings import GOOGLE_API_KEYS


class BaseLlmService(BaseModel):
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

    @model_validator(mode="after")
    def __after_init(self):
        random_api_key = choice(GOOGLE_API_KEYS)
        print(random_api_key)
        if self.llm_model.startswith("gemini"):
            self._llm = ChatGoogleGenerativeAI(
                model=self.llm_model,
                temperature=self.llm_temperature,
                top_p=self.llm_top_p,
                top_k=self.llm_top_k,
                google_api_key=random_api_key,
            )
        elif self.llm_model.startswith("gemma"):
            self._llm = GoogleGenerativeAI(
                model=self.llm_model,
                temperature=self.llm_temperature,
                top_p=self.llm_top_p,
                top_k=self.llm_top_k,
                google_api_key=random_api_key,
            )
        return self
