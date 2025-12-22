# Centralized Email Webhook System

Real-time email processing system using Microsoft Graph webhooks.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your Microsoft Graph credentials
```

3. Run locally:
```bash
uvicorn main:app --reload
```

4. Deploy to Render:
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

## Project Structure

```
webhook_email_system/
├── main.py                 # FastAPI application
├── config.py               # Configuration loader
├── api/                    # API endpoints
├── services/               # Business logic
├── routing/                # Email routing
├── models/                 # Data models
├── utils/                  # Utilities
├── config/                 # Configuration files
└── tests/                  # Tests
```

## Documentation

See `implementation_plan.md` for detailed architecture and implementation guide.
