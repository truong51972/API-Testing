# src.graph.nodes.docs_preprocessing.text_extractor
from docling.datamodel.accelerator_options import (
    AcceleratorDevice,
    AcceleratorOptions,
)
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, InputFormat, PdfFormatOption
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, model_validator, validate_call

from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel
from src.registry.nodes import register_node


@register_node("docs_preprocessing.text_extractor")
class TextExtractor(BaseModel):
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

        return self

    @validate_call
    def __call__(self, state: DocsPreProcessingStateModel):
        data = state.messages[-1].content.strip()

        conversion_result = self.__converter.convert(data)
        doc = conversion_result.document

        text = doc.export_to_text()
        return {
            "messages": [AIMessage(content=text)],
        }


if __name__ == "__main__":
    # source = "http://localhost:9000/mybucket/mac-lenin.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=minioadmin%2F20250817%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20250817T070349Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=ee175d0a9cd36f6f27e28c900af54ee3061b5045ead25fa4215365d3fdc47a0e"
    source = "https://www.octoparse.com/use-cases/e-commerce"
    dest = "data/uploads/mac-lenin.txt"

    input_mess = HumanMessage(
        content=source,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="vi")
    extractor = TextExtractor()
    result = extractor(state)
    print("Extracted text:", result["data"][-1])

    with open(dest, "w", encoding="utf-8") as f:
        f.write(result["data"][-1].content)
