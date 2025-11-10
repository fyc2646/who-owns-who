"""Tests for split strategies."""

import pytest
from decimal import Decimal

from tripsettle.errors import StrategyError
from tripsettle.models import Activity, Person, SplitStrategy
from tripsettle.strategies import compute_all_shares, compute_equal_share, compute_fixed_share, compute_weighted_share


class TestEqualShare:
    """Tests for equal share computation."""

    def test_equal_share_two_people(self):
        """Test equal split between two people."""
        alice = Person(name="Alice")
        bob = Person(name="Bob")
        activity = Activity(
            description="Dinner",
            amount=Decimal("100"),
            payer=alice,
            participants=[alice, bob],
            split_strategy=SplitStrategy.EQUAL,
        )
        alice_share = compute_equal_share(activity, alice)
        bob_share = compute_equal_share(activity, bob)
        assert alice_share == Decimal("50.00")
        assert bob_share == Decimal("50.00")

    def test_equal_share_three_people(self):
        """Test equal split between three people."""
        alice = Person(name="Alice")
        bob = Person(name="Bob")
        carol = Person(name="Carol")
        activity = Activity(
            description="Dinner",
            amount=Decimal("150"),
            payer=alice,
            participants=[alice, bob, carol],
            split_strategy=SplitStrategy.EQUAL,
        )
        shares = compute_all_shares(activity)
        assert shares[alice] == Decimal("50.00")
        assert shares[bob] == Decimal("50.00")
        assert shares[carol] == Decimal("50.00")

    def test_equal_share_not_participant_raises(self):
        """Test that computing share for non-participant raises StrategyError."""
        alice = Person(name="Alice")
        bob = Person(name="Bob")
        carol = Person(name="Carol")
        activity = Activity(
            description="Dinner",
            amount=Decimal("100"),
            payer=alice,
            participants=[alice, bob],
            split_strategy=SplitStrategy.EQUAL,
        )
        with pytest.raises(StrategyError, match="not in activity"):
            compute_equal_share(activity, carol)


class TestWeightedShare:
    """Tests for weighted share computation."""

    def test_weighted_share(self):
        """Test weighted split."""
        bob = Person(name="Bob")
        carol = Person(name="Carol")
        activity = Activity(
            description="Museum",
            amount=Decimal("90"),
            payer=bob,
            participants=[bob, carol],
            split_strategy=SplitStrategy.WEIGHTED,
            weights={bob: Decimal("2"), carol: Decimal("1")},
        )
        bob_share = compute_weighted_share(activity, bob)
        carol_share = compute_weighted_share(activity, carol)
        # Bob should pay 2/3, Carol 1/3
        assert bob_share == Decimal("60.00")
        assert carol_share == Decimal("30.00")

    def test_weighted_share_missing_weights_raises(self):
        """Test that missing weights raises ValidationError at creation time."""
        from tripsettle.errors import ValidationError

        bob = Person(name="Bob")
        with pytest.raises(ValidationError, match="requires weights"):
            Activity(
                description="Museum",
                amount=Decimal("90"),
                payer=bob,
                participants=[bob],
                split_strategy=SplitStrategy.WEIGHTED,
                weights=None,
            )

    def test_weighted_share_not_in_weights_raises(self):
        """Test that participant not in weights raises StrategyError."""
        bob = Person(name="Bob")
        carol = Person(name="Carol")
        activity = Activity(
            description="Museum",
            amount=Decimal("90"),
            payer=bob,
            participants=[bob, carol],
            split_strategy=SplitStrategy.WEIGHTED,
            weights={bob: Decimal("1")},  # Carol missing
        )
        with pytest.raises(StrategyError, match="not found in weights"):
            compute_weighted_share(activity, carol)


class TestFixedShare:
    """Tests for fixed share computation."""

    def test_fixed_share(self):
        """Test fixed shares split."""
        alice = Person(name="Alice")
        bob = Person(name="Bob")
        activity = Activity(
            description="Dinner",
            amount=Decimal("100"),
            payer=alice,
            participants=[alice, bob],
            split_strategy=SplitStrategy.FIXED_SHARES,
            shares={alice: Decimal("60"), bob: Decimal("40")},
        )
        alice_share = compute_fixed_share(activity, alice)
        bob_share = compute_fixed_share(activity, bob)
        assert alice_share == Decimal("60.00")
        assert bob_share == Decimal("40.00")

    def test_fixed_share_missing_shares_raises(self):
        """Test that missing shares raises ValidationError at creation time."""
        from tripsettle.errors import ValidationError

        alice = Person(name="Alice")
        with pytest.raises(ValidationError, match="requires shares"):
            Activity(
                description="Dinner",
                amount=Decimal("100"),
                payer=alice,
                participants=[alice],
                split_strategy=SplitStrategy.FIXED_SHARES,
                shares=None,
            )

    def test_fixed_share_not_in_shares_raises(self):
        """Test that participant not in shares raises StrategyError."""
        alice = Person(name="Alice")
        bob = Person(name="Bob")
        activity = Activity(
            description="Dinner",
            amount=Decimal("100"),
            payer=alice,
            participants=[alice, bob],
            split_strategy=SplitStrategy.FIXED_SHARES,
            shares={alice: Decimal("100")},  # Bob missing
        )
        with pytest.raises(StrategyError, match="not found in shares"):
            compute_fixed_share(activity, bob)

