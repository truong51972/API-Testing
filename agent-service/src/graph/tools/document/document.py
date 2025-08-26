from typing import Optional, Type

from langchain.tools import BaseTool
from langchain_core.messages import ToolMessage
from pydantic import BaseModel, Field

from src.repositories.document.document_repository import DocumentRepository


class _DocumentInput(BaseModel):
    query: str = Field(description="The query text to search for")
    doc_name: Optional[str] = Field(
        default=None, description="The name of the document"
    )
    annotations: Optional[str] = Field(
        default=None, description="Annotations to filter the documents"
    )
    document_amount: Optional[int] = Field(
        default=1, description="The number of documents to return"
    )
    document_offset: Optional[int] = Field(
        default=0, description="The offset for pagination"
    )


class DocumentTool(BaseTool):
    name: str = "document_tool"
    description: str = """
    Tool for searching documents by text and other metadata.

    Args:
        query (str): The query text to search for.
        doc_name (Optional[str], optional): The name of the document. Defaults to None.
        annotations (Optional[str], optional): Annotations to filter the documents. Defaults to None.
        document_amount (Optional[int], optional): The number of documents to return. Defaults to 1.
        document_offset (Optional[int], optional): The offset for pagination. Defaults to 0.

    Returns:
        List[ToolMessage]: A list of documents matching the search criteria.
    """
    args_schema: Type[BaseModel] = _DocumentInput

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__repository = DocumentRepository()

    def _run(
        self,
        query: str,
        document_amount: int = 1,
        document_offset: int = 0,
        doc_name: str = None,
        annotations: str = None,
    ):
        result = self.__repository.search_by_text(
            query=query,
            doc_name=doc_name,
            annotations=annotations,
            document_amount=document_amount,
            document_offset=document_offset,
        )[0]
        return [
            ToolMessage(
                content=result,
                tool_call_id="<TOOL_CALL_ID>",
            )
        ]
