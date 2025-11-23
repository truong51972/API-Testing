# src.graph.nodes.docs_preprocessing.section_based_chunking
from typing import Any, Dict

from pydantic import validate_call

from src.base.service.base_agent_service import BaseAgentService
from src.enums.enums import LanguageEnum
from src.models import DocsPreProcessingStateModel


class DocumentDescriptionNode(BaseAgentService):
    llm_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0.0

    path_to_prompt: dict[LanguageEnum, str] = {
        LanguageEnum.VI: "src/graph/nodes/docs_preprocessing/prompts/document_description_vi.md",
        LanguageEnum.EN: "src/graph/nodes/docs_preprocessing/prompts/document_description_en.md",
    }

    @validate_call
    def __call__(self, state: DocsPreProcessingStateModel) -> Dict[str, Any]:
        data = state.extra_parameters[state.last_extra_parameter].replace(
            "<heading>", ""
        )
        lang = state.lang.value

        self.set_system_lang(lang=lang)
        response = self.run(data).content

        state.extra_parameters["described_doc"] = response
        state.last_extra_parameter = "described_doc"

        return state
