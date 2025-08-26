# src.graph.nodes.docs_preprocessing.section_based_chunking
import logging
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import model_validator, validate_call

from src import cache
from src.base.service.base_agent_service import BaseAgentService
from src.enums.enums import LanguageEnum
from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel
from src.utils.preprocessing.section_preprocessing import (
    create_hierarchical_section_blocks,
)


class SectionBasedChunkingNode(BaseAgentService):
    llm_model: str = "gemma-3-27b-it"
    llm_temperature: float = 0.0
    llm_top_p: float = 0.1
    llm_top_k: int = 3

    batch_size: int = 10
    max_workers: int = 2

    path_to_prompt: dict[LanguageEnum, str] = {
        LanguageEnum.VI: "src/graph/nodes/docs_preprocessing/prompts/section_based_chunking_vi.txt",
        LanguageEnum.EN: "src/graph/nodes/docs_preprocessing/prompts/section_based_chunking_en.txt",
    }

    @cache.cache_func_wrapper
    def __chunk_and_annotate(self, text: str) -> list[Dict[str, Any]]:
        hierarchical_section_blocks = create_hierarchical_section_blocks(text)

        batches = [
            {
                "input": chunk,
                "chat_history": [],
            }
            for chunk in hierarchical_section_blocks
        ]
        annotations = self.runs_parallel(
            batches, batch_size=self.batch_size, max_workers=self.max_workers
        )

        result = []

        for i in range(len(hierarchical_section_blocks)):
            result.append(
                {
                    "content": hierarchical_section_blocks[i],
                    "annotation": annotations[i],
                }
            )
        return result

    @validate_call
    def __call__(self, state: DocsPreProcessingStateModel) -> Dict[str, Any]:
        data = state.messages[-1].content
        self.set_system_prompt(lang=state.lang)

        result = self.__chunk_and_annotate(data)

        return_data = AIMessage(content=result)

        return {
            "messages": [return_data],
        }
