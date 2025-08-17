from src.utils.common import merge_chunks, split_by_size


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
