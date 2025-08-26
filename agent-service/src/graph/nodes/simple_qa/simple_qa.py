# src.graph.nodes.docs_preprocessing.data_cleaning
from typing import Any, Dict

from pydantic import validate_call

from src.base.service.base_agent_service import BaseAgentService
from src.enums.enums import LanguageEnum
from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel


class SimpleQANode(BaseAgentService):
    llm_model: str = "gemini-2.0-flash-lite"
    llm_temperature: float = 0.0
    llm_top_p: float = 0.1
    llm_top_k: int = 3

    path_to_prompt: dict[LanguageEnum, str] = {
        LanguageEnum.VI: "src/graph/nodes/simple_qa/prompts/simple_qa_vi.txt",
        LanguageEnum.EN: "src/graph/nodes/simple_qa/prompts/simple_qa_en.txt",
    }

    @validate_call
    def __call__(self, state: DocsPreProcessingStateModel) -> Dict[str, Any]:
        data = state.messages[-1].content
        self.set_system_prompt(LanguageEnum.VI)

        output = self.run({"input": data, "chat_history": state.messages[-5:]})

        return {
            "messages": [output],
        }
