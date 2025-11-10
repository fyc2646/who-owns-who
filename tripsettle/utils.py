"""Utility functions for money handling and rounding."""

from decimal import Decimal, ROUND_HALF_EVEN
from typing import TYPE_CHECKING, Dict

from tripsettle.errors import RoundingError

if TYPE_CHECKING:
    from tripsettle.models import Person


def round_money(amount: Decimal, places: int = 2) -> Decimal:
    """
    Round a monetary amount using banker's rounding (round half to even).

    Parameters
    ----------
    amount : Decimal
        The amount to round.
    places : int, default=2
        Number of decimal places.

    Returns
    -------
    Decimal
        Rounded amount.
    """
    quantizer = Decimal(10) ** -places
    return amount.quantize(quantizer, rounding=ROUND_HALF_EVEN)


def distribute_remainder(
    balances: "Dict[Person, Decimal]", remainder: Decimal, tolerance: Decimal = Decimal("0.01")
) -> "Dict[Person, Decimal]":
    """
    Distribute a rounding remainder across balances using least-absolute-balance-first.

    Parameters
    ----------
    balances : Dict[Person, Decimal]
        Current balances for each person.
    remainder : Decimal
        The remainder to distribute (should be within tolerance).
    tolerance : Decimal, default=Decimal("0.01")
        Tolerance for rounding errors.

    Returns
    -------
    Dict[Person, Decimal]
        Updated balances with remainder distributed.

    Raises
    ------
    RoundingError
        If remainder exceeds tolerance.
    """
    from tripsettle.models import Person  # noqa: F811

    if abs(remainder) > tolerance:
        raise RoundingError(f"Remainder {remainder} exceeds tolerance {tolerance}")

    if remainder == 0:
        return balances.copy()

    # Sort by absolute balance (ascending), then by person name for determinism
    sorted_people = sorted(
        balances.keys(),
        key=lambda p: (abs(balances[p]), p.name, p.id),
    )

    adjusted = balances.copy()
    remainder_remaining = remainder

    # Distribute remainder in increments of 0.01
    increment = Decimal("0.01") if remainder > 0 else Decimal("-0.01")

    for person in sorted_people:
        if remainder_remaining == 0:
            break
        adjusted[person] += increment
        remainder_remaining -= increment

    return adjusted


def validate_amount(amount: Decimal, name: str = "amount") -> None:
    """
    Validate that an amount is non-negative.

    Parameters
    ----------
    amount : Decimal
        The amount to validate.
    name : str, default="amount"
        Name of the amount for error messages.

    Raises
    ------
    ValidationError
        If amount is negative.
    """
    from tripsettle.errors import ValidationError

    if amount < 0:
        raise ValidationError(f"{name} must be non-negative, got {amount}")


def ensure_zero_sum(balances: "Dict[Person, Decimal]", tolerance: Decimal = Decimal("0.01")) -> "Dict[Person, Decimal]":
    """
    Ensure balances sum to zero by distributing any remainder.

    Parameters
    ----------
    balances : Dict[Person, Decimal]
        Current balances.
    tolerance : Decimal, default=Decimal("0.01")
        Tolerance for rounding errors.

    Returns
    -------
    Dict[Person, Decimal]
        Adjusted balances that sum to zero within tolerance.
    """
    from tripsettle.models import Person  # noqa: F811

    total = sum(balances.values())
    if abs(total) <= tolerance:
        if total != 0:
            # Distribute the small remainder
            return distribute_remainder(balances, total, tolerance)
        return balances.copy()

    raise RoundingError(f"Balances sum to {total}, which exceeds tolerance {tolerance}")

