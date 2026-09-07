"""Finite inputs and absolute accounting comparisons.

Accounting tolerances measure asset quantities, independently of the normalized
market-clearing tolerance and the display-only threshold for numerical dust.
"""

from math import isfinite

ACCOUNTING_TOLERANCE = 1e-8


def require_finite(label: str, *values: float) -> None:
    if any(not isfinite(value) for value in values):
        raise ValueError(f"{label} must be finite")


def balances_match(a: float, b: float, *, tolerance: float = ACCOUNTING_TOLERANCE) -> bool:
    return isfinite(a) and isfinite(b) and abs(a - b) <= tolerance


def assert_close(a: float, b: float, *, tolerance: float = ACCOUNTING_TOLERANCE) -> None:
    if not balances_match(a, b, tolerance=tolerance):
        raise AssertionError(f"accounting mismatch: {a} != {b}")
