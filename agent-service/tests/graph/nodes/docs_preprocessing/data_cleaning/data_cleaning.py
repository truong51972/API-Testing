from src.graph.nodes.docs_preprocessing.data_cleaning.data_cleaning import DataCleaning


def test_data_cleaning_vn():
    state = type(
        "State",
        (object,),
        {"data": "Tôi là một học sinh ở trường trung học.!!!@@@", "lang": "vi"},
    )()
    data_cleaning = DataCleaning()
    result = data_cleaning(state)
    assert result == {"cleaned_data": ["học sinh trường trung học"]}


def test_data_cleaning_en():
    state = type(
        "State",
        (object,),
        {"data": "I am a student at the high school.!!!@@@", "lang": "en"},
    )()
    data_cleaning = DataCleaning()
    result = data_cleaning(state)
    assert result == {"cleaned_data": ["student high school"]}
