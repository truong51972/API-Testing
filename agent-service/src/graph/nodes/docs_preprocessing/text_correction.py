# src.graph.nodes.docs_preprocessing.text_correction
import logging
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import model_validator

from src.base.service.base_agent_service import BaseAgentService

prompt_vn = None
with open(
    "src/graph/nodes/docs_preprocessing/prompts/text_correction_vn.txt", "r"
) as f:
    prompt_vn = f.read()

prompt_en = None
with open(
    "src/graph/nodes/docs_preprocessing/prompts/text_correction_en.txt", "r"
) as f:
    prompt_en = f.read()


class TextCorrection(BaseAgentService):
    llm_model: str = "gemma-3-27b-it"
    llm_temperature: float = 0.0
    llm_top_p: float = 0.1
    llm_top_k: int = 3

    chunk_size: int = 1000
    batch_size: int = 10

    @model_validator(mode="after")
    def __after_init__(self):
        self.__text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=0,
            length_function=len,
        )
        return self

    def __call__(self, state) -> Dict[str, Any]:
        data = state.data
        lang = state.lang

        corrected_text = ""

        if lang == "vi":
            self.system_prompt = prompt_vn
        else:
            self.system_prompt = prompt_en

        chunks = self.__text_splitter.split_text(data)

        batchs = [
            {
                "input": chunk,
                "chat_history": [],
            }
            for chunk in chunks[: self.batch_size]
        ]
        responses = self.runs(batchs, batch_size=self.batch_size)

        corrected_text += "\n".join(responses)

        logging.info("TextCorrection node called")

        return {
            "result": [corrected_text],
        }


if __name__ == "__main__":
    load_dotenv()
    text_correction = TextCorrection()

    source = "data/uploads/mac-lenin.txt"
    dest = "data/uploads/mac-lenin_corrected.txt"

    with open(source, "r") as f:
        string = f.read()

    state = type("State", (object,), {"data": string, "lang": "vi"})()

    response = text_correction(state)

    print(response["result"][0])

    with open(dest, "w") as f:
        f.write(response["result"][0])
