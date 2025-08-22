from langchain_core.messages import HumanMessage

from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel
from src.registry.nodes import NODE_REGISTRY


def test_text_normalization_vn():
    data_test = "Học là sinh trường trung học!"
    node = NODE_REGISTRY.get("docs_preprocessing.text_normalization")()

    input_mess = HumanMessage(
        content=data_test,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="vi")

    result = node(state)["messages"][-1].content
    assert result == "học là sinh trường trung học!"


def test_text_normalization_en():
    data_test = "I Am a student at the high school!"
    node = NODE_REGISTRY.get("docs_preprocessing.text_normalization")()

    input_mess = HumanMessage(
        content=data_test,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="en")

    result = node(state)["messages"][-1].content
    assert result == "i am a student at the high school!"
