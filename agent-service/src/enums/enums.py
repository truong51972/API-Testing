from enum import Enum


class ModelTypeEnum(str, Enum):
    llm = "llm"
    embedding = "embedding"


class LanguageEnum(str, Enum):
    VI = "vi"
    EN = "en"
