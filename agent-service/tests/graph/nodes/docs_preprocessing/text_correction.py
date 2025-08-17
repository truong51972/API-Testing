from src.graph.nodes.docs_preprocessing.text_correction import TextCorrection


def test_text_correction_vn():
    text_correction = TextCorrection()
    state = type(
        "State",
        (object,),
        {"data": "Đ â y là m ột v ăn b ả n cần được chỉnh sửa.", "lang": "vi"},
    )()
    response = text_correction(state)
    assert response["result"][0] == "Đây là một văn bản cần được chỉnh sửa."


def test_text_correction_en():
    text_correction = TextCorrection()
    state = type(
        "State",
        (object,),
        {"data": "T his is a t ext th at ne eds cor rec tion.", "lang": "en"},
    )()
    response = text_correction(state)
    assert response["result"][0] == "This is a text that needs correction."
