# src.graph.nodes.docs_preprocessing.data_cleaning
from typing import Any, Dict

from pydantic import validate_call

from src.common.preprocessing import section_preprocessing, text_preprocessing
from src.models import DocsPreProcessingStateModel


class DocumentNormalizationNode:
    @validate_call
    def __call__(self, state: DocsPreProcessingStateModel) -> Dict[str, Any]:
        data = state.extra_parameters[state.last_extra_parameter]

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

        state.extra_parameters["normalized_text"] = cleaned_data
        state.last_extra_parameter = "normalized_text"

        return state
