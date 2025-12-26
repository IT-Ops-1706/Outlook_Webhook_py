# Utility Migration & Creation Plan

## Overview

**Goal:** Convert existing utilities to webhook-based architecture

**Approach:**
1. **Migrate 2 existing utilities** - Remove scheduler/Graph, keep processing logic
2. **Create 1 new utility** - Build from scratch

---

## Phase 2: Add Utility API Authentication (Do This First) 🔐

### 2.1 Update Dispatcher

**File:** `routing/dispatcher.py`

**Changes needed:**
```python
async def _forward_to_utility(email: EmailMetadata, utility: UtilityConfig):
    """POST to utility API with rate limiting, retry, and logging"""
    async with semaphore:
        start_time = time.time()
        
        # Prepare headers
        headers = {'Content-Type': 'application/json'}
        
        # Add authentication if configured
        if utility.endpoint.get('auth'):
            auth = utility.endpoint['auth']
            if auth['type'] == 'bearer':
                headers['Authorization'] = f"Bearer {auth['token']}"
            elif auth['type'] == 'api_key':
                headers['X-API-Key'] = auth['token']
        
        # Log call start
        processing_logger.log_utility_call_start(
            email.internet_message_id,
            utility.name,
            utility.endpoint['url']
        )
        
        async def call_utility():
            timeout = aiohttp.ClientTimeout(total=utility.timeout)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    utility.endpoint['url'],
                    json=email.to_dict(),
                    headers=headers,  # ← Include auth headers
                    timeout=timeout
                ) as response:
                    response.raise_for_status()
                    
                    try:
                        return await response.json()
                    except:
                        return {"status": "success", "response": await response.text()}
        
        # ... rest of code
```

**Checklist:**
- [ ] Add auth header logic to `_forward_to_utility()`
- [ ] Test with mock utility API
- [ ] Commit changes

---

## Phase 3: Migrate Existing Utilities

### Utility Migration Strategy

**What to REMOVE:**
- ❌ Scheduler (APScheduler, cron jobs)
- ❌ Microsoft Graph connection
- ❌ Email fetching logic
- ❌ Pre-filtering logic (moved to webhook)
- ❌ Polling/checking for new emails

**What to KEEP:**
- ✅ Core processing logic
- ✅ Business rules
- ✅ Database operations
- ✅ External API calls
- ✅ Error handling

**What to ADD:**
- ✅ FastAPI endpoint to receive webhook data
- ✅ Bearer token authentication
- ✅ Input validation (Pydantic models)
- ✅ Health check endpoint

---

### Migration Template

**Before (Existing Utility):**
```python
# Old structure
import schedule
from services import graph_service

def check_emails():
    # Fetch emails from Graph API
    emails = graph_service.fetch_emails(mailbox)
    
    # Filter emails
    for email in emails:
        if matches_criteria(email):
            # Process email
            process_email(email)

# Schedule to run every 5 minutes
schedule.every(5).minutes.do(check_emails)
```

**After (Webhook-based):**
```python
# New structure
from fastapi import FastAPI, Depends
from utils.auth import verify_bearer_token

app = FastAPI()

@app.post("/process")
async def process_email(
    email_data: dict,
    auth: str = Depends(verify_bearer_token)
):
    """Receive email from webhook and process"""
    
    # No fetching needed - data already provided
    # No filtering needed - webhook already filtered
    
    # Just process the email
    result = process_email(email_data)
    
    return result

def process_email(email_data: dict):
    # YOUR EXISTING PROCESSING LOGIC HERE
    # (Keep this part unchanged)
    pass
```

---

## Utility 1: [Existing Utility Name] - Migration

### Step 1: Identify Components

**Current structure analysis:**
- [ ] List all files in existing utility
- [ ] Identify scheduler code (to remove)
- [ ] Identify Graph API code (to remove)
- [ ] Identify pre-filter code (to remove)
- [ ] Identify core processing logic (to keep)
- [ ] Identify database/API calls (to keep)

### Step 2: Create New Structure

```
Utility_1_Migrated/
├── main.py                 # FastAPI app
├── config.py              # Environment variables
├── models/
│   └── email_input.py     # Pydantic model for webhook data
├── services/
│   └── processor.py       # YOUR EXISTING PROCESSING LOGIC (moved here)
├── utils/
│   └── auth.py           # Bearer token authentication
├── .env
├── .env.example
├── requirements.txt
└── README.md
```

### Step 3: Migration Checklist

**Setup:**
- [ ] Create new directory
- [ ] Copy existing processing logic to `services/processor.py`
- [ ] Create `main.py` with FastAPI app
- [ ] Create `utils/auth.py` for authentication
- [ ] Create `models/email_input.py` for input validation

**Remove old code:**
- [ ] Delete scheduler imports (`schedule`, `APScheduler`, etc.)
- [ ] Delete Graph API imports (`msal`, `requests` for Graph)
- [ ] Delete email fetching functions
- [ ] Delete pre-filtering functions
- [ ] Delete polling/checking logic

**Add new code:**
- [ ] Create `POST /process` endpoint
- [ ] Add Bearer token authentication
- [ ] Add input validation (Pydantic)
- [ ] Add error handling
- [ ] Add logging

**Update processing logic:**
- [ ] Change input from Graph API format to webhook format
- [ ] Update email data access (use webhook JSON structure)
- [ ] Keep all business logic unchanged
- [ ] Keep database operations unchanged
- [ ] Keep external API calls unchanged

**Testing:**
- [ ] Test with sample webhook data
- [ ] Test authentication
- [ ] Test error cases
- [ ] Test with real webhook

**Deployment:**
- [ ] Create `requirements.txt`
- [ ] Create `render.yaml`
- [ ] Deploy to Render
- [ ] Add environment variables
- [ ] Test deployed endpoint

**Integration:**
- [ ] Update webhook `utility_rules.json`
- [ ] Add pre-filters (moved from utility)
- [ ] Test end-to-end flow

---

## Utility 2: [Existing Utility Name] - Migration

### Follow same steps as Utility 1

- [ ] Analyze current structure
- [ ] Create new structure
- [ ] Remove scheduler/Graph code
- [ ] Add FastAPI endpoint
- [ ] Migrate processing logic
- [ ] Test and deploy
- [ ] Integrate with webhook

---

## Utility 3: [New Utility Name] - Create from Scratch

### Step 1: Requirements

**Define:**
- [ ] What emails should it process? (pre-filters)
- [ ] What should it do with the email? (processing logic)
- [ ] What data should it store? (database schema)
- [ ] What external APIs does it call? (integrations)

### Step 2: Implementation

**Project setup:**
- [ ] Create new directory
- [ ] Initialize FastAPI project
- [ ] Create project structure

**Core implementation:**
- [ ] Create authentication middleware
- [ ] Create input validation models
- [ ] Implement processing logic
- [ ] Implement database operations
- [ ] Implement external API calls
- [ ] Add error handling and logging

**Endpoints:**
- [ ] `POST /process` - Main processing endpoint
- [ ] `GET /health` - Health check
- [ ] Optional: Query endpoints for data retrieval

**Testing:**
- [ ] Unit tests for processing logic
- [ ] Integration tests with mock data
- [ ] End-to-end tests with webhook

**Deployment:**
- [ ] Deploy to Render
- [ ] Configure environment variables
- [ ] Test deployed endpoint

**Integration:**
- [ ] Update webhook `utility_rules.json`
- [ ] Configure pre-filters
- [ ] Test end-to-end flow

---

## Migration Code Examples

### Example 1: Remove Scheduler

**Before:**
```python
# old_utility.py
import schedule
import time

def check_emails():
    emails = fetch_from_graph()
    for email in emails:
        process(email)

schedule.every(5).minutes.do(check_emails)

while True:
    schedule.run_pending()
    time.sleep(1)
```

**After:**
```python
# main.py
from fastapi import FastAPI

app = FastAPI()

@app.post("/process")
async def process_email(email_data: dict):
    # Webhook calls this automatically
    # No scheduling needed!
    return process(email_data)
```

---

### Example 2: Remove Graph API Fetching

**Before:**
```python
# old_utility.py
from services import graph_service

def fetch_emails():
    token = graph_service.get_access_token()
    response = requests.get(
        f'https://graph.microsoft.com/v1.0/users/{mailbox}/messages',
        headers={'Authorization': f'Bearer {token}'}
    )
    return response.json()['value']
```

**After:**
```python
# main.py
@app.post("/process")
async def process_email(email_data: dict):
    # Email data already provided by webhook
    # No need to fetch!
    subject = email_data['subject']
    body = email_data['body_content']
    attachments = email_data['attachments']
    
    # Process directly
    return process(subject, body, attachments)
```

---

### Example 3: Move Pre-filters to Webhook Config

**Before (in utility):**
```python
# old_utility.py
def should_process(email):
    # Pre-filtering in utility
    if email['from'] != 'vendor@example.com':
        return False
    if 'Invoice' not in email['subject']:
        return False
    if not email['hasAttachments']:
        return False
    return True

def check_emails():
    emails = fetch_emails()
    for email in emails:
        if should_process(email):  # Filter here
            process(email)
```

**After (in webhook config):**
```json
// utility_rules.json
{
  "id": "utility_1",
  "pre_filters": {
    "match_logic": "AND",
    "sender": {
      "exact": "vendor@example.com"
    },
    "subject": {
      "contains": ["Invoice"]
    },
    "attachments": {
      "required": true
    }
  }
}
```

```python
# main.py (utility)
@app.post("/process")
async def process_email(email_data: dict):
    # No filtering needed - webhook already filtered!
    # Just process
    return process(email_data)
```

---

### Example 4: Keep Processing Logic Unchanged

**Before:**
```python
# old_utility.py
def process_invoice(email):
    # Extract invoice number
    invoice_num = extract_invoice_number(email['subject'])
    
    # Check if exists
    if not invoice_exists(invoice_num):
        return {"status": "not_found"}
    
    # Save to database
    save_invoice(invoice_num, email)
    
    # Send notification
    send_notification(invoice_num)
    
    return {"status": "success"}
```

**After:**
```python
# services/processor.py (same logic!)
def process_invoice(email_data):
    # Extract invoice number
    invoice_num = extract_invoice_number(email_data['subject'])
    
    # Check if exists
    if not invoice_exists(invoice_num):
        return {"status": "not_found"}
    
    # Save to database
    save_invoice(invoice_num, email_data)
    
    # Send notification
    send_notification(invoice_num)
    
    return {"status": "success"}

# main.py (just calls it)
@app.post("/process")
async def process_email(email_data: dict):
    return process_invoice(email_data)
```

---

## Webhook Data Format (What Utilities Receive)

```json
{
  "message_id": "AAMkADUw...",
  "internet_message_id": "<unique-id@example.com>",
  "conversation_id": "AAQkAGU...",
  "conversation_index": "AdqlC1mQ...",
  
  "subject": "Invoice ID_12345",
  "body_preview": "Dear Team...",
  "body_content": "<html>...</html>",
  "body_type": "html",
  
  "from_address": "vendor@example.com",
  "from_name": "Vendor Name",
  "to_recipients": [{"address": "it.ops@...", "name": "IT Ops"}],
  "cc_recipients": [],
  "bcc_recipients": [],
  
  "received_datetime": "2025-12-23T17:00:00",
  "sent_datetime": "2025-12-23T16:59:00",
  
  "has_attachments": true,
  "attachments": [
    {
      "id": "AAMkADUw...",
      "name": "invoice.pdf",
      "content_type": "application/pdf",
      "size": 45678,
      "is_inline": false,
      "content": "JVBERi0xLjQK..."  // Base64 encoded
    }
  ],
  
  "mailbox": "it.ops@babajishivram.com",
  "folder": "Inbox",
  "direction": "received"
}
```

---

## Updated Task Checklist

### Phase 2: Utility Authentication (1 hour)
- [ ] Update `routing/dispatcher.py` with auth headers
- [ ] Test with mock utility
- [ ] Commit and deploy

### Phase 3: Migrate Utility 1 (3-4 hours)
- [ ] Analyze existing code
- [ ] Create new project structure
- [ ] Remove scheduler/Graph code
- [ ] Add FastAPI endpoint
- [ ] Add authentication
- [ ] Migrate processing logic
- [ ] Test locally
- [ ] Deploy to Render
- [ ] Update webhook config
- [ ] Test end-to-end

### Phase 4: Migrate Utility 2 (3-4 hours)
- [ ] Follow same steps as Utility 1
- [ ] Deploy and test

### Phase 5: Create Utility 3 (4-6 hours)
- [ ] Define requirements
- [ ] Create from scratch
- [ ] Implement processing logic
- [ ] Deploy and test

### Phase 6: Production Testing (2 hours)
- [ ] Test all 3 utilities end-to-end
- [ ] Monitor logs
- [ ] Verify no errors
- [ ] Performance testing

---

## Summary

**Total estimated time:** 13-17 hours

**Breakdown:**
- Utility auth: 1 hour
- Migrate Utility 1: 3-4 hours
- Migrate Utility 2: 3-4 hours
- Create Utility 3: 4-6 hours
- Testing: 2 hours

**Key points:**
- ✅ Keep all business logic
- ❌ Remove scheduler and Graph API
- ✅ Add FastAPI endpoint
- ✅ Move pre-filters to webhook config
- ✅ Add authentication

**Ready to start Phase 2 (Utility Authentication)?**
