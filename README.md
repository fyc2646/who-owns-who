# Who Owes Who 💰

A production-quality Python package and beautiful Flask web application for settling shared trip expenses among friends. Compute the minimal set of transfers so everyone ends up paying their fair share.

[![GitHub](https://img.shields.io/badge/GitHub-fyc2646%2Fwho--owns--who-blue)](https://github.com/fyc2646/who-owns-who)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## Features

### Python Package
- **Multiple Split Strategies**: Equal, weighted, or fixed shares per activity
- **Multi-Payer Support**: Handle activities where multiple people contribute
- **Precise Money Handling**: Uses `Decimal` for all currency math with banker's rounding
- **Minimal Transfers**: Computes the smallest number of transfers needed to settle expenses
- **Clean API**: Python API designed for integration
- **Comprehensive Testing**: 100% branch coverage for core modules
- **Type Safe**: Full type hints with mypy strict checking

### Web Application
- 🎨 **Elegant UI**: Modern, responsive design with a beautiful gradient background
- 👥 **People Management**: Easily add people to your event
- 💰 **Activity Tracking**: Add expenses with different split strategies
- 📊 **Settlement View**: See who owes whom with detailed summaries
- 📱 **Responsive**: Works great on desktop and mobile devices

## Quick Start

### Web Application (Recommended)

1. **Install Flask**:
```bash
pip install flask
```

2. **Run the application**:
```bash
python app.py
```

3. **Open your browser**:
```
http://localhost:5000
```

4. **Start using it**:
   - Create an event
   - Add people
   - Add activities
   - Compute settlement!

See [QUICKSTART.md](QUICKSTART.md) for a detailed walkthrough.

### Python Package

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

### For Development

```bash
# Clone the repository
git clone https://github.com/fyc2646/who-owns-who.git
cd who-owns-who

# Install in development mode
pip install -e ".[dev]"
```

### Dependencies

The package requires:
- Python 3.11+
- Flask 3.0+ (for web application)

Install Flask:
```bash
pip install flask
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

## Web Application API

The Flask app provides REST API endpoints:

- `POST /api/event` - Create a new event
- `GET /api/event/<event_id>` - Get event details
- `POST /api/event/<event_id>/person` - Add a person to an event
- `POST /api/event/<event_id>/activity` - Add an activity to an event
- `GET /api/event/<event_id>/settlement` - Compute settlement

See [README_FLASK.md](README_FLASK.md) for more details.

## Python API Reference

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

## Project Structure

```
who-owes-who/
├── tripsettle/          # Python package
│   ├── __init__.py
│   ├── models.py        # Data models
│   ├── strategies.py    # Split strategies
│   ├── compute.py       # Settlement computation
│   ├── io.py            # CSV/JSON I/O
│   ├── errors.py        # Custom exceptions
│   └── utils.py         # Utilities
├── app.py               # Flask web application
├── templates/           # HTML templates
├── static/              # CSS and JavaScript
├── tests/               # Test suite
├── examples/            # Example CSV files
└── docs/                # Documentation
```

## Design

See [DESIGN.md](DESIGN.md) for detailed information about:
- The minimal cash flow algorithm
- Rounding policy and remainder distribution
- Limitations and future enhancements

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Repository

**GitHub**: [fyc2646/who-owns-who](https://github.com/fyc2646/who-owns-who)

---

Made with ❤️ for fair expense splitting
