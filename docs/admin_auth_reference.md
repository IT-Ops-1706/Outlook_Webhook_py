# Admin API Authentication - Quick Reference

## Overview

All admin/test endpoints now require Bearer token authentication for security.

**Environment Variable:** `API_BEARER_KEY`

---

## Setup

### 1. Add to .env File

```bash
# .env
API_BEARER_KEY=your-strong-random-secret-key-here
```

**Generate a strong key:**
```bash
# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Output example:
# xK7mP9nQ2wR5tY8uI1oL4aS6dF3gH0jK9mN2bV5cX8zA1qW4eR7tY0uI3oP6
```

### 2. Add to Render Environment Variables

```
Dashboard → Environment → Add Environment Variable
Key: API_BEARER_KEY
Value: xK7mP9nQ2wR5tY8uI1oL4aS6dF3gH0jK9mN2bV5cX8zA1qW4eR7tY0uI3oP6
```

---

## Protected Endpoints

All `/test/*` endpoints now require authentication:

- `GET /test/fetch-emails` - Fetch latest emails
- `GET /test/subscriptions` - List subscriptions
- `POST /test/create-subscription` - Create subscription
- `DELETE /test/delete-subscription/{id}` - Delete subscription

**Public endpoints (no auth required):**
- `POST /webhook` - Webhook notifications (uses clientState)
- `GET /health` - Health check

---

## Usage Examples

### cURL

```bash
# List subscriptions
curl -X GET https://outlook-webhook-py.onrender.com/test/subscriptions \
  -H "Authorization: Bearer xK7mP9nQ2wR5tY8uI1oL4aS6dF3gH0jK9mN2bV5cX8zA1qW4eR7tY0uI3oP6"

# Fetch emails
curl -X GET "https://outlook-webhook-py.onrender.com/test/fetch-emails?mailbox=it.ops@babajishivram.com&limit=5" \
  -H "Authorization: Bearer xK7mP9nQ2wR5tY8uI1oL4aS6dF3gH0jK9mN2bV5cX8zA1qW4eR7tY0uI3oP6"

# Create subscription
curl -X POST "https://outlook-webhook-py.onrender.com/test/create-subscription?mailbox=it.ops@babajishivram.com" \
  -H "Authorization: Bearer xK7mP9nQ2wR5tY8uI1oL4aS6dF3gH0jK9mN2bV5cX8zA1qW4eR7tY0uI3oP6"

# Delete subscription
curl -X DELETE https://outlook-webhook-py.onrender.com/test/delete-subscription/abc-123-def \
  -H "Authorization: Bearer xK7mP9nQ2wR5tY8uI1oL4aS6dF3gH0jK9mN2bV5cX8zA1qW4eR7tY0uI3oP6"
```

### Python (requests)

```python
import requests

API_URL = "https://outlook-webhook-py.onrender.com"
BEARER_TOKEN = "xK7mP9nQ2wR5tY8uI1oL4aS6dF3gH0jK9mN2bV5cX8zA1qW4eR7tY0uI3oP6"

headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}"
}

# List subscriptions
response = requests.get(f"{API_URL}/test/subscriptions", headers=headers)
print(response.json())

# Fetch emails
params = {"mailbox": "it.ops@babajishivram.com", "limit": 5}
response = requests.get(f"{API_URL}/test/fetch-emails", headers=headers, params=params)
print(response.json())
```

### JavaScript (fetch)

```javascript
const API_URL = "https://outlook-webhook-py.onrender.com";
const BEARER_TOKEN = "xK7mP9nQ2wR5tY8uI1oL4aS6dF3gH0jK9mN2bV5cX8zA1qW4eR7tY0uI3oP6";

const headers = {
    "Authorization": `Bearer ${BEARER_TOKEN}`
};

// List subscriptions
fetch(`${API_URL}/test/subscriptions`, { headers })
    .then(res => res.json())
    .then(data => console.log(data));

// Fetch emails
fetch(`${API_URL}/test/fetch-emails?mailbox=it.ops@babajishivram.com&limit=5`, { headers })
    .then(res => res.json())
    .then(data => console.log(data));
```

### Postman

1. **Create request:** `GET https://outlook-webhook-py.onrender.com/test/subscriptions`
2. **Go to Authorization tab**
3. **Type:** Bearer Token
4. **Token:** `xK7mP9nQ2wR5tY8uI1oL4aS6dF3gH0jK9mN2bV5cX8zA1qW4eR7tY0uI3oP6`
5. **Send**

---

## Error Responses

### Missing Authorization Header

```bash
curl https://outlook-webhook-py.onrender.com/test/subscriptions
```

**Response (422):**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["header", "Authorization"],
      "msg": "Field required"
    }
  ]
}
```

### Invalid Format

```bash
curl -H "Authorization: InvalidFormat" \
  https://outlook-webhook-py.onrender.com/test/subscriptions
```

**Response (401):**
```json
{
  "detail": "Invalid authorization header format. Expected: 'Bearer <token>'"
}
```

### Wrong Token

```bash
curl -H "Authorization: Bearer wrong-token" \
  https://outlook-webhook-py.onrender.com/test/subscriptions
```

**Response (401):**
```json
{
  "detail": "Unauthorized - Invalid bearer token"
}
```

### API_BEARER_KEY Not Configured

**Response (500):**
```json
{
  "detail": "Server authentication not configured"
}
```

---

## Security Best Practices

### ✅ DO

- Use strong, random tokens (32+ characters)
- Store in environment variables, never in code
- Use different tokens for dev/staging/production
- Rotate tokens periodically (every 90 days)
- Use HTTPS only (already enforced by Render)

### ❌ DON'T

- Hardcode tokens in code
- Share tokens in chat/email
- Commit tokens to Git
- Use simple/guessable tokens like "admin123"
- Reuse tokens across different services

---

## Token Rotation

When rotating tokens:

1. **Generate new token:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Update Render environment variable:**
   - Dashboard → Environment → Edit `API_BEARER_KEY`
   - Save (triggers redeploy)

3. **Update local .env:**
   ```bash
   API_BEARER_KEY=new-token-here
   ```

4. **Update any scripts/tools using the old token**

---

## Troubleshooting

### Issue: "Field required" error

**Cause:** Missing Authorization header

**Fix:**
```bash
# Add header
-H "Authorization: Bearer YOUR_TOKEN"
```

### Issue: "Invalid authorization header format"

**Cause:** Header doesn't start with "Bearer "

**Fix:**
```bash
# Correct format
Authorization: Bearer YOUR_TOKEN

# NOT
Authorization: YOUR_TOKEN
```

### Issue: "Unauthorized - Invalid bearer token"

**Cause:** Token doesn't match `API_BEARER_KEY`

**Fix:**
- Check token in .env file
- Check Render environment variables
- Ensure no extra spaces/newlines

### Issue: "Server authentication not configured"

**Cause:** `API_BEARER_KEY` not set in environment

**Fix:**
```bash
# Add to .env
API_BEARER_KEY=your-token-here

# Or set in Render dashboard
```

---

## Implementation Details

### Authentication Flow

```
1. Client sends request with Authorization header
   ↓
2. FastAPI extracts header value
   ↓
3. verify_bearer_token() dependency runs
   ↓
4. Checks if header starts with "Bearer "
   ↓
5. Extracts token (removes "Bearer " prefix)
   ↓
6. Compares with config.API_BEARER_KEY
   ↓
7a. Match → Allow request ✓
7b. No match → Return 401 ✗
```

### Code Location

- **Dependency:** [`utils/auth.py`](file:///c:/Webhook_mail/Webhook_/utils/auth.py)
- **Config:** [`config.py`](file:///c:/Webhook_mail/Webhook_/config.py)
- **Usage:** [`api/test_endpoints.py`](file:///c:/Webhook_mail/Webhook_/api/test_endpoints.py)

---

## Summary

**What:** Bearer token authentication for admin endpoints

**Why:** Prevent unauthorized access to internal APIs

**How:** Add `Authorization: Bearer <token>` header to requests

**Setup:** Set `API_BEARER_KEY` in environment variables

**Status:** ✅ Implemented and ready for use
