# tests/graph/nodes/docs_preprocessing/data_cleaning.py
from langchain_core.messages import HumanMessage

from src.graph import nodes
from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel


def test_stopword_removal_vn():
    data_test = "học là sinh trường trung học"
    node = nodes.StopWordRemovalNode()

    input_mess = HumanMessage(
        content=data_test,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="vi")

    result = node(state)["messages"][-1].content
    assert result == "học sinh trường trung học"


def test_stopword_removal_en():
    data_test = "I am a student at the high school"
    node = nodes.StopWordRemovalNode()

    input_mess = HumanMessage(
        content=data_test,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="en")

    result = node(state)["messages"][-1].content
    assert result == "I student high school"
