# src.graph.nodes.docs_preprocessing.data_cleaning
from typing import Any, Dict

from langchain_core.messages import AIMessage
from pydantic import validate_call

from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel
from src.utils.preprocessing.text_preprocessing import (
    extract_link_text,
    lowercase_text,
    normalize_unicode,
    remove_extra_newlines,
    remove_extra_whitespace,
    remove_repeated_punctuation,
)


class TextNormalizationNode:
    @validate_call
    def __call__(self, state: DocsPreProcessingStateModel) -> Dict[str, Any]:
        data = state.messages[-1].content

        cleaned_data = normalize_unicode(data)
        cleaned_data = lowercase_text(cleaned_data)
        cleaned_data = remove_extra_whitespace(cleaned_data, ignore_code_blocks=True)
        cleaned_data = remove_repeated_punctuation(
            cleaned_data, ignore_code_blocks=True
        )
        cleaned_data = extract_link_text(cleaned_data)
        cleaned_data = remove_extra_newlines(cleaned_data, ignore_code_blocks=True)

        return_data = AIMessage(content=cleaned_data)

        return {
            "messages": [return_data],
        }
