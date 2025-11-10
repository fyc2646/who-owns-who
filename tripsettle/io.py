"""I/O functionality for reading and writing events and settlements."""

import csv
import json
from decimal import Decimal
from pathlib import Path
from typing import Dict, List

from tripsettle.errors import ValidationError
from tripsettle.models import Activity, Event, Person, SettlementTransfer, SplitStrategy


def from_csv(path_people: str, path_activities: str) -> Event:
    """
    Load an event from CSV files.

    CSV Schema:
    - people.csv: id, name
    - activities.csv: id, description, amount, payer_id, participants (comma-separated IDs),
                      split_strategy, weights (optional JSON dict), shares (optional JSON dict)

    Parameters
    ----------
    path_people : str
        Path to people CSV file.
    path_activities : str
        Path to activities CSV file.

    Returns
    -------
    Event
        The loaded event.

    Raises
    ------
    ValidationError
        If CSV files are malformed or missing required fields.
    """
    from uuid import UUID

    # Read people
    people_map: Dict[str, Person] = {}
    event_name = "Imported Event"
    currency = "USD"

    with open(path_people, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            person_id = row.get("id", "").strip()
            name = row.get("name", "").strip()
            if not person_id or not name:
                raise ValidationError(f"Invalid person row: {row}")
            person = Person(id=UUID(person_id), name=name)
            people_map[person_id] = person

    if not people_map:
        raise ValidationError("No people found in CSV")

    # Read activities
    activities: List[Activity] = []

    with open(path_activities, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            activity_id = row.get("id", "").strip()
            description = row.get("description", "").strip()
            amount_str = row.get("amount", "").strip()
            payer_id = row.get("payer_id", "").strip()
            participants_str = row.get("participants", "").strip()
            split_strategy_str = row.get("split_strategy", "EQUAL").strip().upper()
            weights_str = row.get("weights", "").strip()
            shares_str = row.get("shares", "").strip()

            if not description or not amount_str or not payer_id or not participants_str:
                raise ValidationError(f"Invalid activity row: {row}")

            try:
                amount = Decimal(amount_str)
            except (ValueError, TypeError) as e:
                raise ValidationError(f"Invalid amount '{amount_str}': {e}")

            # Parse payer
            if payer_id not in people_map:
                raise ValidationError(f"Payer ID {payer_id} not found in people")
            payer = people_map[payer_id]

            # Parse participants
            participant_ids = [pid.strip() for pid in participants_str.split(",") if pid.strip()]
            participants = []
            for pid in participant_ids:
                if pid not in people_map:
                    raise ValidationError(f"Participant ID {pid} not found in people")
                participants.append(people_map[pid])

            if not participants:
                raise ValidationError(f"Activity {description} has no participants")

            # Parse split strategy
            try:
                split_strategy = SplitStrategy(split_strategy_str)
            except ValueError:
                raise ValidationError(f"Invalid split strategy: {split_strategy_str}")

            # Parse weights if provided
            weights = None
            if weights_str:
                try:
                    weights_dict = json.loads(weights_str)
                    weights = {people_map[pid]: Decimal(str(w)) for pid, w in weights_dict.items()}
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    raise ValidationError(f"Invalid weights JSON: {e}")

            # Parse shares if provided
            shares = None
            if shares_str:
                try:
                    shares_dict = json.loads(shares_str)
                    shares = {people_map[pid]: Decimal(str(s)) for pid, s in shares_dict.items()}
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    raise ValidationError(f"Invalid shares JSON: {e}")

            activity = Activity(
                id=UUID(activity_id) if activity_id else None,
                description=description,
                amount=amount,
                payer=payer,
                participants=participants,
                split_strategy=split_strategy,
                weights=weights,
                shares=shares,
                currency=currency,
            )
            activities.append(activity)

    # Create event
    event = Event(
        name=event_name,
        people=list(people_map.values()),
        activities=activities,
        currency=currency,
    )

    return event


def to_json(event: Event, path: str) -> None:
    """
    Write an event to a JSON file.

    Parameters
    ----------
    event : Event
        The event to write.
    path : str
        Path to output JSON file.
    """
    data = event.to_dict()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def to_csv(event: Event, transfers: List[SettlementTransfer], summary: Dict[Person, Dict[str, Decimal]], path_dir: str) -> None:
    """
    Write settlement results to CSV files.

    Creates:
    - transfers.csv: from_person_id, from_person_name, to_person_id, to_person_name, amount
    - summary.csv: person_id, person_name, paid, owed, net

    Parameters
    ----------
    event : Event
        The event.
    transfers : List[SettlementTransfer]
        List of transfers.
    summary : Dict[Person, Dict[str, Decimal]]
        Summary dictionary.
    path_dir : str
        Directory to write CSV files to.
    """
    path_dir_obj = Path(path_dir)
    path_dir_obj.mkdir(parents=True, exist_ok=True)

    # Write transfers.csv
    transfers_path = path_dir_obj / "transfers.csv"
    with open(transfers_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["from_person_id", "from_person_name", "to_person_id", "to_person_name", "amount"])
        for transfer in sorted(transfers, key=lambda t: (t.from_person.name, str(t.from_person.id))):
            writer.writerow([
                str(transfer.from_person.id),
                transfer.from_person.name,
                str(transfer.to_person.id),
                transfer.to_person.name,
                str(transfer.amount),
            ])

    # Write summary.csv
    summary_path = path_dir_obj / "summary.csv"
    with open(summary_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["person_id", "person_name", "paid", "owed", "net"])
        for person in sorted(summary.keys(), key=lambda p: (p.name, str(p.id))):
            data = summary[person]
            writer.writerow([
                str(person.id),
                person.name,
                str(data["paid"]),
                str(data["owed"]),
                str(data["net"]),
            ])

