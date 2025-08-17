# src.graph.nodes.docs_preprocessing.text_correction
import logging
import re
from typing import Any, Dict

from dotenv import load_dotenv

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

    max_len_per_request: int = 1500
    num_of_batch: int = 10

    def __call__(self, state) -> Dict[str, Any]:
        data = state.data
        lang = state.lang

        corrected_text = ""

        if lang == "vi":
            self.system_prompt = prompt_vn
        else:
            self.system_prompt = prompt_en

        text = ""
        batch = []

        lines = data.split("\n")
        for i, line in enumerate(lines):
            if ((len(text) + len(line)) > self.max_len_per_request) or (
                i == len(lines) - 1
            ):
                invoke_input = {
                    "input": text,
                    "chat_history": [],
                }

                if len(batch) < self.num_of_batch:
                    batch.append(invoke_input)
                else:
                    responses = self.run_in_batch(batch)
                    corrected_text += "\n".join(responses) + "\n"
                    batch = []

                text = ""

            else:
                text += line + "\n"

        logging.info("TextCorrection node called")

        return {
            "messages": [corrected_text],
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

    print(response["messages"][0])

    with open(dest, "w") as f:
        f.write(response["messages"][0])
