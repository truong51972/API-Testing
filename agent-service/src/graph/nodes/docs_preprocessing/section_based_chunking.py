# src.graph.nodes.docs_preprocessing.section_based_chunking
import logging
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import model_validator, validate_call

from src.base.service.base_agent_service import BaseAgentService
from src.enums.enums import LanguageEnum
from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel
from src.utils.preprocessing.section_preprocessing import (
    create_hierarchical_section_blocks,
)

prompts = {}

with open(
    "src/graph/nodes/docs_preprocessing/prompts/section_based_chunking_vn.txt", "r"
) as f:
    prompts[LanguageEnum.VI] = f.read()

with open(
    "src/graph/nodes/docs_preprocessing/prompts/section_based_chunking_en.txt", "r"
) as f:
    prompts[LanguageEnum.EN] = f.read()


class SectionBasedChunkingNode(BaseAgentService):
    llm_model: str = "gemma-3-27b-it"
    llm_temperature: float = 0.0
    llm_top_p: float = 0.1
    llm_top_k: int = 3

    @validate_call
    def __call__(self, state: DocsPreProcessingStateModel) -> Dict[str, Any]:
        data = state.messages[-1].content
        self.load_system_prompt(prompts[state.lang])

        hierarchical_section_blocks = create_hierarchical_section_blocks(data)

        text = "\n\n".join(hierarchical_section_blocks)
        return_data = AIMessage(content=hierarchical_section_blocks)

        return {
            "messages": [return_data],
        }
