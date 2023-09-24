from tabulous._range import RectRange
import pytest

@pytest.mark.parametrize(
    "a, b",
    [
        ((2, 2), (slice(0, 6), slice(0, 5))),
        ((0, 2), (slice(0, 1), slice(0, 3))),
        ((9, 3), (slice(5, None), slice(None, 5))),
        ((6, 6), (slice(None), slice(5, 7))),
        ((6, 6), (slice(5, 7), slice(None))),
    ]
)
def test_contains(a, b):
    assert a in RectRange(*b)

@pytest.mark.parametrize(
    "a, b",
    [
        ((1, 1), (slice(2, 6), slice(1, 5))),
        ((3, 7), (slice(2, 6), slice(1, 5))),
        ((4, 2), (slice(5, None), slice(None, 5))),
        ((6, 7), (slice(None), slice(5, 7))),
        ((7, 6), (slice(5, 7), slice(None))),
    ]
)
def test_does_not_contain(a, b):
    assert a not in RectRange(*b)

@pytest.mark.parametrize(
    "a, b",
    [
        ((slice(3, 5), slice(2, 4)), (slice(0, 6), slice(0, 5))),
        ((slice(6, 8), slice(3, 4)), (slice(5, None), slice(None, 5))),
        ((slice(1, 9), slice(5, 7)), (slice(None), slice(5, 7))),
        ((slice(5, 7), slice(1, 9)), (slice(5, 7), slice(None))),
    ]
)
def test_includes(a, b):
    assert RectRange(*b).includes(RectRange(*a))

@pytest.mark.parametrize(
    "a, b",
    [
        ((slice(3, 7), slice(2, 4)), (slice(0, 6), slice(0, 5))),
        ((slice(4, 7), slice(3, 4)), (slice(5, None), slice(None, 5))),
        ((slice(1, 9), slice(5, 8)), (slice(None), slice(5, 7))),
        ((slice(4, 7), slice(1, 9)), (slice(5, 7), slice(None))),
    ]
)
def test_does_not_include(a, b):
    assert not RectRange(*b).includes(RectRange(*a))

@pytest.mark.parametrize(
    "a, b",
    [
        ((slice(3, 7), slice(2, 4)), (slice(0, 6), slice(0, 5))),
        ((slice(4, 7), slice(3, 4)), (slice(5, None), slice(None, 5))),
        ((slice(1, 3), slice(3, 6)), (slice(None), slice(5, 7))),
        ((slice(4, 6), slice(1, 9)), (slice(5, 7), slice(None))),
    ]
)
def test_overlaps_with(a, b):
    assert RectRange(*b).overlaps_with(RectRange(*a))

@pytest.mark.parametrize(
    "a, b",
    [
        ((slice(1, 3), slice(2, 4)), (slice(3, 6), slice(0, 5))),
        ((slice(2, 4), slice(3, 9)), (slice(5, None), slice(None, 5))),
        ((slice(3, 8), slice(8, 9)), (slice(None), slice(5, 7))),
        ((slice(2, 5), slice(1, 9)), (slice(5, 7), slice(None))),
    ]
)
def test_does_not_overlap_with(a, b):
    assert not RectRange(*b).overlaps_with(RectRange(*a))
