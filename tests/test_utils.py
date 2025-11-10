"""Tests for utility functions."""

import pytest
from decimal import Decimal

from tripsettle.errors import RoundingError, ValidationError
from tripsettle.models import Person
from tripsettle.utils import distribute_remainder, ensure_zero_sum, round_money, validate_amount


class TestRoundMoney:
    """Tests for money rounding."""

    def test_round_to_two_decimals(self):
        """Test rounding to two decimal places."""
        assert round_money(Decimal("10.555")) == Decimal("10.56")
        assert round_money(Decimal("10.545")) == Decimal("10.54")  # Banker's rounding
        assert round_money(Decimal("10.5")) == Decimal("10.50")

    def test_bankers_rounding(self):
        """Test banker's rounding (round half to even)."""
        # 0.5 rounds to 0 (even)
        assert round_money(Decimal("0.5")) == Decimal("0.50")
        # 1.5 rounds to 2 (even)
        assert round_money(Decimal("1.5")) == Decimal("1.50")
        # 2.5 rounds to 2 (even)
        assert round_money(Decimal("2.5")) == Decimal("2.50")


class TestValidateAmount:
    """Tests for amount validation."""

    def test_positive_amount(self):
        """Test that positive amount passes validation."""
        validate_amount(Decimal("10.00"))

    def test_zero_amount(self):
        """Test that zero amount passes validation."""
        validate_amount(Decimal("0"))

    def test_negative_amount_raises(self):
        """Test that negative amount raises ValidationError."""
        with pytest.raises(ValidationError, match="must be non-negative"):
            validate_amount(Decimal("-10"))


class TestDistributeRemainder:
    """Tests for remainder distribution."""

    def test_distribute_small_remainder(self):
        """Test distributing a small remainder."""
        alice = Person(name="Alice")
        bob = Person(name="Bob")
        balances = {alice: Decimal("50.00"), bob: Decimal("-50.01")}
        remainder = Decimal("0.01")
        adjusted = distribute_remainder(balances, remainder)
        # One person should get +0.01
        assert sum(adjusted.values()) == Decimal("0.00")

    def test_remainder_exceeds_tolerance_raises(self):
        """Test that remainder exceeding tolerance raises RoundingError."""
        alice = Person(name="Alice")
        balances = {alice: Decimal("50.00")}
        remainder = Decimal("1.00")
        with pytest.raises(RoundingError, match="exceeds tolerance"):
            distribute_remainder(balances, remainder, tolerance=Decimal("0.01"))


class TestEnsureZeroSum:
    """Tests for ensuring zero sum."""

    def test_already_zero_sum(self):
        """Test that already zero-sum balances are unchanged."""
        alice = Person(name="Alice")
        bob = Person(name="Bob")
        balances = {alice: Decimal("50.00"), bob: Decimal("-50.00")}
        adjusted = ensure_zero_sum(balances)
        assert sum(adjusted.values()) == Decimal("0.00")

    def test_small_remainder_distributed(self):
        """Test that small remainder is distributed."""
        alice = Person(name="Alice")
        bob = Person(name="Bob")
        carol = Person(name="Carol")
        balances = {alice: Decimal("33.33"), bob: Decimal("-33.33"), carol: Decimal("0.01")}
        adjusted = ensure_zero_sum(balances, tolerance=Decimal("0.02"))
        # After distribution, sum should be zero within tolerance
        assert abs(sum(adjusted.values())) <= Decimal("0.02")

    def test_large_remainder_raises(self):
        """Test that large remainder raises RoundingError."""
        alice = Person(name="Alice")
        bob = Person(name="Bob")
        balances = {alice: Decimal("50.00"), bob: Decimal("-40.00")}
        with pytest.raises(RoundingError, match="exceeds tolerance"):
            ensure_zero_sum(balances)

