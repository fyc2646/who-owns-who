# Who Owes Who Web UI

A beautiful, modern web interface for the Who Owes Who expense splitting app built with Flask.

## Features

- 🎨 **Elegant UI**: Modern, responsive design with a beautiful gradient background
- 👥 **People Management**: Easily add people to your event
- 💰 **Activity Tracking**: Add expenses with different split strategies (Equal, Weighted, Fixed Shares)
- 📊 **Settlement View**: See who owes whom and view detailed summaries
- 📱 **Responsive**: Works great on desktop and mobile devices

## Installation

1. Install Flask (if not already installed):
```bash
pip install flask
```

Or install the package with Flask:
```bash
pip install -e ".[dev]"
```

## Running the Application

1. Start the Flask server:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

## Usage

1. **Create an Event**: Enter an event name and select a currency
2. **Add People**: Add all participants to the event
3. **Add Activities**: 
   - Enter activity description and amount
   - Select who paid
   - Choose participants
   - Select split strategy (Equal, Weighted, or Fixed Shares)
   - For Weighted: Enter weights for each participant
   - For Fixed Shares: Enter exact amounts for each participant
4. **Compute Settlement**: Click the button to see who owes whom

## API Endpoints

The Flask app provides the following REST API endpoints:

- `POST /api/event` - Create a new event
- `GET /api/event/<event_id>` - Get event details
- `POST /api/event/<event_id>/person` - Add a person to an event
- `POST /api/event/<event_id>/activity` - Add an activity to an event
- `GET /api/event/<event_id>/settlement` - Compute settlement

## Development

The application uses:
- **Backend**: Flask (Python)
- **Frontend**: Vanilla JavaScript (no frameworks)
- **Styling**: Modern CSS with CSS variables for theming

## Notes

- Events are stored in-memory (use a database for production)
- The secret key should be changed for production deployments
- For production, use a proper WSGI server like Gunicorn

## Example Workflow

1. Create event "Ski Trip 2024"
2. Add people: Alice, Bob, Carol
3. Add activities:
   - Dinner: $150, paid by Alice, split equally among all
   - Gas: $60, paid by Bob, split equally between Alice and Bob
   - Museum: $90, paid by Carol, weighted (Bob: 2, Carol: 1)
4. Compute settlement to see transfers needed

