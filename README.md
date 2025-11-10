# tripsettle

A production-quality Python 3.11+ package for settling shared trip expenses among friends. Compute the minimal set of transfers so everyone ends up paying their fair share.

## Features

- **Multiple Split Strategies**: Equal, weighted, or fixed shares per activity
- **Multi-Payer Support**: Handle activities where multiple people contribute
- **Precise Money Handling**: Uses `Decimal` for all currency math with banker's rounding
- **Minimal Transfers**: Computes the smallest number of transfers needed to settle expenses
- **Clean API**: No CLI, just a Python API designed for integration
- **Comprehensive Testing**: 100% branch coverage for core modules
- **Type Safe**: Full type hints with mypy strict checking

## Quick Start

```python
from decimal import Decimal
from tripsettle.models import Event

# Create an event
e = Event(name="Ski Trip", currency="USD")
alice = e.add_person("Alice")
bob = e.add_person("Bob")
carol = e.add_person("Carol")

# Add activities
e.add_activity(
    "Dinner",
    Decimal("150"),
    payer=alice,
    participants=[alice, bob, carol],
    split_strategy="EQUAL"
)

e.add_activity(
    "Gas",
    Decimal("60"),
    payer=bob,
    participants=[alice, bob],
    split_strategy="EQUAL"
)

e.add_activity(
    "Museum",
    Decimal("90"),
    payer=carol,
    participants=[bob, carol],
    split_strategy="WEIGHTED",
    weights={bob: Decimal("2"), carol: Decimal("1")}
)

# Compute settlement
transfers, summary = e.compute_settlement()

# View results
for person, data in summary.items():
    print(f"{person.name}: paid={data['paid']}, owed={data['owed']}, net={data['net']}")

for transfer in transfers:
    print(f"{transfer.from_person.name} -> {transfer.to_person.name}: ${transfer.amount}")
```

## Installation

```bash
pip install tripsettle
```

For development:

```bash
git clone https://github.com/yourusername/tripsettle.git
cd tripsettle
pip install -e ".[dev]"
```

## Split Strategies

### EQUAL
Split the expense equally among all participants.

```python
e.add_activity(
    "Dinner",
    Decimal("100"),
    payer=alice,
    participants=[alice, bob, carol],
    split_strategy="EQUAL"
)
# Each person owes $33.33
```

### WEIGHTED
Split based on weights (automatically normalized to sum to 1.0).

```python
e.add_activity(
    "Museum",
    Decimal("90"),
    payer=carol,
    participants=[bob, carol],
    split_strategy="WEIGHTED",
    weights={bob: Decimal("2"), carol: Decimal("1")}
)
# Bob owes $60 (2/3), Carol owes $30 (1/3)
```

### FIXED_SHARES
Specify exact amounts each person owes (must sum to activity amount).

```python
e.add_activity(
    "Dinner",
    Decimal("100"),
    payer=alice,
    participants=[alice, bob],
    split_strategy="FIXED_SHARES",
    shares={alice: Decimal("60"), bob: Decimal("40")}
)
```

## Multi-Payer Activities

Support activities where multiple people contribute:

```python
e.add_activity(
    "Dinner",
    Decimal("100"),
    payer=[(alice, Decimal("60")), (bob, Decimal("40"))],
    participants=[alice, bob, carol],
    split_strategy="EQUAL"
)
```

## I/O

### JSON

```python
from tripsettle.io import to_json
from tripsettle.models import Event

event = Event(name="Trip")
# ... add people and activities ...

to_json(event, "event.json")
```

### CSV

```python
from tripsettle.io import from_csv, to_csv

# Load from CSV
event = from_csv("people.csv", "activities.csv")

# Save settlement results
transfers, summary = event.compute_settlement()
to_csv(event, transfers, summary, "output/")
# Creates output/transfers.csv and output/summary.csv
```

See `examples/` directory for CSV schema examples.

## API Reference

### Event

- `add_person(name: str) -> Person`: Add a person to the event
- `add_activity(...) -> Activity`: Add an expense activity
- `compute_settlement() -> tuple[list[SettlementTransfer], dict[Person, dict]]`: Compute settlement
- `to_dict() -> dict`: Serialize to dictionary
- `from_dict(data: dict) -> Event`: Deserialize from dictionary

### Models

- `Person`: Represents a person (id, name)
- `Activity`: Represents an expense activity
- `SettlementTransfer`: Represents a transfer from one person to another
- `Event`: Container for people and activities

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=tripsettle --cov-report=html

# Type checking
mypy tripsettle

# Linting
ruff check tripsettle
black --check tripsettle
```

## Design

See [DESIGN.md](DESIGN.md) for detailed information about:
- The minimal cash flow algorithm
- Rounding policy and remainder distribution
- Limitations and future enhancements

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

