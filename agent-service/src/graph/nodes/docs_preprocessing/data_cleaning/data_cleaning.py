# src.graph.nodes.data_cleanning.data_cleanning
import logging
from typing import Any, Dict

from nltk.corpus import stopwords as nltk_stopwords

from src.utils.text_preprocessing import (
    lowercase_text,
    normalize_unicode,
    remove_extra_whitespace,
    remove_punctuation,
    remove_stopwords,
)


class DataCleaning:
    def __call__(self, state) -> Dict[str, Any]:
        data = state.data
        lang = state.lang

        stopwords = []

        if lang == "vi":
            file_path = "src/resources/vietnamese-stopwords.txt"
            with open(file_path, "r", encoding="utf-8") as f:
                stopwords.extend(f.read().splitlines())
        elif lang == "en":
            stopwords.extend(nltk_stopwords.words("english"))

        cleaned_data = normalize_unicode(data)
        cleaned_data = lowercase_text(cleaned_data)
        cleaned_data = remove_extra_whitespace(cleaned_data)
        cleaned_data = remove_punctuation(cleaned_data)
        cleaned_data = remove_stopwords(cleaned_data, stopwords)

        return {
            "cleaned_data": [cleaned_data],
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    state = type(
        "State",
        (object,),
        {"data": "Tôi    là một học sinh ở trường trung học.!!!@@@", "lang": "vi"},
    )()
    data_cleaning = DataCleaning()
    result = data_cleaning(state)
    logger.info(
        f"Data cleaning result: {result=={'cleaned_data': ['học sinh trường trung học']}}"
    )
