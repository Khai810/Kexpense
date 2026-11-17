"""Unit & property-based tests for ADR-010 allocation service (TC-02-23)."""

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.app.services.allocation import allocate


def test_allocate_empty_list():
    """Edge case: empty list returns empty list."""
    assert allocate(100000, []) == []
    assert allocate(0, []) == []


def test_allocate_single_item():
    """Edge case: single item receives the entire total."""
    assert allocate(50000, [45000]) == [50000]
    assert allocate(12345, [0]) == [12345]


def test_allocate_all_zeros():
    """Edge case: all line totals are zero -> divides evenly."""
    assert allocate(100, [0, 0, 0, 0]) == [25, 25, 25, 25]
    # Remainder distributed to first items
    assert allocate(10, [0, 0, 0]) == [4, 3, 3]


def test_allocate_total_smaller_than_item_count():
    """Edge case: total is smaller than number of items."""
    result = allocate(2, [1000, 1000, 1000, 1000])
    assert result == [1, 1, 0, 0]
    assert sum(result) == 2


def test_allocate_tax_and_discount_discrepancy():
    """Real world test: receipt items with 10% VAT and discount where printed total differs by ~12%."""
    # Line totals: 3 items (35k, 45k, 20k) -> base = 100k
    # Printed total after 10% VAT and 5k service fee = 115k
    line_totals = [35000, 45000, 20000]
    total = 115000
    allocated = allocate(total, line_totals)
    assert len(allocated) == 3
    assert sum(allocated) == total
    # Check proportions: 35k * 1.15 = 40250, 45k * 1.15 = 51750, 20k * 1.15 = 23000
    assert allocated == [40250, 51750, 23000]


@given(
    total=st.integers(min_value=0, max_value=10_000_000_000),
    line_totals=st.lists(st.integers(min_value=0, max_value=1_000_000_000), min_size=1, max_size=100),
)
@settings(max_examples=200)
def test_allocate_hypothesis_properties(total: int, line_totals: list[int]):
    """TC-02-23: Property-based testing with Hypothesis.

    Invariants:
      1. sum(result) == total
      2. all(x >= 0 for x in result)
      3. len(result) == len(line_totals)
    """
    result = allocate(total, line_totals)

    assert len(result) == len(line_totals)
    assert sum(result) == total
    assert all(x >= 0 for x in result)
