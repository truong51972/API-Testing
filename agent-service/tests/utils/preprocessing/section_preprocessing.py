# tests.utils.preprocessing.section_preprocessing
from src.utils.preprocessing.section_preprocessing import (
    create_hierarchical_section_blocks,
    extract_section_content,
    get_all_section_headings,
    is_a_child_of,
    is_section_heading,
)


def test_is_section_heading():
    # Numbered section headings
    assert is_section_heading("1. This is a valid section header")
    assert is_section_heading("2.1: Another valid section header")
    assert is_section_heading("2.1 Another valid section header")
    assert is_section_heading("2.1) Another valid section header")
    assert is_section_heading("2.1 ) Another valid section header")
    assert is_section_heading("    2.1: Another valid section header")
    assert is_section_heading("    2 Another valid section header")
    assert is_section_heading("# 3.4 safety and security requirements")

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


def test_is_a_child_of():
    assert is_a_child_of(current_section="1.1 ABC", parent_section="1. ABC")
    assert not is_a_child_of(current_section="1.1 ABC", parent_section="2. ABC")


def test_extract_section_content():
    text = """
    1. Introduction
    Content Introduction line 1
    Content Introduction line 2
    2.1 Background
    Content Background line 1
    Content Background line 2
    Content Background line 3
    2.2 History
    Content History line 1
    Content History line 2
    II. Related Work
    Content Related Work line 1
    Content Related Work line 2
    III) Methodology
    Content Methodology line 1
    Content Methodology line 2
    3.1 Data Collection
    Content Data Collection
    3.2 Analysis
    Content Analysis
    KẾT LUẬN
    Content Conclusion line 1
    Content Conclusion line 2
    Content Conclusion line 3
    """

    # Test basic section extraction with next section
    intro_content = extract_section_content(text, "1. Introduction", "2.1 Background")
    assert "Content Introduction line 1" in intro_content
    assert "Content Introduction line 2" in intro_content
    assert "Content Background" not in intro_content

    # Test section extraction with multiple content lines
    background_content = extract_section_content(text, "2.1 Background", "2.2 History")
    assert "Content Background line 1" in background_content
    assert "Content Background line 2" in background_content
    assert "Content Background line 3" in background_content
    assert "Content History" not in background_content
    assert "Content Introduction" not in background_content

    # Test Roman numeral sections
    related_work_content = extract_section_content(
        text, "II. Related Work", "III) Methodology"
    )
    assert "Content Related Work line 1" in related_work_content
    assert "Content Related Work line 2" in related_work_content
    assert "Content Methodology" not in related_work_content

    # Test section extraction without next section (last section)
    conclusion_content = extract_section_content(text, "KẾT LUẬN")
    assert "Content Conclusion line 1" in conclusion_content
    assert "Content Conclusion line 2" in conclusion_content
    assert "Content Conclusion line 3" in conclusion_content
    assert "Content Analysis" not in conclusion_content

    # Test subsection extraction
    data_collection_content = extract_section_content(
        text, "3.1 Data Collection", "3.2 Analysis"
    )
    assert "Content Data Collection" in data_collection_content
    assert "Content Analysis" not in data_collection_content

    # Test edge case: section not found
    empty_content = extract_section_content(text, "4. Non-existent Section")
    assert empty_content.strip() == "" or empty_content is None

    # Test edge case: next section not found
    last_analysis_content = extract_section_content(
        text, "3.2 Analysis", "4. Non-existent"
    )
    assert "Content Analysis" in last_analysis_content
    assert "KẾT LUẬN" in last_analysis_content

    # Test case sensitivity and exact matching
    methodology_content = extract_section_content(
        text, "III) Methodology", "3.1 Data Collection"
    )
    assert "Content Methodology line 1" in methodology_content
    assert "Content Methodology line 2" in methodology_content
    assert "Content Data Collection" not in methodology_content


def test_create_hierarchical_section_blocks():
    text = """
    1. ABC
    Content 1. ABC
    1.1 DEF
    Content 1.1 DEF
    Content 1.1 DEF line 2
    1.2 GHI
    Content 1.2 GHI
    Content 1.2 GHI line 2
    2. XYZ
    Content 2. XYZ
    2.1 UVW
    Content 2.1 UVW
    Content 2.1 UVW line 2
    2.2 RST
    Content 2.2 RST
    Content 2.2 RST line 2
    """

    blocks = create_hierarchical_section_blocks(text)

    # Should have 4 blocks: 1.1, 1.2, 2.1, 2.2 each with their parent
    assert len(blocks) == 4

    # Test first block (1. ABC -> 1.1 DEF)
    first_block = blocks[0]
    assert "1. ABC" in first_block
    assert "1.1 DEF" in first_block
    assert "Content 1. ABC" in first_block
    assert "Content 1.1 DEF" in first_block
    assert "Content 1.1 DEF line 2" in first_block
    # Should not contain other subsections
    assert "1.2 GHI" not in first_block
    assert "Content 1.2 GHI" not in first_block

    # Test second block (1. ABC -> 1.2 GHI)
    second_block = blocks[1]
    assert "1. ABC" in second_block
    assert "1.2 GHI" in second_block
    assert "Content 1. ABC" in second_block
    assert "Content 1.2 GHI" in second_block
    assert "Content 1.2 GHI line 2" in second_block
    # Should not contain other subsections
    assert "1.1 DEF" not in second_block
    assert "Content 1.1 DEF" not in second_block

    # Test third block (2. XYZ -> 2.1 UVW)
    third_block = blocks[2]
    assert "2. XYZ" in third_block
    assert "2.1 UVW" in third_block
    assert "Content 2. XYZ" in third_block
    assert "Content 2.1 UVW" in third_block
    assert "Content 2.1 UVW line 2" in third_block
    # Should not contain section 1 content or other section 2 subsections
    assert "1. ABC" not in third_block
    assert "2.2 RST" not in third_block

    # Test fourth block (2. XYZ -> 2.2 RST)
    fourth_block = blocks[3]
    assert "2. XYZ" in fourth_block
    assert "2.2 RST" in fourth_block
    assert "Content 2. XYZ" in fourth_block
    assert "Content 2.2 RST" in fourth_block
    assert "Content 2.2 RST line 2" in fourth_block
    # Should not contain other subsections
    assert "2.1 UVW" not in fourth_block
    assert "Content 2.1 UVW" not in fourth_block
