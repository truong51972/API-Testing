from langchain_core.messages import HumanMessage

from src.models.agent.docs_preprocessing_state_model import DocsPreProcessingStateModel
from src.registry.nodes import NODE_REGISTRY


def test_text_extractor_pdf_vn():
    data_test = "assents/test_extractor/test_vn.pdf"
    node = NODE_REGISTRY.get("docs_preprocessing.text_extractor")()
    input_mess = HumanMessage(
        content=data_test,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="vi")

    result = node(state)["messages"][-1].content
    assert "Trường" in result


def test_text_extractor_pdf_en():
    data_test = "assents/test_extractor/test_en.pdf"
    node = NODE_REGISTRY.get("docs_preprocessing.text_extractor")()
    input_mess = HumanMessage(
        content=data_test,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="en")

    result = node(state)["messages"][-1].content

    assert "Truong" in result


def test_text_extractor_via_link():
    source = "https://www.octoparse.com/use-cases/e-commerce"
    extractor = NODE_REGISTRY.get("docs_preprocessing.text_extractor")()
    input_mess = HumanMessage(
        content=source,
    )
    state = DocsPreProcessingStateModel(user_input="", messages=[input_mess], lang="vi")

    result = extractor(state)["messages"][-1].content

    assert "Web Scraping for E-commerce" in result
