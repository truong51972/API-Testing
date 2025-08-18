from langchain_core.messages import HumanMessage

from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel
from src.registry.nodes import NODE_REGISTRY


def test_text_correction_vn():
    data_test = "Đ â y là m ột v ăn b ả n cần được chỉnh sửa."
    node = NODE_REGISTRY.get("docs_preprocessing.text_correction")()
    input_mess = HumanMessage(
        content=data_test,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="vi")

    result = node(state)["messages"][-1].content
    assert result == "Đây là một văn bản cần được chỉnh sửa."


def test_text_correction_en():
    data_test = "This is a text that needs correction."
    node = NODE_REGISTRY.get("docs_preprocessing.text_correction")()

    input_mess = HumanMessage(
        content=data_test,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="en")

    result = node(state)["messages"][-1].content

    assert result == "This is a text that needs correction."
