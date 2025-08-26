# src.graph.nodes.docs_preprocessing.data_cleaning
import logging
from typing import Any, Dict

from langchain_core.messages import AIMessage
from nltk.corpus import stopwords as nltk_stopwords
from pydantic import validate_call

from src.enums.enums import LanguageEnum
from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel
from src.utils.preprocessing.text_preprocessing import (
    remove_stopwords,
)


class StopWordRemovalNode:
    @validate_call
    def __call__(self, state: DocsPreProcessingStateModel) -> Dict[str, Any]:
        data = state.messages[-1].content
        lang = state.lang

        stopwords = []

        if lang == LanguageEnum.VI:
            file_path = "assents/stopwords/vietnamese-stopwords.txt"
            with open(file_path, "r", encoding="utf-8") as f:
                stopwords.extend(f.read().splitlines())
        elif lang == LanguageEnum.EN:
            stopwords.extend(nltk_stopwords.words("english"))

        cleaned_data = remove_stopwords(data, stopwords)

        return_data = AIMessage(content=cleaned_data)

        return {
            "messages": [return_data],
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    state = type(
        "State",
        (object,),
        {"data": "Tôi    là một học sinh ở trường trung học.!!!@@@", "lang": "vi"},
    )()
    data_cleaning = StopWordRemovalNode()
    result = data_cleaning(state)
    logger.info(
        f"Data cleaning result: {result=={'cleaned_data': ['học sinh trường trung học']}}"
    )
