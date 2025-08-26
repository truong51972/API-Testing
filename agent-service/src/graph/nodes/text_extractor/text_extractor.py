# src.graph.nodes.text_extractor.text_extractor
import logging

from docling.datamodel.accelerator_options import (
    AcceleratorDevice,
    AcceleratorOptions,
)
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, InputFormat, PdfFormatOption
from langchain_core.messages import AIMessage, HumanMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import model_validator, validate_call

from src import cache
from src.base.service.base_agent_service import BaseAgentService
from src.enums.enums import LanguageEnum
from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel
from src.utils.common import get_percent_space


class TextExtractorNode(BaseAgentService):
    llm_model: str = "gemma-3-27b-it"
    llm_temperature: float = 0.0
    llm_top_p: float = 0.1
    llm_top_k: int = 3

    chunk_size: int = 1500
    batch_size: int = 5

    path_to_prompt: dict[LanguageEnum, str] = {
        LanguageEnum.VI: "src/graph/nodes/text_extractor/prompts/fix_orc_split_text_vi.txt",
        LanguageEnum.EN: "src/graph/nodes/text_extractor/prompts/fix_orc_split_text_en.txt",
    }

    @model_validator(mode="after")
    def __after_init__(self):
        accelerator_options = AcceleratorOptions(
            num_threads=8, device=AcceleratorDevice.CUDA
        )

        pipeline_options = PdfPipelineOptions()
        pipeline_options.accelerator_options = accelerator_options
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True

        self.__converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                )
            }
        )

        self.__text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=0,
            length_function=len,
        )

        return self

    def __fix_orc_split_text(self, text, lang):
        self.set_system_prompt(lang=lang)

        corrected_text = ""

        chunks = self.__text_splitter.split_text(text)

        batches = [
            {
                "input": chunk,
                "chat_history": [],
            }
            for chunk in chunks
        ]
        responses = self.runs_parallel(batches, batch_size=self.batch_size)

        corrected_text += "\n".join(responses)

        return corrected_text

    @cache.cache_func_wrapper
    def __extract(self, data):
        conversion_result = self.__converter.convert(data)
        doc = conversion_result.document

        text = doc.export_to_text()

        return text, doc.name

    @validate_call
    def __call__(self, state: DocsPreProcessingStateModel):
        data = state.messages[-1].content.strip()
        lang = state.lang.value

        text, doc_name = self.__extract(data)

        if get_percent_space(text) >= 35:
            logging.warning(
                "High whitespace percentage detected! Applying text correction."
            )
            text = self.__fix_orc_split_text(text, lang)

        return {"messages": [AIMessage(content=text)], "doc_name": doc_name}


if __name__ == "__main__":
    # source = "http://localhost:9000/mybucket/mac-lenin.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=minioadmin%2F20250817%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20250817T070349Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=ee175d0a9cd36f6f27e28c900af54ee3061b5045ead25fa4215365d3fdc47a0e"
    source = "https://www.octoparse.com/use-cases/e-commerce"
    dest = "data/uploads/mac-lenin.txt"

    input_mess = HumanMessage(
        content=source,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="vi")
    extractor = TextExtractorNode()
    result = extractor(state)
    print("Extracted text:", result["data"][-1])

    with open(dest, "w", encoding="utf-8") as f:
        f.write(result["data"][-1].content)
