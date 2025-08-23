# src.graph.nodes.docs_preprocessing.section_based_chunking
import logging
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import model_validator, validate_call

from src.base.service.base_agent_service import BaseAgentService
from src.enums.enums import LanguageEnum
from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel
from src.registry.nodes import register_node
from src.utils.common import get_all_section_headings

prompts = {}

with open(
    "src/graph/nodes/docs_preprocessing/prompts/section_based_chunking_vn.txt", "r"
) as f:
    prompts[LanguageEnum.VI] = f.read()

with open(
    "src/graph/nodes/docs_preprocessing/prompts/section_based_chunking_en.txt", "r"
) as f:
    prompts[LanguageEnum.EN] = f.read()


@register_node("docs_preprocessing.section_based_chunking")
class SectionBasedChunking(BaseAgentService):
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

    @validate_call
    def __call__(self, state: DocsPreProcessingStateModel) -> Dict[str, Any]:
        data = state.messages[-1].content
        self.load_system_prompt(prompts[state.lang])

        all_section_headings = get_all_section_headings(data)

        return_data = AIMessage(content=all_section_headings)

        return {
            "messages": [return_data],
        }


if __name__ == "__main__":
    load_dotenv()
    section_based_chunking = SectionBasedChunking()

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

    response = section_based_chunking(state)

    print(response["data"][0])
