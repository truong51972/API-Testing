# tests.utils.common
from src.utils.common import (
    get_percent_space,
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
