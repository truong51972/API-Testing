# src.common.preprocessing.section_preprocessing
import re
from typing import Optional

from src.common.common import is_number
from src.common.preprocessing.text_preprocessing import remove_extra_whitespace


def extract_section_identifier_title(
    line,
    extra_patterns: Optional[list[str]] = None,
    heading_annotation: str = "<heading>",
) -> bool:
    """
    Extract the identifier of a section heading from a line if it matches common heading patterns.

    Supports:
    - Numbered headings (e.g., "1. Title", "1.2) Subtitle")
    - Roman numeral headings (e.g., "II. Introduction", "IV) Results")
    - Uppercase headings (e.g., "KẾT LUẬN", "GIỚI THIỆU")
    - Custom patterns via extra_patterns

    Returns:
        str or None: The extracted identifier if the line is a section heading, otherwise None.
    """

    # Remove leading '#' characters and surrounding whitespace
    removed_sharp = re.sub(r"^\s*#+\s*", "", line)

    section_identifier = None
    section_title = None

    # Pattern for numbered section headings
    numbered_pattern = rf"^\s*(\d+(\.\d+)*)[.\):\-]?\s+(.+)({heading_annotation})?"
    # Pattern for Roman numeral section headings, with ) or : or - after numerals
    roman_pattern = rf"^\s*([IVXLCDM]+)[.\):\-]?\s+(.+)({heading_annotation})?"

    if matched := re.match(numbered_pattern, removed_sharp):
        section_identifier = matched.group(1)
        section_title = matched.group(3).strip()
    elif matched := re.match(roman_pattern, removed_sharp):
        section_identifier = matched.group(1)
        section_title = matched.group(2).strip()

    elif extra_patterns:
        for pattern in extra_patterns:
            if matched := re.match(pattern, line):
                section_identifier = pattern
                break

    return section_identifier, section_title


def pattern_mining(text, min_occurrences=3) -> dict:
    pattern = r"^([#\*]*\s*)([a-zA-Z0-9]+)([-:\.)]+)\s*([a-zA-Z0-9]+)\s*([#\*]*\s*)"

    lines = text.splitlines()
    prefix_counts = {}

    for line in lines:
        m = re.match(pattern, line)
        if m:
            separator = m.group(3).replace(".", r"\.")
            prefix = (
                rf"{m.group(1)}"
                + (r"\d+" if is_number(m.group(2)) else r"\w+")
                + rf"{separator}"
            )
            code = m.group(4)
            key = prefix + (r"\d+" if is_number(code) else r"\w+")

            if r"\d+" not in key:
                continue

            prefix_counts[key] = prefix_counts.get(key, 0) + 1

    prefix_counts = dict(
        sorted(
            [item for item in prefix_counts.items() if item[1] >= min_occurrences],
            key=lambda x: x[1],
            reverse=True,
        )
    )

    return prefix_counts


def normalize_section_headings(text: str, heading_annotation: str = "<heading>") -> str:
    """
    Normalize section headings in the text by ensuring consistent formatting.

    Args:
        text (str): The input text containing section headings.
    Returns:
        str: The text with normalized section headings.
    """

    for line in text.splitlines():
        if line.strip().endswith(heading_annotation):
            continue

        section_identifier, section_title = extract_section_identifier_title(
            line=line, heading_annotation=heading_annotation
        )

        if section_identifier and section_title:
            # Normalize the heading format (e.g., "1. Title")
            normalized_heading = (
                f"{heading_annotation}{section_identifier} - {section_title}"
            )
            text = text.replace(line, normalized_heading)

    return text


def get_table_and_contents(
    text: str, heading_annotation: str = "<heading>"
) -> tuple[str, dict]:
    """
    Generate a table of contents from the identifier-to-title mapping.
    Also include the initial content before the first heading as 'Title' in toc.

    Args:
        text (str): The input text to search for section headings.
        heading_annotation (str): The annotation used to mark headings.

    Returns:
        tuple[str, dict]: A tuple containing the table of contents and a mapping of headings to their contents.
    """

    toc = ""

    first_heading_idx = text.find(heading_annotation)
    if first_heading_idx > 0:
        title_content = text[:first_heading_idx].strip()
        # Remove leading '#' characters and surrounding whitespace from title_content
        title_content = re.sub(r"^\s*#+\s*", "", title_content)
        if title_content:
            toc += title_content + "\n"

    pattern = rf"^{re.escape(heading_annotation)}\s*(.+?)\s*\n(.*?)(?=^\s*{re.escape(heading_annotation)}|\Z)"

    matches = re.findall(pattern, text, re.DOTALL | re.MULTILINE)
    heading_to_contents = {m[0]: m[1] for m in matches}

    for heading, content in heading_to_contents.items():
        toc += f"{heading}{'' if content else '<no_content>'}\n"

    return toc.strip(), heading_to_contents
