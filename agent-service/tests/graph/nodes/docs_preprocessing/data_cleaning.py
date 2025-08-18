# tests/graph/nodes/docs_preprocessing/data_cleaning.py
from langchain_core.messages import HumanMessage

from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel
from src.registry.nodes import NODE_REGISTRY


def test_data_cleaning_vn():
    data_test = "Tôi là một học sinh ở trường trung học.!!!@@@"
    node = NODE_REGISTRY.get("docs_preprocessing.data_cleaning")()

    input_mess = HumanMessage(
        content=data_test,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="vi")

    result = node(state)["messages"][-1].content
    assert result == "học sinh trường trung học"


def test_data_cleaning_en():
    data_test = "I am a student at the high school.!!!@@@"
    node = NODE_REGISTRY.get("docs_preprocessing.data_cleaning")()

    input_mess = HumanMessage(
        content=data_test,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="en")

    result = node(state)["messages"][-1].content
    assert result == "student high school"
