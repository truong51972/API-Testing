import hashlib

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
