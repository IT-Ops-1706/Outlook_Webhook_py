# Environment Configuration Guide

Guide for configuring environment variables for local development and production deployment.

---

## Local Development (.env)

```env
# Microsoft Graph API
TENANT_ID=your-tenant-id
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret

# Webhook (HTTP for local)
WEBHOOK_URL=http://localhost:8000/webhook
WEBHOOK_CLIENT_STATE=dev-secret-123

# Admin API
ADMIN_TOKEN=dev-admin-123

# Logging
LOG_LEVEL=DEBUG
```

---

## Production (.env)

```env
# Microsoft Graph API (SAME as local)
TENANT_ID=your-tenant-id
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret

# Webhook (HTTPS for production!)
WEBHOOK_URL=https://webhook.yourdomain.com/webhook
WEBHOOK_CLIENT_STATE=xK9mP2vN8qR5tL7wY4jH6fD3sA1gZ0uB

# Admin API (strong token)
ADMIN_TOKEN=bV8nM4kP9rT2wY7jL5hF3dS6aG1zX0qC

# Logging
LOG_LEVEL=INFO
```

---

## Key Differences

| Variable | Local | Production |
|----------|-------|------------|
| `WEBHOOK_URL` | `http://localhost:8000/webhook` | `https://webhook.yourdomain.com/webhook` |
| `WEBHOOK_CLIENT_STATE` | Simple OK | **Strong random required** |
| `ADMIN_TOKEN` | Simple OK | **Strong random required** |
| `LOG_LEVEL` | `DEBUG` | `INFO` |

---

## Generate Secure Tokens

```powershell
# Generate CLIENT_STATE
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate ADMIN_TOKEN
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Migration Steps

1. **Backup local .env:**
   ```powershell
   Copy-Item .env .env.local.backup
   ```

2. **Create production .env:**
   - Copy all values from local
   - Change `WEBHOOK_URL` to HTTPS
   - Generate new strong tokens

3. **Deploy to server:**
   ```powershell
   # Copy .env to C:\WebhookApp\.env
   # Restart service
   Restart-Service EmailWebhook
   ```

4. **Verify:**
   ```powershell
   # Check WEBHOOK_URL
   python -c "import config; print(config.WEBHOOK_URL)"
   
   # Should output: https://webhook.yourdomain.com/webhook
   ```

---

## Security Best Practices

- ✅ Never commit `.env` to git
- ✅ Use strong random tokens (32+ characters) in production
- ✅ Store backup `.env` securely
- ✅ Rotate tokens every 90 days
- ❌ Never email or share `.env` in plain text

---

## Troubleshooting

**Subscriptions still using HTTP?**
```powershell
# Update .env with HTTPS URL
# Restart service
Restart-Service EmailWebhook

# Cleanup old subscriptions
# Visit: https://webhook.yourdomain.com/docs
# Call: POST /test/cleanup-subscriptions
```

**401 Unauthorized from Graph API?**
```powershell
# Verify credentials
Get-Content .env | Select-String "TENANT_ID|CLIENT_ID|CLIENT_SECRET"

# Test authentication
python -c "from services.graph_service import graph_service; import asyncio; print(asyncio.run(graph_service.get_access_token())[:50])"
```
