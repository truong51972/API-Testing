from typing import List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)
from pymilvus import DataType

from src.utils.common import create_unique_id


class DocumentModel(BaseModel):
    """Document model"""

    id: str = Field(
        default=None,
        description="document ID, must be unique.",
        json_schema_extra={
            "milvus_config": {
                "dtype": DataType.VARCHAR,
                "is_primary": True,
                "auto_id": False,
            },
        },
    )

    doc_id: str = Field(
        description="document external ID, must be unique.",
        max_length=64,
        json_schema_extra={
            "milvus_config": {
                "dtype": DataType.VARCHAR,
                "max_length": 64,  # Milvus VARCHAR max_length
            }
        },
    )

    selected: bool = Field(
        default=False,
        description="whether the document is selected or not.",
        json_schema_extra={
            "milvus_config": {
                "dtype": DataType.BOOL,
            }
        },
    )

    doc_name: str = Field(
        min_length=3,
        max_length=512,
        description="document name",
        json_schema_extra={
            "milvus_config": {
                "dtype": DataType.VARCHAR,
                "max_length": 512,  # Milvus VARCHAR max_length
            }
        },
    )

    annotations: str = Field(
        min_length=3,
        description="document annotations, must be at least 3 characters long.",
        json_schema_extra={
            "milvus_config": {
                "dtype": DataType.VARCHAR,
                "max_length": 512,  # Milvus VARCHAR max_length
            }
        },
    )

    collection: str = Field(
        min_length=3,
        description="document collection, must be at least 3 characters long.",
        json_schema_extra={
            "milvus_config": {
                "dtype": DataType.VARCHAR,
                "max_length": 512,  # Milvus VARCHAR max_length
            }
        },
    )

    vector: Optional[List[float]] = Field(
        default_factory=list,
        description="embedding vector for the document, must be a list of floats.",
        json_schema_extra={
            "milvus_config": {
                "dtype": DataType.FLOAT_VECTOR
                # 'dim' will be dynamically added from the 'embedding_dim' parameter
            }
        },
    )

    text: Optional[str] = Field(
        default_factory=str,
        description="text for context, used for displaying document information.",
        json_schema_extra={
            "milvus_config": {
                "dtype": DataType.VARCHAR,
                "max_length": 16384,  # Milvus VARCHAR max_length
            }
        },
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "doc_name": "Document Name",
                "annotations": "Document Annotations",
                "vector": [0.1, 0.2, 0.3],
                "text": "Document Text",
            }
        }
    )

    # after init, if id not exists, create a new id from defined seed
    @model_validator(mode="after")
    def check_id(self):
        if self.id is None:
            # create a new id from defined seed
            seed = self.annotations + self.doc_name + self.text
            if seed:
                self.id = create_unique_id(seed)
            else:
                raise ValueError(
                    "ID must be provided or text must be provided to create a new ID"
                )
        return self
