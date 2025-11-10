"""Tests for models module."""

import pytest
from decimal import Decimal
from uuid import uuid4

from tripsettle.errors import ValidationError
from tripsettle.models import Activity, Event, Person, SettlementTransfer, SplitStrategy


class TestPerson:
    """Tests for Person model."""

    def test_create_person(self):
        """Test creating a person."""
        person = Person(name="Alice")
        assert person.name == "Alice"
        assert isinstance(person.id, type(uuid4()))

    def test_person_empty_name_raises(self):
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError, match="name cannot be empty"):
            Person(name="")

    def test_person_whitespace_name_raises(self):
        """Test that whitespace-only name raises ValidationError."""
        with pytest.raises(ValidationError, match="name cannot be empty"):
            Person(name="   ")

    def test_person_serialization(self):
        """Test person serialization."""
        person = Person(name="Alice")
        data = person.to_dict()
        assert data["name"] == "Alice"
        assert "id" in data

        restored = Person.from_dict(data)
        assert restored.name == person.name
        assert restored.id == person.id


class TestActivity:
    """Tests for Activity model."""

    def test_create_equal_split_activity(self):
        """Test creating an activity with equal split."""
        alice = Person(name="Alice")
        bob = Person(name="Bob")
        activity = Activity(
            description="Dinner",
            amount=Decimal("100"),
            payer=alice,
            participants=[alice, bob],
            split_strategy=SplitStrategy.EQUAL,
        )
        assert activity.description == "Dinner"
        assert activity.amount == Decimal("100")
        assert activity.payer == alice
        assert len(activity.participants) == 2

    def test_activity_negative_amount_raises(self):
        """Test that negative amount raises ValidationError."""
        alice = Person(name="Alice")
        with pytest.raises(ValidationError, match="must be non-negative"):
            Activity(
                description="Dinner",
                amount=Decimal("-10"),
                payer=alice,
                participants=[alice],
            )

    def test_activity_empty_description_raises(self):
        """Test that empty description raises ValidationError."""
        alice = Person(name="Alice")
        with pytest.raises(ValidationError, match="description cannot be empty"):
            Activity(
                description="",
                amount=Decimal("100"),
                payer=alice,
                participants=[alice],
            )

    def test_activity_no_participants_raises(self):
        """Test that no participants raises ValidationError."""
        alice = Person(name="Alice")
        with pytest.raises(ValidationError, match="at least one participant"):
            Activity(
                description="Dinner",
                amount=Decimal("100"),
                payer=alice,
                participants=[],
            )

    def test_activity_no_payer_raises(self):
        """Test that no payer raises ValidationError."""
        alice = Person(name="Alice")
        with pytest.raises(ValidationError, match="at least one payer"):
            Activity(
                description="Dinner",
                amount=Decimal("100"),
                payer=[],
                participants=[alice],
            )

    def test_activity_weighted_strategy(self):
        """Test creating activity with weighted split."""
        alice = Person(name="Alice")
        bob = Person(name="Bob")
        activity = Activity(
            description="Museum",
            amount=Decimal("90"),
            payer=alice,
            participants=[alice, bob],
            split_strategy=SplitStrategy.WEIGHTED,
            weights={alice: Decimal("0.5"), bob: Decimal("0.5")},
        )
        assert activity.weights is not None
        assert activity.weights[alice] == Decimal("0.5")

    def test_activity_weighted_missing_weights_raises(self):
        """Test that weighted strategy without weights raises ValidationError."""
        alice = Person(name="Alice")
        with pytest.raises(ValidationError, match="requires weights"):
            Activity(
                description="Museum",
                amount=Decimal("90"),
                payer=alice,
                participants=[alice],
                split_strategy=SplitStrategy.WEIGHTED,
            )

    def test_activity_weighted_renormalization(self):
        """Test that weights are re-normalized if they don't sum to 1.0."""
        alice = Person(name="Alice")
        bob = Person(name="Bob")
        activity = Activity(
            description="Museum",
            amount=Decimal("90"),
            payer=alice,
            participants=[alice, bob],
            split_strategy=SplitStrategy.WEIGHTED,
            weights={alice: Decimal("2"), bob: Decimal("2")},  # Sums to 4, should normalize to 0.5 each
        )
        # Weights should be normalized
        assert abs(activity.weights[alice] - Decimal("0.5")) < Decimal("0.01")
        assert abs(activity.weights[bob] - Decimal("0.5")) < Decimal("0.01")

    def test_activity_fixed_shares(self):
        """Test creating activity with fixed shares."""
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
        assert activity.shares is not None
        assert activity.shares[alice] == Decimal("60")

    def test_activity_fixed_shares_mismatch_raises(self):
        """Test that fixed shares that don't sum to amount raises ValidationError."""
        alice = Person(name="Alice")
        bob = Person(name="Bob")
        with pytest.raises(ValidationError, match="sum to"):
            Activity(
                description="Dinner",
                amount=Decimal("100"),
                payer=alice,
                participants=[alice, bob],
                split_strategy=SplitStrategy.FIXED_SHARES,
                shares={alice: Decimal("60"), bob: Decimal("50")},  # Sums to 110
            )

    def test_activity_multi_payer(self):
        """Test creating activity with multiple payers."""
        alice = Person(name="Alice")
        bob = Person(name="Bob")
        activity = Activity(
            description="Dinner",
            amount=Decimal("100"),
            payer=[(alice, Decimal("60")), (bob, Decimal("40"))],
            participants=[alice, bob],
        )
        payers = activity.get_payers()
        assert len(payers) == 2
        assert payers[0][1] == Decimal("60")
        assert payers[1][1] == Decimal("40")

    def test_activity_multi_payer_mismatch_raises(self):
        """Test that multi-payer amounts must sum to activity amount."""
        alice = Person(name="Alice")
        bob = Person(name="Bob")
        with pytest.raises(ValidationError, match="sum to"):
            Activity(
                description="Dinner",
                amount=Decimal("100"),
                payer=[(alice, Decimal("60")), (bob, Decimal("50"))],  # Sums to 110
                participants=[alice, bob],
            )


class TestEvent:
    """Tests for Event model."""

    def test_create_event(self):
        """Test creating an event."""
        event = Event(name="Ski Trip")
        assert event.name == "Ski Trip"
        assert event.currency == "USD"

    def test_add_person(self):
        """Test adding a person to an event."""
        event = Event(name="Trip")
        alice = event.add_person("Alice")
        assert alice.name == "Alice"
        assert alice in event.people

    def test_add_activity(self):
        """Test adding an activity to an event."""
        event = Event(name="Trip")
        alice = event.add_person("Alice")
        bob = event.add_person("Bob")
        activity = event.add_activity(
            description="Dinner",
            amount=Decimal("100"),
            payer=alice,
            participants=[alice, bob],
        )
        assert activity in event.activities

    def test_add_activity_payer_not_in_event_raises(self):
        """Test that adding activity with payer not in event raises ValidationError."""
        event = Event(name="Trip")
        alice = event.add_person("Alice")
        bob = Person(name="Bob")  # Not added to event
        with pytest.raises(ValidationError, match="not in the event"):
            event.add_activity(
                description="Dinner",
                amount=Decimal("100"),
                payer=bob,
                participants=[alice],
            )

    def test_add_activity_participant_not_in_event_raises(self):
        """Test that adding activity with participant not in event raises ValidationError."""
        event = Event(name="Trip")
        alice = event.add_person("Alice")
        bob = Person(name="Bob")  # Not added to event
        with pytest.raises(ValidationError, match="not in the event"):
            event.add_activity(
                description="Dinner",
                amount=Decimal("100"),
                payer=alice,
                participants=[bob],
            )

    def test_compute_settlement(self):
        """Test computing settlement."""
        event = Event(name="Trip")
        alice = event.add_person("Alice")
        bob = event.add_person("Bob")
        event.add_activity(
            description="Dinner",
            amount=Decimal("100"),
            payer=alice,
            participants=[alice, bob],
        )
        transfers, summary = event.compute_settlement()
        assert isinstance(transfers, list)
        assert isinstance(summary, dict)
        assert alice in summary
        assert bob in summary

    def test_event_serialization(self):
        """Test event serialization."""
        event = Event(name="Trip")
        alice = event.add_person("Alice")
        bob = event.add_person("Bob")
        event.add_activity(
            description="Dinner",
            amount=Decimal("100"),
            payer=alice,
            participants=[alice, bob],
        )
        data = event.to_dict()
        assert data["name"] == "Trip"
        assert len(data["people"]) == 2
        assert len(data["activities"]) == 1

        restored = Event.from_dict(data)
        assert restored.name == event.name
        assert len(restored.people) == 2
        assert len(restored.activities) == 1


class TestSettlementTransfer:
    """Tests for SettlementTransfer model."""

    def test_create_transfer(self):
        """Test creating a transfer."""
        alice = Person(name="Alice")
        bob = Person(name="Bob")
        transfer = SettlementTransfer(from_person=bob, to_person=alice, amount=Decimal("50.00"))
        assert transfer.from_person == bob
        assert transfer.to_person == alice
        assert transfer.amount == Decimal("50.00")

    def test_transfer_negative_amount_raises(self):
        """Test that negative transfer amount raises ValidationError."""
        alice = Person(name="Alice")
        bob = Person(name="Bob")
        with pytest.raises(ValidationError, match="must be non-negative"):
            SettlementTransfer(from_person=bob, to_person=alice, amount=Decimal("-10"))

