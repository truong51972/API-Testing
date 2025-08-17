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
