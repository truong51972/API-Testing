# src.utils.preprocessing.section_preprocessing
import re
from typing import Optional

from src.utils.preprocessing.text_preprocessing import remove_extra_whitespace


def is_section_heading(line):
    """
    Check if a line is a valid section heading in a technical document.

    Section headings can be:
    - Numbered headings: e.g., "1. Title", "1.2) Subtitle", "3.1: Details", "2.1- Section"
    - Roman numeral headings: e.g., "II. Introduction", "IV) Results", "V: Discussion", "III- Analysis"
    - Uppercase headings: e.g., "KẾT LUẬN", "GIỚI THIỆU"
    """

    # Pattern for numbered section headings
    numbered_pattern = r"^\s*\d+(\.\d+)*[.\):\-]?\s+.+"
    # Pattern for Roman numeral section headings, with ) or : or - after numerals
    roman_pattern = r"^\s*[IVXLCDM]+[.\):\-]?\s+.+"
    # Pattern for uppercase headings (at least 5 letters and mostly uppercase)
    uppercase_pattern = r"^[A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠƯẠ-ỹ ]{5,}$"

    return (
        bool(re.match(numbered_pattern, line))
        or bool(re.match(roman_pattern, line))
        or bool(re.match(uppercase_pattern, line))
    )


def get_all_section_headings(text: str) -> list[str]:
    """
    Extract all section headings from the given text.

    Args:
        text (str): The input text to search for section headings.

    Returns:
        list: A list of all section headings found in the text.
    """
    lines = text.splitlines()
    return [line for line in lines if is_section_heading(line)]


def is_a_child_of(current_section: str, parent_section: str) -> bool:
    # Implement logic to determine if current_section is a child of parent_section
    curr_heading = current_section.strip().split(" ")[0]
    parent_heading = parent_section.strip().split(" ")[0]

    return curr_heading.startswith(parent_heading) and curr_heading != parent_heading


def extract_section_content(
    text: str, curr_section_heading: str, next_section_heading: Optional[str] = None
) -> str:
    """
    Extract the content of a section from the text.

    Args:
        text (str): The input text to search within.
        curr_section_heading (str): The heading of the current section.
        next_section_heading (str): The heading of the next section.

    Returns:
        str: The content of the current section.
    """

    # Check if current section heading exists in text
    if curr_section_heading not in text:
        return ""

    # Check if next section heading exists in text (if provided)
    if next_section_heading and next_section_heading in text:
        pattern = (
            rf"{re.escape(curr_section_heading)}\s*\n(.*?)"
            rf"(?=^\s*{re.escape(next_section_heading)}|\Z)"
        )
    else:
        pattern = rf"{re.escape(curr_section_heading)}\s*\n(.*)"

    match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
    if match:
        return remove_extra_whitespace(text=match.group(1), ignore_code_blocks=True)

    return ""


def create_hierarchical_section_blocks(text: str) -> list[str]:
    """
    Create hierarchical section blocks containing parent-child relationships.

    Each block contains a parent section and one of its child sections with their content.
    For example, "1. ABC" with subsections "1.1 ABC" and "1.2 ABC" will be split into
    separate blocks: ["1. ABC\n1.1 ABC\n..."] and ["1. ABC\n1.2 ABC\n..."]

    Args:
        text (str): The input text containing hierarchical sections.

    Returns:
        list[str]: List of text blocks, each containing a parent section with one child section.
    """

    section_headings = get_all_section_headings(text)

    # Clean whitespace from section headings
    section_headings = [heading.strip() for heading in section_headings]
    section_to_content = {}

    # Extract content for each section
    for i, current_heading in enumerate(section_headings):
        next_heading = (
            section_headings[i + 1] if i + 1 < len(section_headings) else None
        )
        section_to_content[current_heading.strip()] = extract_section_content(
            text, current_heading, next_heading
        )

    # Group parent sections with their child sections
    parent_child_blocks: list[list[str]] = []
    current_parent_child_group: list[str] = []

    for i, current_heading in enumerate(section_headings):
        current_parent_child_group.append(current_heading)
        # Find parent sections for current heading
        for previous_heading in section_headings[i::-1]:
            if is_a_child_of(current_heading, previous_heading):
                current_parent_child_group.append(previous_heading)

        parent_child_blocks.append(current_parent_child_group)
        current_parent_child_group = []

    # Filter blocks that have parent-child relationships (more than 1 section)
    parent_child_blocks = [block for block in parent_child_blocks if len(block) > 1]

    # Generate text blocks with parent and child content
    hierarchical_text_blocks = []

    for parent_child_group in parent_child_blocks:
        combined_block_text = ""
        # Reverse to put parent first, then child
        for section_heading in parent_child_group[::-1]:
            combined_block_text += f"{section_heading}\n"
            combined_block_text += f"{section_to_content[section_heading.strip()]}\n"
        hierarchical_text_blocks.append(combined_block_text)

    print(hierarchical_text_blocks)
    return hierarchical_text_blocks


if __name__ == "__main__":
    text = """
    1. ABC
    Content 1.
    1.1 ABC
    Content 1.1
    Content 1.1
    Content 1.1
    1.2 ABC
    Content 1.2
    Content 1.2
    Content 1.2
    2. ABC
    Content 2.
    2.1 ABC
    Content 2.1
    Content 2.1
    Content 2.1
    2.2 ABC
    Content 2.2
    Content 2.2
    Content 2.2
    """

    for block in create_hierarchical_section_blocks(text):
        print(f"{block}")
