# src.graph.nodes.docs_preprocessing.data_cleaning
from typing import Any, Dict

from pydantic import validate_call

from src.base.service.base_agent_service import BaseAgentService
from src.enums.enums import LanguageEnum
from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel
from src.registry.nodes import register_node

prompts = {}
with open("src/graph/nodes/simple_qa/prompts/simple_qa_vn.txt", "r") as f:
    prompts[LanguageEnum.VI] = f.read()

with open("src/graph/nodes/simple_qa/prompts/simple_qa_en.txt", "r") as f:
    prompts[LanguageEnum.EN] = f.read()


@register_node("simple_qa.simple_qa")
class SimpleQA(BaseAgentService):
    llm_model: str = "gemini-2.0-flash-lite"
    llm_temperature: float = 0.0
    llm_top_p: float = 0.1
    llm_top_k: int = 3

    @validate_call
    def __call__(self, state: DocsPreProcessingStateModel) -> Dict[str, Any]:
        data = state.messages[-1].content
        self.load_system_prompt(prompts[LanguageEnum.VI])

        output = self.run({"input": data, "chat_history": state.messages[-5:]})

        return {
            "messages": [output],
        }
