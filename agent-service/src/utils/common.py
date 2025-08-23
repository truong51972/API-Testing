import hashlib
import re

from pydantic import (
    Field,
    validate_call,
)


def split_by_size(input_list, chunk_size):
    """Split list into chunks of specified size."""
    if chunk_size <= 0:
        return [input_list]
    return [
        input_list[i : i + chunk_size] for i in range(0, len(input_list), chunk_size)
    ]


def merge_chunks(chunks):
    """Merge list of chunks into a single list."""
    return [item for sublist in chunks for item in sublist]


@validate_call
def create_unique_id(text: str = Field(min_length=1)) -> int:
    """Create a unique id with text as a seed"""
    # assert len(text) < 1000, "text must not be too long"

    # create a unique id for the product
    hash_bytes = hashlib.md5(text.encode()).digest()
    int_64bit = int.from_bytes(hash_bytes[:8], "big", signed=True)  # Dạng signed
    return int_64bit


def get_percent_space(text):
    total = len(text)
    spaces = text.count(" ")
    return spaces / total * 100 if total > 0 else 0


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


def get_all_section_headings(text):
    """
    Extract all section headings from the given text.

    Args:
        text (str): The input text to search for section headings.

    Returns:
        list: A list of all section headings found in the text.
    """
    lines = text.splitlines()
    return [line for line in lines if is_section_heading(line)]
