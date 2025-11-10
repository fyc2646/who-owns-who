# Quick Start Guide - Who Owes Who Web UI

## Installation

```bash
# Install Flask (if not already installed)
pip install flask

# Or install the full package
pip install -e .
```

## Running the Application

```bash
python app.py
```

Then open your browser to: **http://localhost:5000**

## Quick Demo

1. **Create Event**: Enter "Ski Trip 2024" and select USD
2. **Add People**: 
   - Alice
   - Bob
   - Carol
3. **Add Activities**:
   - **Dinner**: $150, paid by Alice, split equally among all three
   - **Gas**: $60, paid by Bob, split equally between Alice and Bob
   - **Museum**: $90, paid by Carol, weighted (Bob: 2, Carol: 1)
4. **Compute Settlement**: Click the button to see who owes whom!

## Features

- ✅ Beautiful, modern UI with gradient design
- ✅ Responsive layout (works on mobile too)
- ✅ Support for all split strategies (Equal, Weighted, Fixed Shares)
- ✅ Real-time settlement computation
- ✅ Clear visualization of transfers needed

## API Usage

The web UI uses REST API endpoints that you can also call directly:

```bash
# Create event
curl -X POST http://localhost:5000/api/event \
  -H "Content-Type: application/json" \
  -d '{"name": "Ski Trip", "currency": "USD"}'

# Add person
curl -X POST http://localhost:5000/api/event/{event_id}/person \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice"}'

# Compute settlement
curl http://localhost:5000/api/event/{event_id}/settlement
```

Enjoy splitting expenses fairly! 💰

