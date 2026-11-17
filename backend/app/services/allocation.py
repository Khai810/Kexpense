"""ADR-010: Allocation service for line items using the largest-remainder method."""


def allocate(total: int, line_totals: list[int]) -> list[int]:
    """Allocate `total` amount across line items proportionally to `line_totals`.

    Uses the largest-remainder method (Hamilton/Hare-Niemeyer method) on integer VND.
    Guarantees:
      1. sum(result) == total strictly for all valid inputs.
      2. all(x >= 0 for x in result).
      3. Stable ordering matching line_totals.
      4. Handles zero-base edge cases by uniform integer division.
    """
    if total < 0:
        raise ValueError("Total amount cannot be negative")

    for lt in line_totals:
        if lt < 0:
            raise ValueError("Line totals cannot contain negative values")

    n = len(line_totals)
    if n == 0:
        return []

    base = sum(line_totals)
    if base == 0:
        # Uniform distribution when line totals are all zero
        q, r = divmod(total, n)
        return [q + (1 if i < r else 0) for i in range(n)]

    # Largest remainder method
    floors = [total * lt // base for lt in line_totals]
    rema = [total * lt % base for lt in line_totals]
    left = total - sum(floors)

    # Distribute the leftover units to items with largest remainder
    for i in sorted(range(n), key=lambda idx: (-rema[idx], idx))[:left]:
        floors[i] += 1

    return floors
