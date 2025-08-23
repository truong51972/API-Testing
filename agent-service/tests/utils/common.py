# tests.utils.common
from src.utils.common import (
    get_all_section_headings,
    get_percent_space,
    is_section_heading,
    merge_chunks,
    split_by_size,
)


def test_split_by_size():
    assert split_by_size([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert split_by_size([1, 2, 3, 4, 5], 3) == [[1, 2, 3], [4, 5]]
    assert split_by_size([1, 2, 3, 4, 5], 1) == [[1], [2], [3], [4], [5]]
    assert split_by_size([], 2) == []


def test_merge_chunks():
    assert merge_chunks([[1, 2], [3, 4], [5]]) == [1, 2, 3, 4, 5]
    assert merge_chunks([[1, 2, 3], [4, 5]]) == [1, 2, 3, 4, 5]
    assert merge_chunks([[1], [2], [3], [4], [5]]) == [1, 2, 3, 4, 5]
    assert merge_chunks([]) == []


def test_get_percent_space():
    assert get_percent_space("This is a test.") <= 35
    assert get_percent_space("t h i s i s a s p l i t t e x t") >= 35


def test_is_section_heading():
    # Numbered section headings
    assert is_section_heading("1. This is a valid section header")
    assert is_section_heading("2.1: Another valid section header")
    assert is_section_heading("2.1 Another valid section header")
    assert is_section_heading("2.1) Another valid section header")
    assert is_section_heading("2.1 ) Another valid section header")
    assert is_section_heading("    2.1: Another valid section header")
    assert is_section_heading("    2 Another valid section header")

    # Roman numeral section headings
    assert is_section_heading("II. Introduction")
    assert is_section_heading("III) Results")
    assert is_section_heading("IV: Discussion")
    assert is_section_heading("V- Analysis")
    assert is_section_heading("    IX. Appendix")

    # Uppercase headings
    assert is_section_heading("KẾT LUẬN")
    assert is_section_heading("GIỚI THIỆU")
    assert is_section_heading("PHÂN TÍCH")
    assert is_section_heading("RESULTS")
    assert is_section_heading("CONCLUSION")

    # Negative cases (not section headings)
    assert not is_section_heading("This is not a valid section header")
    assert not is_section_heading("Section 2.1 Another invalid section header")
    assert not is_section_heading("This should not match")
    assert not is_section_heading("section header but not valid")


def test_get_all_section_headings():
    text = """
    1. Introduction
    Content
    2.1 Background
    Content
    Content
    Content
    II. Related Work
    Content
    III) Methodology
    Content
    Content
    KẾT LUẬN
    Content
    Content
    Content
    """
    expected = [
        "1. Introduction",
        "2.1 Background",
        "II. Related Work",
        "III) Methodology",
        "KẾT LUẬN",
    ]

    all_section_headings = get_all_section_headings(text)

    for i, expected_heading in enumerate(expected):
        assert expected_heading in all_section_headings[i]
