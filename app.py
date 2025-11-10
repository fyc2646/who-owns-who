"""Flask application for Who Owes Who web UI."""

from decimal import Decimal
from flask import Flask, render_template, request, jsonify, session
from tripsettle.models import Event, SplitStrategy

app = Flask(__name__)
app.secret_key = "who-owes-who-secret-key-change-in-production"  # Change in production!

# In-memory storage (use a database in production)
events_store: dict[str, Event] = {}


@app.route("/")
def index():
    """Render the main page."""
    return render_template("index.html")


@app.route("/api/event", methods=["POST"])
def create_event():
    """Create a new event."""
    data = request.json
    event = Event(name=data.get("name", "New Event"), currency=data.get("currency", "USD"))
    event_id = str(event.id)
    events_store[event_id] = event
    session["current_event_id"] = event_id
    return jsonify({"event_id": event_id, "name": event.name, "currency": event.currency})


@app.route("/api/event/<event_id>", methods=["GET"])
def get_event(event_id: str):
    """Get event details."""
    if event_id not in events_store:
        return jsonify({"error": "Event not found"}), 404
    
    event = events_store[event_id]
    return jsonify({
        "id": str(event.id),
        "name": event.name,
        "currency": event.currency,
        "people": [{"id": str(p.id), "name": p.name} for p in event.people],
        "activities": [
            {
                "id": str(a.id),
                "description": a.description,
                "amount": str(a.amount),
                "payer": a.get_payers()[0][0].name if len(a.get_payers()) == 1 else "Multiple",
                "participants": [p.name for p in a.participants],
                "split_strategy": a.split_strategy.value,
            }
            for a in event.activities
        ],
    })


@app.route("/api/event/<event_id>/person", methods=["POST"])
def add_person(event_id: str):
    """Add a person to an event."""
    if event_id not in events_store:
        return jsonify({"error": "Event not found"}), 404
    
    data = request.json
    person = events_store[event_id].add_person(data["name"])
    return jsonify({"id": str(person.id), "name": person.name})


@app.route("/api/event/<event_id>/activity", methods=["POST"])
def add_activity(event_id: str):
    """Add an activity to an event."""
    if event_id not in events_store:
        return jsonify({"error": "Event not found"}), 404
    
    event = events_store[event_id]
    data = request.json
    
    # Find payer
    payer_name = data["payer"]
    payer = next((p for p in event.people if p.name == payer_name), None)
    if not payer:
        return jsonify({"error": f"Payer '{payer_name}' not found"}), 400
    
    # Find participants
    participant_names = data["participants"]
    participants = [p for p in event.people if p.name in participant_names]
    if len(participants) != len(participant_names):
        missing = set(participant_names) - {p.name for p in participants}
        return jsonify({"error": f"Participants not found: {', '.join(missing)}"}), 400
    
    # Parse split strategy
    split_strategy = data.get("split_strategy", "EQUAL")
    weights = None
    shares = None
    
    if split_strategy == "WEIGHTED" and "weights" in data:
        weights = {
            next(p for p in event.people if p.name == name): Decimal(str(w))
            for name, w in data["weights"].items()
        }
    elif split_strategy == "FIXED_SHARES" and "shares" in data:
        shares = {
            next(p for p in event.people if p.name == name): Decimal(str(s))
            for name, s in data["shares"].items()
        }
    
    activity = event.add_activity(
        description=data["description"],
        amount=Decimal(str(data["amount"])),
        payer=payer,
        participants=participants,
        split_strategy=split_strategy,
        weights=weights,
        shares=shares,
    )
    
    return jsonify({
        "id": str(activity.id),
        "description": activity.description,
        "amount": str(activity.amount),
        "payer": payer.name,
        "participants": [p.name for p in participants],
        "split_strategy": split_strategy,
    })


@app.route("/api/event/<event_id>/settlement", methods=["GET"])
def compute_settlement(event_id: str):
    """Compute settlement for an event."""
    if event_id not in events_store:
        return jsonify({"error": "Event not found"}), 404
    
    event = events_store[event_id]
    transfers, summary = event.compute_settlement()
    
    return jsonify({
        "transfers": [
            {
                "from": t.from_person.name,
                "to": t.to_person.name,
                "amount": str(t.amount),
            }
            for t in transfers
        ],
        "summary": {
            p.name: {
                "paid": str(data["paid"]),
                "owed": str(data["owed"]),
                "net": str(data["net"]),
            }
            for p, data in summary.items()
        },
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)

