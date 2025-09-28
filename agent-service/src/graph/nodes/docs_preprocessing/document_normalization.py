# src.graph.nodes.docs_preprocessing.data_cleaning
from typing import Any, Dict

from langchain_core.messages import AIMessage
from pydantic import validate_call

from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel
from src.utils.preprocessing import section_preprocessing, text_preprocessing


class DocumentNormalizationNode:
    @validate_call
    def __call__(self, state: DocsPreProcessingStateModel) -> Dict[str, Any]:
        data = state.messages[-1].content

        cleaned_data = text_preprocessing.normalize_unicode(data)
        # cleaned_data = text_preprocessing.lowercase_text(cleaned_data)
        cleaned_data = text_preprocessing.remove_extra_whitespace(
            cleaned_data, ignore_code_blocks=True
        )
        cleaned_data = text_preprocessing.remove_repeated_punctuation(
            cleaned_data, ignore_code_blocks=True
        )
        cleaned_data = text_preprocessing.extract_link_text(cleaned_data)
        cleaned_data = text_preprocessing.remove_extra_newlines(
            cleaned_data, ignore_code_blocks=True
        )

        cleaned_data = section_preprocessing.normalize_section_headings(cleaned_data)

        return_data = AIMessage(content=cleaned_data)

        return {
            "messages": [return_data],
        }
