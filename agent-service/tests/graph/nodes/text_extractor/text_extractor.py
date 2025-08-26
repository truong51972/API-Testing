from langchain_core.messages import HumanMessage

from src.graph import nodes
from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel


def test_text_extractor_pdf_vn():
    data_test = "assents/test_extractor/test_vn.pdf"
    node = nodes.TextExtractorNode()
    input_mess = HumanMessage(
        content=data_test,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="vi")

    result = node(state)["messages"][-1].content
    assert "Trường" in result


def test_text_extractor_pdf_en():
    data_test = "assents/test_extractor/test_en.pdf"
    node = nodes.TextExtractorNode()
    input_mess = HumanMessage(
        content=data_test,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="en")

    result = node(state)["messages"][-1].content

    assert "Truong" in result


def test_text_extractor_via_link():
    source = "https://www.octoparse.com/use-cases/e-commerce"
    node = nodes.TextExtractorNode()
    input_mess = HumanMessage(
        content=source,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="vi")

    result = node(state)["messages"][-1].content

    assert "Web Scraping for E-commerce" in result


def test_text_extractor_with_split_text():
    data_test = "assents/test_extractor/test_split_text.pdf"
    node = nodes.TextExtractorNode()
    input_mess = HumanMessage(
        content=data_test,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="vi")

    result = node(state)["messages"][-1].content
    assert result == "this is a split text"
