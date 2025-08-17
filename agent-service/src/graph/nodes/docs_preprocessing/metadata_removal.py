# src.graph.nodes.docs_preprocessing.metadata_removal
import logging
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import model_validator

from src.base.service.base_agent_service import BaseAgentService

prompt_vn = None
with open(
    "src/graph/nodes/docs_preprocessing/prompts/metadata_removal_vn.txt", "r"
) as f:
    prompt_vn = f.read()

prompt_en = None
with open(
    "src/graph/nodes/docs_preprocessing/prompts/metadata_removal_en.txt", "r"
) as f:
    prompt_en = f.read()


class MetaDataRemoval(BaseAgentService):
    llm_model: str = "gemini-2.0-flash"
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

        if lang == "vi":
            self.system_prompt = prompt_vn
        else:
            self.system_prompt = prompt_en

        result_text = ""
        chunks = self.__text_splitter.split_text(data)

        batchs = [
            {
                "input": chunk,
                "chat_history": [],
            }
            for chunk in chunks[: self.batch_size]
        ]
        responses = self.runs(batchs, batch_size=self.batch_size)

        result_text += "\n".join([response.content for response in responses]) + "\n"

        logging.info("MetaDataRemoval node called")

        return {
            "result": [result_text],
        }


if __name__ == "__main__":
    load_dotenv()
    meta_data_removal = MetaDataRemoval()

    string = """
    Tác giả: Nguyễn Văn A
    Ngày tạo: 15/08/2025
    Email: nguyenvana@example.com
    Số điện thoại: 0912 345 678
    Nhóm: Nghiên cứu AI

    Báo cáo kết quả tuần
    Tuần này, nhóm đã hoàn thành việc kiểm thử hệ thống AI cho dự án mới.
    Các vấn đề phát sinh đã được ghi nhận và xử lý kịp thời.
    Kế hoạch tuần tới là tối ưu hóa thuật toán và cập nhật tài liệu hướng dẫn sử dụng.
    """
    state = type("State", (object,), {"data": string, "lang": "vi"})()

    response = meta_data_removal(state)

    print(response["result"][0])
