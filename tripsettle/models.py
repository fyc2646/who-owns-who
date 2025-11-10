"""Data models for tripsettle package."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

from tripsettle.errors import ValidationError
from tripsettle.utils import round_money, validate_amount


class SplitStrategy(str, Enum):
    """Enumeration of split strategies for activities."""

    EQUAL = "EQUAL"
    WEIGHTED = "WEIGHTED"
    FIXED_SHARES = "FIXED_SHARES"


@dataclass(frozen=True, eq=True, order=False)
class Person:
    """
    Represents a person participating in an event.

    Attributes
    ----------
    id : UUID
        Unique identifier for the person.
    name : str
        Name of the person.
    """

    name: str
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        """Validate person data."""
        if not self.name or not self.name.strip():
            raise ValidationError("Person name cannot be empty")

    def to_dict(self) -> dict:
        """Serialize person to dictionary."""
        return {"id": str(self.id), "name": self.name}

    @classmethod
    def from_dict(cls, data: dict) -> "Person":
        """Deserialize person from dictionary."""
        return cls(id=UUID(data["id"]), name=data["name"])


@dataclass
class Activity:
    """
    Represents an expense activity in an event.

    Attributes
    ----------
    id : UUID
        Unique identifier for the activity.
    description : str
        Description of the activity.
    amount : Decimal
        Total amount of the activity.
    payer : Union[Person, List[tuple[Person, Decimal]]]
        Person(s) who paid, optionally with amounts for multi-payer.
    participants : List[Person]
        List of people who participated in the activity.
    split_strategy : SplitStrategy
        How to split the expense among participants.
    weights : Optional[Dict[Person, Decimal]]
        Weights for WEIGHTED split strategy.
    shares : Optional[Dict[Person, Decimal]]
        Fixed shares for FIXED_SHARES split strategy.
    currency : str
        Currency code (default: "USD").
    """

    id: UUID = field(default_factory=uuid4)
    description: str = ""
    amount: Decimal = Decimal("0")
    payer: Union[Person, List[tuple[Person, Decimal]]] = field(default_factory=list)
    participants: List[Person] = field(default_factory=list)
    split_strategy: SplitStrategy = SplitStrategy.EQUAL
    weights: Optional[Dict[Person, Decimal]] = None
    shares: Optional[Dict[Person, Decimal]] = None
    currency: str = "USD"

    def __post_init__(self) -> None:
        """Validate activity data."""
        validate_amount(self.amount, "activity amount")

        if not self.description or not self.description.strip():
            raise ValidationError("Activity description cannot be empty")

        if not self.participants:
            raise ValidationError("Activity must have at least one participant")

        if not self.payer:
            raise ValidationError("Activity must have at least one payer")

        # Validate payer structure
        if isinstance(self.payer, list):
            if not self.payer:
                raise ValidationError("Activity must have at least one payer")
            payer_total = sum(amt for _, amt in self.payer)
            if abs(payer_total - self.amount) > Decimal("0.01"):
                raise ValidationError(
                    f"Multi-payer amounts sum to {payer_total}, but activity amount is {self.amount}"
                )
            for person, amt in self.payer:
                validate_amount(amt, f"payer {person.name} amount")
        else:
            # Single payer - validate they're in participants if needed
            pass

        # Validate split strategy configuration
        if self.split_strategy == SplitStrategy.WEIGHTED:
            if not self.weights:
                raise ValidationError("WEIGHTED strategy requires weights")
            weight_sum = sum(self.weights.values())
            if abs(weight_sum - Decimal("1.0")) > Decimal("0.01"):
                # Re-normalize if close
                if weight_sum > 0:
                    self.weights = {p: w / weight_sum for p, w in self.weights.items()}
                else:
                    raise ValidationError(f"Weights sum to {weight_sum}, must be positive")

        elif self.split_strategy == SplitStrategy.FIXED_SHARES:
            if not self.shares:
                raise ValidationError("FIXED_SHARES strategy requires shares")
            shares_sum = sum(self.shares.values())
            if abs(shares_sum - self.amount) > Decimal("0.01"):
                raise ValidationError(
                    f"Fixed shares sum to {shares_sum}, but activity amount is {self.amount}"
                )
            # Validate all shares are non-negative
            for person, share in self.shares.items():
                validate_amount(share, f"share for {person.name}")

    def get_payers(self) -> List[tuple[Person, Decimal]]:
        """
        Get list of payers with amounts.

        Returns
        -------
        List[tuple[Person, Decimal]]
            List of (person, amount) tuples.
        """
        if isinstance(self.payer, list):
            return self.payer
        return [(self.payer, self.amount)]

    def to_dict(self) -> dict:
        """Serialize activity to dictionary."""
        result = {
            "id": str(self.id),
            "description": self.description,
            "amount": str(self.amount),
            "participants": [p.to_dict() for p in sorted(self.participants, key=lambda x: (x.name, str(x.id)))],
            "split_strategy": self.split_strategy.value,
            "currency": self.currency,
        }

        # Serialize payer(s)
        payers = self.get_payers()
        if len(payers) == 1:
            result["payer"] = payers[0][0].to_dict()
        else:
            result["payer"] = [{"person": p.to_dict(), "amount": str(amt)} for p, amt in payers]

        # Serialize strategy-specific data
        if self.weights:
            result["weights"] = {str(p.id): str(w) for p, w in self.weights.items()}
        if self.shares:
            result["shares"] = {str(p.id): str(s) for p, s in self.shares.items()}

        return result

    @classmethod
    def from_dict(cls, data: dict, people_map: Dict[str, Person]) -> "Activity":
        """Deserialize activity from dictionary."""
        # Reconstruct people from IDs
        participants = [people_map[p["id"]] for p in data["participants"]]

        # Reconstruct payer(s)
        payer_data = data["payer"]
        if isinstance(payer_data, list):
            payer = [(people_map[p["person"]["id"]], Decimal(p["amount"])) for p in payer_data]
        else:
            payer = people_map[payer_data["id"]]

        # Reconstruct strategy-specific data
        weights = None
        if "weights" in data:
            weights = {people_map[pid]: Decimal(w) for pid, w in data["weights"].items()}

        shares = None
        if "shares" in data:
            shares = {people_map[pid]: Decimal(s) for pid, s in data["shares"].items()}

        return cls(
            id=UUID(data["id"]),
            description=data["description"],
            amount=Decimal(data["amount"]),
            payer=payer,
            participants=participants,
            split_strategy=SplitStrategy(data["split_strategy"]),
            weights=weights,
            shares=shares,
            currency=data.get("currency", "USD"),
        )


@dataclass
class SettlementTransfer:
    """
    Represents a transfer from one person to another to settle expenses.

    Attributes
    ----------
    from_person : Person
        Person who owes money.
    to_person : Person
        Person who should receive money.
    amount : Decimal
        Amount to transfer (rounded to 2 decimals).
    """

    from_person: Person
    to_person: Person
    amount: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        """Validate and round transfer amount."""
        validate_amount(self.amount, "transfer amount")
        self.amount = round_money(self.amount)

    def to_dict(self) -> dict:
        """Serialize transfer to dictionary."""
        return {
            "from_person": self.from_person.to_dict(),
            "to_person": self.to_person.to_dict(),
            "amount": str(self.amount),
        }

    @classmethod
    def from_dict(cls, data: dict, people_map: Dict[str, Person]) -> "SettlementTransfer":
        """Deserialize transfer from dictionary."""
        return cls(
            from_person=people_map[data["from_person"]["id"]],
            to_person=people_map[data["to_person"]["id"]],
            amount=Decimal(data["amount"]),
        )


@dataclass
class Event:
    """
    Represents an event with people and expense activities.

    Attributes
    ----------
    id : UUID
        Unique identifier for the event.
    name : str
        Name of the event.
    people : List[Person]
        List of people participating in the event.
    activities : List[Activity]
        List of expense activities.
    currency : str
        Currency code (default: "USD").
    """

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    people: List[Person] = field(default_factory=list)
    activities: List[Activity] = field(default_factory=list)
    currency: str = "USD"

    def add_person(self, name: str) -> Person:
        """
        Add a person to the event.

        Parameters
        ----------
        name : str
            Name of the person.

        Returns
        -------
        Person
            The created person.
        """
        person = Person(name=name)
        self.people.append(person)
        return person

    def add_activity(
        self,
        description: str,
        amount: Decimal,
        payer: Union[Person, List[tuple[Person, Decimal]]],
        participants: List[Person],
        split_strategy: Union[str, SplitStrategy] = "EQUAL",
        weights: Optional[Dict[Person, Decimal]] = None,
        shares: Optional[Dict[Person, Decimal]] = None,
    ) -> Activity:
        """
        Add an activity to the event.

        Parameters
        ----------
        description : str
            Description of the activity.
        amount : Decimal
            Total amount of the activity.
        payer : Union[Person, List[tuple[Person, Decimal]]]
            Person(s) who paid.
        participants : List[Person]
            List of people who participated.
        split_strategy : Union[str, SplitStrategy], default="EQUAL"
            How to split the expense.
        weights : Optional[Dict[Person, Decimal]], default=None
            Weights for WEIGHTED strategy.
        shares : Optional[Dict[Person, Decimal]], default=None
            Fixed shares for FIXED_SHARES strategy.

        Returns
        -------
        Activity
            The created activity.

        Raises
        ------
        ValidationError
            If payer or participants are not in the event's people list.
        """
        # Validate people belong to event
        event_people_set = set(self.people)

        # Validate payer(s)
        if isinstance(payer, list):
            for p, _ in payer:
                if p not in event_people_set:
                    raise ValidationError(f"Payer {p.name} is not in the event")
        else:
            if payer not in event_people_set:
                raise ValidationError(f"Payer {payer.name} is not in the event")

        # Validate participants
        for participant in participants:
            if participant not in event_people_set:
                raise ValidationError(f"Participant {participant.name} is not in the event")

        # Convert string to enum if needed
        if isinstance(split_strategy, str):
            split_strategy = SplitStrategy(split_strategy)

        activity = Activity(
            description=description,
            amount=amount,
            payer=payer,
            participants=participants,
            split_strategy=split_strategy,
            weights=weights,
            shares=shares,
            currency=self.currency,
        )

        self.activities.append(activity)
        return activity

    def compute_settlement(
        self,
    ) -> Tuple[List[SettlementTransfer], Dict[Person, Dict[str, Decimal]]]:
        """
        Compute settlement transfers and summary for the event.

        Returns
        -------
        Tuple[List[SettlementTransfer], Dict[Person, Dict[str, Decimal]]]
            A tuple of (transfers, summary) where:
            - transfers: List of transfers needed to settle expenses
            - summary: Dict mapping person to their paid/owed/net amounts
        """
        from tripsettle.compute import compute_minimal_transfers, compute_net_balances, compute_settlement_summary

        balances = compute_net_balances(self)
        transfers = compute_minimal_transfers(balances)
        summary = compute_settlement_summary(self, balances)

        return transfers, summary

    def to_dict(self) -> dict:
        """Serialize event to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "currency": self.currency,
            "people": [p.to_dict() for p in sorted(self.people, key=lambda x: (x.name, str(x.id)))],
            "activities": [
                a.to_dict() for a in sorted(self.activities, key=lambda x: (x.description, str(x.id)))
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Event":
        """Deserialize event from dictionary."""
        # First, create people map
        people = [Person.from_dict(p) for p in data["people"]]
        people_map = {str(p.id): p for p in people}

        # Then create activities (which reference people)
        activities = [Activity.from_dict(a, people_map) for a in data["activities"]]

        return cls(
            id=UUID(data["id"]),
            name=data["name"],
            currency=data.get("currency", "USD"),
            people=people,
            activities=activities,
        )

