# Centralized Email Webhook System

A production-ready, enterprise-grade Microsoft Outlook email webhook system that processes emails in real-time through a centralized server and dispatches them to multiple utility APIs based on configurable filtering rules.

## Overview

This system replaces traditional scheduler-based email polling with real-time webhook notifications from Microsoft Graph. It provides:

- **Real-time Processing**: Instant email notification via webhooks (no polling delays)
- **Centralized Logic**: All email filtering and routing in one place
- **Scalable Architecture**: Handle multiple mailboxes and utilities
- **Enterprise Features**: Attachment handling, retry logic, comprehensive logging, security validation
- **Auto-Management**: Subscription auto-renewal, smart subscription creation

## Key Features

### Core Functionality
- Microsoft Graph webhook integration
- Real-time email notifications
- Comprehensive email metadata fetching (including full attachment content)
- Multi-utility routing engine with complex filter rules
- Concurrent API dispatching with rate limiting
- Email deduplication (handles CC/TO scenarios)

### Enterprise Features
- **Attachment Handling**: Downloads full attachment content with base64 decoding
- **Retry Mechanism**: 3 attempts with exponential backoff for connection failures
- **Processing Logs**: Detailed JSON logs tracking entire email flow
- **Security Validation**: Client state verification for webhook notifications
- **Auto-Renewal**: Background task renews subscriptions every 12 hours
- **Fail-Soft Design**: Individual utility failures don't crash the system

### Filter Capabilities
- Subject matching (contains, regex)
- Body content matching (contains, regex)
- Sender filtering (exact, in-list, contains)
- Receiver filtering (in-list, contains)
- Attachment requirements (required, filename patterns)
- Email direction (received, sent, both)
- Folder-based filtering
- AND/OR logic combinations

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Microsoft Graph                           │
│              (Webhook Notifications)                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Centralized Webhook Server                      │
│                 (Render/Physical Server)                     │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  1. Webhook Endpoint                                 │   │
│  │     - Validation (client state)                      │   │
│  │     - Fire-and-forget response                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                     │                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  2. Email Fetcher                                    │   │
│  │     - Full metadata retrieval                        │   │
│  │     - Attachment downloading                         │   │
│  │     - Deduplication                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                     │                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  3. Rule Matcher                                     │   │
│  │     - Complex filter evaluation                      │   │
│  │     - Match to utilities                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                     │                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  4. Dispatcher                                       │   │
│  │     - Concurrent API calls                           │   │
│  │     - Retry with backoff                             │   │
│  │     - Processing logs                                │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────┐         ┌──────────────┐
│  Utility 1   │   ...   │  Utility N   │
│  (Own API)   │         │  (Own API)   │
└──────────────┘         └──────────────┘
```

## Project Structure

```
Webhook_/
├── api/
│   ├── __init__.py
│   ├── webhook.py              # Webhook endpoint & notifications
│   └── test_endpoints.py       # Testing endpoints
│
├── services/
│   ├── __init__.py
│   ├── graph_service.py        # Microsoft Graph API client
│   ├── config_service.py       # Configuration loader
│   ├── email_fetcher.py        # Email metadata fetcher
│   ├── attachment_downloader.py # Attachment content downloader
│   ├── subscription_manager.py  # Subscription management
│   └── services.py             # Legacy functions (to be refactored)
│
├── routing/
│   ├── __init__.py
│   ├── rule_matcher.py         # Email-to-utility matching
│   └── dispatcher.py           # Concurrent API dispatcher
│
├── models/
│   ├── __init__.py
│   ├── email_metadata.py       # Email data structure
│   └── utility_config.py       # Utility configuration model
│
├── utils/
│   ├── __init__.py
│   ├── deduplication.py        # Email deduplication
│   ├── logging_config.py       # Logging setup
│   ├── retry_handler.py        # Retry with backoff
│   ├── processing_logger.py    # Processing flow logs
│   └── webhook_validator.py    # Security validation
│
├── config/
│   └── utility_rules.json      # Utility configurations
│
├── logs/
│   └── processing/             # Daily processing logs
│
├── tests/
│   └── __init__.py
│
├── main.py                     # FastAPI application
├── config.py                   # Configuration loader
├── requirements.txt
├── .env                        # Environment variables (gitignored)
├── .env.example                # Environment template
├── .gitignore
├── README.md
├── TESTING.md                  # Testing guide
├── ENTERPRISE_FEATURES.md      # Feature implementation guide
├── FUTURE_ENHANCEMENTS.md      # Future improvements
└── SUBSCRIPTION_RENEWAL.md     # Auto-renewal documentation
```

## Quick Start

### Prerequisites

- Python 3.8+
- Microsoft 365 account with admin access
- Azure AD app registration with:
  - `Mail.Read` permission (Application)
  - Client credentials flow enabled

### Installation

1. **Clone the repository**
```bash
cd c:\Webhook_mail\Webhook_
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
# Copy template
copy .env.example .env

# Edit .env with your values:
CLIENT_ID=your_azure_app_client_id
CLIENT_SECRET=your_azure_app_secret
TENANT_ID=your_tenant_id
WEBHOOK_URL=https://your-app.onrender.com/webhook
WEBHOOK_CLIENT_STATE=YourSecretString
```

4. **Configure utilities**

Edit `config/utility_rules.json`:
```json
{
  "utilities": [
    {
      "id": "your_utility",
      "name": "Your Utility Name",
      "enabled": true,
      "subscriptions": {
        "mailboxes": [
          {"address": "mailbox@company.com", "folders": ["Inbox"]}
        ]
      },
      "pre_filters": {
        "match_logic": "AND",
        "subject": {"contains": ["keyword"]},
        "sender": {"exact": "sender@example.com"}
      },
      "endpoint": {
        "url": "https://your-utility-api.com/process",
        "method": "POST"
      },
      "timeout": 10
    }
  ]
}
```

5. **Run locally**
```bash
uvicorn main:app --reload
```

6. **Test**
```
http://localhost:8000/health
http://localhost:8000/docs
```

### Deployment (Render)

1. **Push to GitHub**
```bash
git add .
git commit -m "Initial setup"
git push
```

2. **Create Render Web Service**
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

3. **Set Environment Variables**
All variables from `.env` (see .env.example)

4. **Deploy and verify**
```
https://your-app.onrender.com/health
```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `CLIENT_ID` | Azure AD App ID | Yes | - |
| `CLIENT_SECRET` | Azure AD App Secret | Yes | - |
| `TENANT_ID` | Azure AD Tenant ID | Yes | - |
| `WEBHOOK_URL` | Public webhook URL | Yes | - |
| `WEBHOOK_CLIENT_STATE` | Security validation key | Yes | SecretClientState |
| `PORT` | Server port | No | 8000 |
| `MAX_CONCURRENT_FORWARDS` | Max parallel API calls | No | 25 |
| `BATCH_SIZE` | Emails per batch | No | 10 |
| `DEDUPLICATION_TTL` | Cache TTL (seconds) | No | 300 |
| `LOG_LEVEL` | Logging level | No | INFO |

### Utility Configuration Schema

See `config/utility_rules.json` for complete examples.

## Usage

### Creating Subscriptions

**Automatic (on startup):**
The system automatically creates all needed subscriptions based on `utility_rules.json`.

**Manual:**
```
POST /test/create-subscription?mailbox=email@company.com&folder=Inbox
```

### Listing Subscriptions
```
GET /test/subscriptions
```

### Testing Email Fetch
```
GET /test/fetch-emails?mailbox=email@company.com&limit=5
```

### Deleting Subscriptions
```
DELETE /test/delete-subscription/{subscription_id}
```

## How It Works

1. **Notification Arrives**: Microsoft sends webhook notification
2. **Validation**: Client state verified
3. **Deduplication**: Remove duplicate notifications
4. **Fetch Email**: Download full email + attachments from Graph API
5. **Match Rules**: Evaluate against all utility filters
6. **Dispatch**: Concurrently POST to matched utility APIs (with retry)
7. **Log**: Complete flow logged to `logs/processing/`

## Monitoring

### Application Logs
- **Render**: Dashboard → Logs tab
- **Local**: Console output + `logs/processing/`

### Processing Logs
Daily JSON files in `logs/processing/processing_YYYYMMDD.jsonl`

Events tracked:
- `notification_received`
- `email_fetched`
- `utilities_matched`
- `utility_call_start`
- `utility_call_success` / `utility_call_failure`
- `processing_complete`

### Health Check
```
GET /health
```

```json
{
  "status": "healthy",
  "service": "email_webhook"
}
```

## Current Status

**Production Ready**: ✅
- Deployed on Render
- Auto-renewal active
- All core features implemented
- Security validated
- Comprehensive logging

**Utilities**: 
- 1 test utility configured (webhook.site)
- Ready for 3 production utilities

## Next Steps

1. **Deploy Production Utilities** (see `migration_plan.md`)
   - Attachment Processor API
   - FE Number Tracker API
   - Multi-Keyword Inspector API

2. **Monitor & Optimize** (1 week)
   - Review processing logs
   - Tune concurrency settings
   - Identify bottlenecks

3. **Future Enhancements** (optional)
   - Rate limiting per utility
   - Metrics dashboard
   - Configuration validation
   - Dead letter queue

## Documentation

- [Testing Guide](TESTING.md) - How to test all features
- [Enterprise Features](ENTERPRISE_FEATURES.md) - Implementation details  
- [Future Enhancements](FUTURE_ENHANCEMENTS.md) - Planned improvements
- [Migration Plan](migration_plan.md) - Utility migration guide
- [Project Status](PROJECT_STATUS.md) - Complete implementation status

## Troubleshooting

### Webhook Validation Errors
- Check `WEBHOOK_CLIENT_STATE` matches in:
  - Environment variables
  - Existing subscriptions
  - Webhook validator

### Attachments Not Downloading
- Verify `Mail.Read` permission
- Check Graph API token scope
- Review attachment downloader logs

### Retry Not Working
- Confirm connection error (not 4xx/5xx)
- Check retry handler logs
- Verify 3 attempts with backoff

### Processing Logs Missing
- Check `logs/processing/` directory
- Verify write permissions
- Review error logs

## Support & Maintenance

### Regular Tasks
- **Monitor**: Check Render logs daily
- **Subscriptions**: Automatically renewed every 12 hours
- **Logs**: Archived manually (or set up rotation)

### Updates
- Update dependencies: `pip install -r requirements.txt --upgrade`
- Test before deploying
- Monitor logs post-deployment

## Security

- Client credentials flow (no user passwords)
- Client state validation on all notifications
- HTTPS only
- Secrets in environment variables (never in code)
- Isolated utility APIs

## Performance

- Concurrent processing: 25 parallel API calls
- Batch processing: 10 emails per batch
- Average latency: <5 seconds per email
- Retry overhead: ~14 seconds max (3 retries)

## License

Internal use only.

## Contact

Project maintained by IT Operations team.

---

**Version**: 1.0.0  
**Last Updated**: 2025-12-22  
**Status**: Production Ready
