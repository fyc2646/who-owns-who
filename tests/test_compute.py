"""Tests for settlement computation."""

import pytest
from decimal import Decimal

from tripsettle.compute import compute_minimal_transfers, compute_net_balances, compute_settlement_summary
from tripsettle.models import Event, Person, SplitStrategy


class TestNetBalances:
    """Tests for net balance computation."""

    def test_simple_two_person_settlement(self):
        """Test simple two-person settlement."""
        event = Event(name="Trip")
        alice = event.add_person("Alice")
        bob = event.add_person("Bob")
        event.add_activity(
            description="Dinner",
            amount=Decimal("100"),
            payer=alice,
            participants=[alice, bob],
        )
        balances = compute_net_balances(event)
        # Alice paid 100, owes 50, net = +50
        # Bob paid 0, owes 50, net = -50
        assert balances[alice] == Decimal("50.00")
        assert balances[bob] == Decimal("-50.00")
        # Sum should be zero
        assert sum(balances.values()) == Decimal("0.00")

    def test_example_scenario(self):
        """Test the example scenario from requirements."""
        event = Event(name="Ski Trip")
        alice = event.add_person("Alice")
        bob = event.add_person("Bob")
        carol = event.add_person("Carol")

        # Dinner: $150, payer=Alice, participants=[A,B,C], EQUAL
        event.add_activity(
            description="Dinner",
            amount=Decimal("150"),
            payer=alice,
            participants=[alice, bob, carol],
            split_strategy="EQUAL",
        )

        # Gas: $60, payer=Bob, participants=[A,B], EQUAL
        event.add_activity(
            description="Gas",
            amount=Decimal("60"),
            payer=bob,
            participants=[alice, bob],
            split_strategy="EQUAL",
        )

        # Museum: $90, payer=Carol, participants=[B,C], WEIGHTED, weights={B:2, C:1}
        event.add_activity(
            description="Museum",
            amount=Decimal("90"),
            payer=carol,
            participants=[bob, carol],
            split_strategy="WEIGHTED",
            weights={bob: Decimal("2"), carol: Decimal("1")},
        )

        balances = compute_net_balances(event)

        # Alice: paid 150, owed 50 (dinner) + 30 (gas) = 80, net = +70
        # Bob: paid 60, owed 50 (dinner) + 30 (gas) + 60 (museum) = 140, net = -80
        # Carol: paid 90, owed 50 (dinner) + 30 (museum) = 80, net = +10

        # Allow for rounding
        assert abs(balances[alice] - Decimal("70.00")) < Decimal("0.01")
        assert abs(balances[bob] - Decimal("-80.00")) < Decimal("0.01")
        assert abs(balances[carol] - Decimal("10.00")) < Decimal("0.01")

        # Sum should be zero
        assert abs(sum(balances.values())) < Decimal("0.01")

    def test_multi_payer_activity(self):
        """Test activity with multiple payers."""
        event = Event(name="Trip")
        alice = event.add_person("Alice")
        bob = event.add_person("Bob")
        event.add_activity(
            description="Dinner",
            amount=Decimal("100"),
            payer=[(alice, Decimal("60")), (bob, Decimal("40"))],
            participants=[alice, bob],
        )
        balances = compute_net_balances(event)
        # Alice paid 60, owes 50, net = +10
        # Bob paid 40, owes 50, net = -10
        assert abs(balances[alice] - Decimal("10.00")) < Decimal("0.01")
        assert abs(balances[bob] - Decimal("-10.00")) < Decimal("0.01")
        assert abs(sum(balances.values())) < Decimal("0.01")


class TestMinimalTransfers:
    """Tests for minimal transfer computation."""

    def test_simple_transfer(self):
        """Test simple two-person transfer."""
        alice = Person(name="Alice")
        bob = Person(name="Bob")
        balances = {alice: Decimal("50.00"), bob: Decimal("-50.00")}
        transfers = compute_minimal_transfers(balances)
        assert len(transfers) == 1
        assert transfers[0].from_person == bob
        assert transfers[0].to_person == alice
        assert transfers[0].amount == Decimal("50.00")

    def test_example_scenario_transfers(self):
        """Test transfers for example scenario."""
        event = Event(name="Ski Trip")
        alice = event.add_person("Alice")
        bob = event.add_person("Bob")
        carol = event.add_person("Carol")

        event.add_activity(
            description="Dinner",
            amount=Decimal("150"),
            payer=alice,
            participants=[alice, bob, carol],
            split_strategy="EQUAL",
        )
        event.add_activity(
            description="Gas",
            amount=Decimal("60"),
            payer=bob,
            participants=[alice, bob],
            split_strategy="EQUAL",
        )
        event.add_activity(
            description="Museum",
            amount=Decimal("90"),
            payer=carol,
            participants=[bob, carol],
            split_strategy="WEIGHTED",
            weights={bob: Decimal("2"), carol: Decimal("1")},
        )

        balances = compute_net_balances(event)
        transfers = compute_minimal_transfers(balances)

        # Should have minimal transfers (likely 2: Bob->Alice, Bob->Carol)
        assert len(transfers) >= 1
        assert len(transfers) <= 2

        # Verify all transfers are valid
        for transfer in transfers:
            assert transfer.amount > 0
            assert transfer.from_person != transfer.to_person

        # Verify balances are cleared
        working_balances = balances.copy()
        for transfer in transfers:
            working_balances[transfer.from_person] += transfer.amount
            working_balances[transfer.to_person] -= transfer.amount

        for balance in working_balances.values():
            assert abs(balance) < Decimal("0.01")

    def test_three_person_rounding(self):
        """Test that rounding is handled correctly with three people."""
        event = Event(name="Trip")
        alice = event.add_person("Alice")
        bob = event.add_person("Bob")
        carol = event.add_person("Carol")

        # Use amount that doesn't divide evenly
        event.add_activity(
            description="Dinner",
            amount=Decimal("100"),
            payer=alice,
            participants=[alice, bob, carol],
        )

        balances = compute_net_balances(event)
        # Sum should be zero within tolerance (allow up to 0.02 for rounding accumulation)
        # Note: after ensure_zero_sum, the sum should be exactly 0 or very close
        assert abs(sum(balances.values())) <= Decimal("0.02")

        transfers = compute_minimal_transfers(balances)
        # Should be able to clear all balances
        working_balances = balances.copy()
        for transfer in transfers:
            working_balances[transfer.from_person] += transfer.amount
            working_balances[transfer.to_person] -= transfer.amount

        for balance in working_balances.values():
            assert abs(balance) <= Decimal("0.02")  # Allow slightly larger tolerance for rounding


class TestSettlementSummary:
    """Tests for settlement summary computation."""

    def test_summary(self):
        """Test settlement summary computation."""
        event = Event(name="Trip")
        alice = event.add_person("Alice")
        bob = event.add_person("Bob")
        event.add_activity(
            description="Dinner",
            amount=Decimal("100"),
            payer=alice,
            participants=[alice, bob],
        )

        balances = compute_net_balances(event)
        summary = compute_settlement_summary(event, balances)

        assert alice in summary
        assert bob in summary
        assert "paid" in summary[alice]
        assert "owed" in summary[alice]
        assert "net" in summary[alice]

        # Alice paid 100, owed 50
        assert summary[alice]["paid"] == Decimal("100.00")
        assert summary[alice]["owed"] == Decimal("50.00")
        assert summary[alice]["net"] == Decimal("50.00")

        # Bob paid 0, owed 50
        assert summary[bob]["paid"] == Decimal("0.00")
        assert summary[bob]["owed"] == Decimal("50.00")
        assert summary[bob]["net"] == Decimal("-50.00")

