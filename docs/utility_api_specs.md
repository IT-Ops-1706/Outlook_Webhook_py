# Utility API Specifications & Architecture

## 1. JSON Format Sent to Utilities

### Complete Email Payload

**What webhook sends to each utility:**

```json
{
  "message_id": "AAMkADUwZTYyODA5LTY4YTUtNDNiMy05MGFiLTI1MGM5NGRlYzAzNABGAAAD88uwkSoLOE2bo6UUuqFRdQcAy5fS0fLzwkS5XpZLsgAijwAAAgEMAAAAy5fS0fLzwkS5XpZLsgAijwABCgTz1AAAAA==",
  "internet_message_id": "<CAKmF+OoVxN7Bw_unique_id@mail.gmail.com>",
  "conversation_id": "AAQkAGU3ZjQwNzg5LWNiYzItNDQ4Zi1hMWE3LWJlNzYwZjk1YjRkMQAQANxVz...",
  "conversation_index": "AdqlC1mQiNxVz5Kj5UKVqRLbGw==",
  
  "subject": "Invoice ID_12345 - Payment Required",
  "body_preview": "Dear Team, Please find attached the invoice for processing. Invoice Number: ID_12345, Amount: $5,000",
  "body_content": "<html><body><p>Dear Team,</p><p>Please find attached the invoice for processing.</p><p>Invoice Number: ID_12345</p><p>Amount: $5,000</p><p>Best regards,<br>Vendor Name</p></body></html>",
  "body_type": "html",
  
  "from_address": "vendor@example.com",
  "from_name": "Vendor Name",
  "to_recipients": [
    {
      "address": "it.ops@babajishivram.com",
      "name": "IT Operations"
    }
  ],
  "cc_recipients": [
    {
      "address": "finance@babajishivram.com",
      "name": "Finance Team"
    }
  ],
  "bcc_recipients": [],
  
  "received_datetime": "2025-12-23T09:45:12.000000",
  "sent_datetime": "2025-12-23T09:44:58.000000",
  
  "has_attachments": true,
  "attachment_metadata": [
    {
      "id": "AAMkADUwZTYy...ESABAAjKOJPnYqSUOSVqjr9dKNVw==",
      "name": "INVOICE_ID_12345.pdf",
      "size": 45678,
      "content_type": "application/pdf",
      "is_inline": false
    }
  ],
  "attachments": [
    {
      "id": "AAMkADUwZTYy...ESABAAjKOJPnYqSUOSVqjr9dKNVw==",
      "name": "INVOICE_ID_12345.pdf",
      "content_type": "application/pdf",
      "size": 45678,
      "is_inline": false,
      "content_bytes": "JVBERi0xLjQKJeLjz9MKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMi...",
      "content": "JVBERi0xLjQKJeLjz9MKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMi..."
    }
  ],
  
  "mailbox": "it.ops@babajishivram.com",
  "folder": "Inbox",
  "direction": "received"
}
```

### Field Descriptions

| Field | Type | Description | Always Present |
|-------|------|-------------|----------------|
| `message_id` | string | Microsoft Graph message ID | ✅ |
| `internet_message_id` | string | RFC 822 message ID (unique) | ✅ |
| `conversation_id` | string | Thread/conversation ID | ✅ |
| `conversation_index` | string | Thread position indicator | ✅ |
| `subject` | string | Email subject | ✅ |
| `body_preview` | string | First ~200 chars of body | ✅ |
| `body_content` | string | Full email body (HTML or text) | ✅ |
| `body_type` | string | "html" or "text" | ✅ |
| `from_address` | string | Sender email | ✅ |
| `from_name` | string | Sender display name | ⚠️ (can be empty) |
| `to_recipients` | array | List of TO recipients | ✅ |
| `cc_recipients` | array | List of CC recipients | ✅ |
| `bcc_recipients` | array | List of BCC recipients | ✅ |
| `received_datetime` | string | When email was received (ISO) | ✅ |
| `sent_datetime` | string | When email was sent (ISO) | ✅ |
| `has_attachments` | boolean | Whether email has attachments | ✅ |
| `attachment_metadata` | array | Attachment names/sizes (always) | ✅ |
| `attachments` | array | Full attachment content (if matched) | ⚠️ (only if pre-filter matched) |
| `mailbox` | string | Which mailbox received email | ✅ |
| `folder` | string | Which folder (Inbox, Sent Items) | ✅ |
| `direction` | string | "received" or "sent" | ✅ |

---

## 2. Request Frequency & Patterns

### How Often Utilities Receive Requests

**Pattern:** Event-driven (real-time)

```
Email arrives → Webhook notified (< 1 second)
              ↓
Webhook processes (< 5 seconds)
              ↓
Utility called (immediately if matched)
```

### Frequency Examples

**Low volume (10 emails/hour):**
```
Utility receives: ~10 requests/hour
Average: 1 request every 6 minutes
Peak: 3-5 requests in 1 minute (burst)
```

**Medium volume (100 emails/hour):**
```
Utility receives: ~100 requests/hour
Average: 1.67 requests/minute
Peak: 10-20 requests in 1 minute (burst)
```

**High volume (1000 emails/hour):**
```
Utility receives: ~1000 requests/hour
Average: 16.67 requests/minute
Peak: 50-100 requests in 1 minute (burst)
```

### Burst Patterns

**Typical scenario:**
```
00:00 - 00:05: 0 requests (quiet)
00:05 - 00:06: 25 requests (burst - someone sent batch)
00:06 - 00:15: 5 requests (normal)
00:15 - 00:16: 15 requests (burst - another batch)
```

**Why bursts happen:**
- Someone sends multiple emails at once
- Scheduled emails released
- Email server delays then releases queue
- Multiple people reply to same thread

---

## 3. Concurrency Requirements

### Utility Must Handle Concurrent Requests

**Why:**
- Webhook dispatcher sends requests concurrently (up to 25 parallel)
- Multiple emails can arrive simultaneously
- Bursts can send 10-50 requests in seconds

### Async/Await Architecture (Required) ✅

**FastAPI handles this automatically:**

```python
from fastapi import FastAPI
import asyncio

app = FastAPI()

@app.post("/process")
async def process_email(email_data: dict):
    """
    FastAPI automatically handles concurrency!
    
    Each request runs in its own async task.
    Can handle 100+ concurrent requests.
    """
    
    # Your processing logic
    result = await process_attachment(email_data)
    
    return result

async def process_attachment(email_data: dict):
    """Use async for I/O operations"""
    
    # Async HTTP calls
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
    
    # Async database operations
    await db.save(data)
    
    return result
```

**Key points:**
- ✅ Use `async def` for endpoints
- ✅ Use `await` for I/O operations (HTTP, database, file)
- ✅ FastAPI handles concurrency automatically
- ✅ No need for threading or multiprocessing

---

## 4. Utility Architecture Requirements

### 4.1 Async HTTP Client (Required)

**Use connection pooling:**

```python
import httpx

# Global client with connection pooling
http_client = httpx.AsyncClient(
    timeout=30.0,
    limits=httpx.Limits(
        max_connections=100,      # Max total connections
        max_keepalive_connections=20  # Reuse connections
    )
)

@app.post("/process")
async def process_email(email_data: dict):
    # Reuse connection pool
    response = await http_client.post(url, json=data)
    return response.json()

@app.on_event("shutdown")
async def shutdown():
    # Close client on shutdown
    await http_client.aclose()
```

**Benefits:**
- ✅ Reuses TCP connections (faster)
- ✅ Handles concurrent requests efficiently
- ✅ Prevents connection exhaustion

---

### 4.2 Database Connection Pooling (If Using Database)

**Example with asyncpg (PostgreSQL):**

```python
import asyncpg

# Global connection pool
db_pool = None

@app.on_event("startup")
async def startup():
    global db_pool
    db_pool = await asyncpg.create_pool(
        host='localhost',
        database='mydb',
        user='user',
        password='password',
        min_size=10,    # Min connections
        max_size=50     # Max connections
    )

@app.post("/process")
async def process_email(email_data: dict):
    # Get connection from pool
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO emails VALUES ($1, $2)",
            email_data['message_id'],
            email_data['subject']
        )
    
    return {"status": "success"}

@app.on_event("shutdown")
async def shutdown():
    await db_pool.close()
```

---

### 4.3 Rate Limiting (Optional but Recommended)

**Protect your utility from overload:**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/process")
@limiter.limit("100/minute")  # Max 100 requests per minute
async def process_email(email_data: dict):
    # Process email
    return result
```

**Or use token bucket:**

```python
import asyncio
from collections import deque
import time

class RateLimiter:
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
    
    async def acquire(self):
        now = time.time()
        
        # Remove old requests
        while self.requests and self.requests[0] < now - self.time_window:
            self.requests.popleft()
        
        # Check if limit reached
        if len(self.requests) >= self.max_requests:
            wait_time = self.requests[0] + self.time_window - now
            await asyncio.sleep(wait_time)
        
        self.requests.append(now)

# Global rate limiter
rate_limiter = RateLimiter(max_requests=100, time_window=60)

@app.post("/process")
async def process_email(email_data: dict):
    # Wait if rate limit reached
    await rate_limiter.acquire()
    
    # Process email
    return result
```

---

### 4.4 Error Handling & Retry Logic

**Utility should handle errors gracefully:**

```python
@app.post("/process")
async def process_email(email_data: dict):
    try:
        # Process email
        result = await process_attachment(email_data)
        return {"status": "success", "result": result}
    
    except httpx.HTTPStatusError as e:
        # HTTP error from external API
        logger.error(f"HTTP error: {e}")
        return {
            "status": "error",
            "error_type": "http_error",
            "message": str(e),
            "retryable": e.response.status_code >= 500  # Retry on 5xx
        }
    
    except asyncpg.PostgresError as e:
        # Database error
        logger.error(f"Database error: {e}")
        return {
            "status": "error",
            "error_type": "database_error",
            "message": str(e),
            "retryable": True
        }
    
    except Exception as e:
        # Unknown error
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            "status": "error",
            "error_type": "unknown",
            "message": str(e),
            "retryable": False
        }
```

**Webhook dispatcher will retry if:**
- Connection error (3 attempts)
- Timeout (3 attempts)
- 5xx status code (3 attempts)

**Webhook dispatcher will NOT retry if:**
- 4xx status code (client error)
- 200-299 status code (success)

---

### 4.5 Logging & Monitoring

**Structured logging:**

```python
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

@app.post("/process")
async def process_email(email_data: dict):
    start_time = datetime.utcnow()
    
    # Log request received
    logger.info(json.dumps({
        "event": "request_received",
        "message_id": email_data['message_id'],
        "subject": email_data['subject'][:50],
        "from": email_data['from_address'],
        "timestamp": start_time.isoformat()
    }))
    
    try:
        result = await process_attachment(email_data)
        
        # Log success
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.info(json.dumps({
            "event": "request_completed",
            "message_id": email_data['message_id'],
            "status": "success",
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        return result
    
    except Exception as e:
        # Log error
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.error(json.dumps({
            "event": "request_failed",
            "message_id": email_data['message_id'],
            "error": str(e),
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        raise
```

---

### 4.6 Health Check & Metrics

**Health check endpoint:**

```python
@app.get("/health")
async def health_check():
    """
    Health check for monitoring
    
    Returns:
    - status: healthy/unhealthy
    - dependencies: status of external services
    - metrics: request counts, errors, etc.
    """
    
    # Check database connection
    db_healthy = await check_database()
    
    # Check external API
    api_healthy = await check_external_api()
    
    # Get metrics
    metrics = {
        "requests_total": request_counter.get(),
        "requests_success": success_counter.get(),
        "requests_error": error_counter.get(),
        "avg_response_time_ms": avg_response_time.get()
    }
    
    status = "healthy" if (db_healthy and api_healthy) else "unhealthy"
    
    return {
        "status": status,
        "dependencies": {
            "database": "healthy" if db_healthy else "unhealthy",
            "external_api": "healthy" if api_healthy else "unhealthy"
        },
        "metrics": metrics,
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

## 5. Performance Requirements

### Response Time Targets

| Priority | Target | Max Acceptable |
|----------|--------|----------------|
| High | < 500ms | < 2 seconds |
| Medium | < 2 seconds | < 5 seconds |
| Low | < 5 seconds | < 30 seconds |

**Webhook timeout:** 30 seconds (configurable)

### Concurrency Targets

| Load | Concurrent Requests | Target Throughput |
|------|---------------------|-------------------|
| Low | 1-5 | 10 req/min |
| Medium | 5-25 | 100 req/min |
| High | 25-100 | 1000 req/min |

### Resource Limits

**Memory:**
- Baseline: 128 MB
- Per request: ~5-10 MB
- Max: 512 MB (Render free tier)

**CPU:**
- Baseline: 0.1 CPU
- Per request: 0.01-0.05 CPU
- Max: 0.5 CPU (Render free tier)

---

## 6. Complete Utility Template

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
import httpx
import asyncio
import logging
from datetime import datetime
import json

from models.email_input import EmailInput
from utils.auth import verify_bearer_token
import config

# Configure logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="My Utility", version="1.0.0")

# Global HTTP client with connection pooling
http_client = None

# Metrics
request_counter = 0
success_counter = 0
error_counter = 0

@app.on_event("startup")
async def startup():
    """Initialize resources on startup"""
    global http_client
    
    http_client = httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20
        )
    )
    
    logger.info("Utility started successfully")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup resources on shutdown"""
    if http_client:
        await http_client.aclose()
    
    logger.info("Utility shut down")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "my_utility",
        "version": "1.0.0",
        "metrics": {
            "requests_total": request_counter,
            "requests_success": success_counter,
            "requests_error": error_counter
        }
    }

@app.post("/process")
async def process_email(
    email: EmailInput,
    auth: str = Depends(verify_bearer_token)
):
    """
    Process email from webhook
    
    Handles concurrent requests automatically.
    Uses async I/O for external calls.
    """
    global request_counter, success_counter, error_counter
    
    request_counter += 1
    start_time = datetime.utcnow()
    
    # Log request
    logger.info(json.dumps({
        "event": "request_received",
        "message_id": email.message_id,
        "subject": email.subject[:50],
        "from": email.from_address
    }))
    
    try:
        # Convert to dict
        email_dict = email.model_dump()
        
        # Process email (your logic here)
        result = await process_email_logic(email_dict)
        
        # Update metrics
        success_counter += 1
        
        # Log success
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.info(json.dumps({
            "event": "request_completed",
            "message_id": email.message_id,
            "status": "success",
            "duration_ms": duration_ms
        }))
        
        return result
    
    except Exception as e:
        # Update metrics
        error_counter += 1
        
        # Log error
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.error(json.dumps({
            "event": "request_failed",
            "message_id": email.message_id,
            "error": str(e),
            "duration_ms": duration_ms
        }))
        
        raise HTTPException(status_code=500, detail=str(e))

async def process_email_logic(email_data: dict) -> dict:
    """
    Your processing logic here
    
    Use async for I/O operations:
    - HTTP calls: await http_client.post(...)
    - Database: await db.execute(...)
    - File I/O: await aiofiles.open(...)
    """
    
    # Example: Call external API
    response = await http_client.post(
        "https://external-api.com/process",
        json=email_data
    )
    
    return response.json()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
```

---

## Summary

### JSON Format
- ✅ Complete email metadata
- ✅ Full attachment content (base64)
- ✅ Conversation threading info
- ✅ Always same structure

### Frequency
- ⚡ Real-time (< 1 second after email)
- 📊 Varies: 10-1000 emails/hour
- 💥 Bursts: 10-100 requests/minute

### Concurrency
- ✅ Use async/await (FastAPI handles it)
- ✅ Connection pooling (HTTP & database)
- ✅ Handle 25-100 concurrent requests
- ✅ No polling needed (event-driven)

### Requirements
- ✅ Async HTTP client (httpx)
- ✅ Connection pooling
- ✅ Error handling
- ✅ Structured logging
- ✅ Health check endpoint
- ⚠️ Rate limiting (optional)
- ⚠️ Metrics (optional)

**Your utility will receive requests in real-time, handle them concurrently, and respond within 30 seconds!** 🚀
