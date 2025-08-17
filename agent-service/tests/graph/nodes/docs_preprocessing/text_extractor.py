from src.graph.nodes.docs_preprocessing.text_extractor import TextExtractor


def test_text_extractor_vn():
    source = "assents/test_extractor/test_vn.pdf"

    extractor = TextExtractor()
    result = extractor(type("State", (object,), {"data": source, "lang": "vi"})())

    assert "Trường" in result["messages"][0]


def test_text_extractor_en():
    source = "assents/test_extractor/test_en.pdf"

    extractor = TextExtractor()
    result = extractor(type("State", (object,), {"data": source, "lang": "en"})())

    assert "Truong" in result["messages"][0]
