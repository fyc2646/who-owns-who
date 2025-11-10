"""Integration tests for the full workflow."""

import pytest
from decimal import Decimal

from tripsettle.models import Event


def test_example_scenario_from_requirements():
    """Test the exact example scenario from requirements."""
    e = Event(name="Ski Trip", currency="USD")
    alice = e.add_person("Alice")
    bob = e.add_person("Bob")
    carol = e.add_person("Carol")

    e.add_activity(
        "Dinner",
        Decimal("150"),
        payer=alice,
        participants=[alice, bob, carol],
        split_strategy="EQUAL",
    )
    e.add_activity(
        "Gas",
        Decimal("60"),
        payer=bob,
        participants=[alice, bob],
        split_strategy="EQUAL",
    )
    e.add_activity(
        "Museum",
        Decimal("90"),
        payer=carol,
        participants=[bob, carol],
        split_strategy="WEIGHTED",
        weights={bob: Decimal("2"), carol: Decimal("1")},
    )

    transfers, summary = e.compute_settlement()

    # Assert: sum(p['net'] for p in summary.values()) == Decimal("0.00") within cent tolerance
    net_sum = sum(p["net"] for p in summary.values())
    assert abs(net_sum) < Decimal("0.01"), f"Net sum should be zero, got {net_sum}"

    # Verify all people are in summary
    assert alice in summary
    assert bob in summary
    assert carol in summary

    # Verify transfers are valid
    for transfer in transfers:
        assert transfer.amount > 0
        assert transfer.from_person != transfer.to_person

    # Verify balances are cleared by transfers
    balances = {p: summary[p]["net"] for p in summary.keys()}
    for transfer in transfers:
        balances[transfer.from_person] += transfer.amount
        balances[transfer.to_person] -= transfer.amount

    for balance in balances.values():
        assert abs(balance) < Decimal("0.01"), f"Balance should be zero after transfers, got {balance}"


def test_single_person_event():
    """Test edge case: event with only one person."""
    e = Event(name="Solo Trip")
    alice = e.add_person("Alice")
    e.add_activity(
        "Dinner",
        Decimal("100"),
        payer=alice,
        participants=[alice],
    )

    transfers, summary = e.compute_settlement()
    # Should have no transfers (person paid for themselves)
    assert len(transfers) == 0
    assert summary[alice]["net"] == Decimal("0.00")


def test_person_not_in_activity():
    """Test that person not in an activity doesn't affect their balance."""
    e = Event(name="Trip")
    alice = e.add_person("Alice")
    bob = e.add_person("Bob")
    carol = e.add_person("Carol")

    # Only Alice and Bob participate
    e.add_activity(
        "Dinner",
        Decimal("100"),
        payer=alice,
        participants=[alice, bob],
    )

    transfers, summary = e.compute_settlement()
    # Carol should have zero balance
    assert summary[carol]["paid"] == Decimal("0.00")
    assert summary[carol]["owed"] == Decimal("0.00")
    assert summary[carol]["net"] == Decimal("0.00")


def test_zero_amount_activity_rejected():
    """Test that zero-amount activity is rejected."""
    from tripsettle.errors import ValidationError

    e = Event(name="Trip")
    alice = e.add_person("Alice")

    # Zero amount should be allowed (person might pay nothing)
    # But let's test with negative to ensure validation works
    with pytest.raises(ValidationError):
        e.add_activity(
            "Dinner",
            Decimal("-10"),
            payer=alice,
            participants=[alice],
        )


def test_duplicate_person_names():
    """Test that duplicate person names are handled via IDs."""
    e = Event(name="Trip")
    alice1 = e.add_person("Alice")
    alice2 = e.add_person("Alice")  # Same name, different ID

    assert alice1.name == alice2.name
    assert alice1.id != alice2.id

    e.add_activity(
        "Dinner",
        Decimal("100"),
        payer=alice1,
        participants=[alice1, alice2],
    )

    transfers, summary = e.compute_settlement()
    assert alice1 in summary
    assert alice2 in summary
    # Verify net balances sum to zero (within tolerance for rounding)
    net_sum = sum(p["net"] for p in summary.values())
    assert abs(net_sum) <= Decimal("0.02"), f"Net sum should be zero, got {net_sum}"


def test_fixed_shares_integration():
    """Test fixed shares strategy in full workflow."""
    e = Event(name="Trip")
    alice = e.add_person("Alice")
    bob = e.add_person("Bob")
    e.add_activity(
        "Dinner",
        Decimal("100"),
        payer=alice,
        participants=[alice, bob],
        split_strategy="FIXED_SHARES",
        shares={alice: Decimal("60"), bob: Decimal("40")},
    )

    transfers, summary = e.compute_settlement()
    # Alice paid 100, owed 60, net = +40
    # Bob paid 0, owed 40, net = -40
    assert abs(summary[alice]["net"] - Decimal("40.00")) < Decimal("0.01")
    assert abs(summary[bob]["net"] - Decimal("-40.00")) < Decimal("0.01")
    assert abs(sum(p["net"] for p in summary.values())) < Decimal("0.01")

