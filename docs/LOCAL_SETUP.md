# Local Development Setup Guide

Step-by-step guide to run the Email Webhook System on your local Windows machine.

---

## Overview

**What you'll do:**
1. Verify Python installation
2. Install dependencies
3. Configure environment variables
4. Start the application
5. Test all endpoints

**Time Required:** ~10 minutes

---

## Step 1: Verify Python Installation

### Check Python Version

```powershell
# Open PowerShell and run:
python --version

# Should show: Python 3.10.x or higher
```

**If Python is not installed:**
- Download from [python.org](https://www.python.org/downloads/windows/)
- Install with "Add Python to PATH" checked
- Restart PowerShell

---

## Step 2: Install Dependencies

### Navigate to Project Directory

```powershell
cd C:\Webhook_mail\Webhook_
```

### Install Required Packages

```powershell
# Install all dependencies
pip install -r requirements.txt

# This will install:
# - fastapi
# - uvicorn
# - aiohttp
# - python-dotenv
# - pydantic
```

**Verify installation:**
```powershell
pip list | Select-String "fastapi|uvicorn|aiohttp"
```

---

## Step 3: Configure Environment

### Check Your .env File

Open `C:\Webhook_mail\Webhook_\.env` and verify it has:

```env
# Microsoft Graph API Credentials
TENANT_ID=your-tenant-id
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret

# Webhook Configuration (HTTP for local)
WEBHOOK_URL=http://localhost:8000/webhook
WEBHOOK_CLIENT_STATE=dev-secret-123

# Admin API Token
ADMIN_TOKEN=dev-admin-123

# Logging
LOG_LEVEL=DEBUG
PORT=8000
```

**Important for local development:**
- ✅ `WEBHOOK_URL` should be `http://localhost:8000/webhook`
- ✅ `LOG_LEVEL` should be `DEBUG` for detailed logs
- ✅ Tokens can be simple for local testing

### Verify Configuration File

```powershell
# Check if config file exists
Test-Path C:\Webhook_mail\Webhook_\config\utility_rules.json

# Should return: True
```

---

## Step 4: Start the Application

### Method 1: Direct Python (Recommended for Testing)

```powershell
# Navigate to project directory
cd C:\Webhook_mail\Webhook_

# Start the application
python main.py
```

**Expected output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Keep this window open!** The application is now running.

### Method 2: Using Uvicorn Directly

```powershell
cd C:\Webhook_mail\Webhook_
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# --reload: Auto-restart on code changes (useful for development)
```

---

## Step 5: Test the Application

### Open a NEW PowerShell window (keep the app running in the first one)

### Test 1: Health Check

```powershell
# Test health endpoint
Invoke-WebRequest -Uri http://localhost:8000/health

# Expected response:
# StatusCode: 200
# Content: {"status":"healthy",...}
```

### Test 2: API Documentation

Open your browser and go to:
```
http://localhost:8000/docs
```

You should see the **Swagger UI** with all available endpoints:
- webhook
- testing
- management

### Test 3: Test Endpoints

In the browser at `http://localhost:8000/docs`:

1. **Authorize:**
   - Click the **Authorize** button (top right)
   - Enter your `ADMIN_TOKEN` (from .env, e.g., `dev-admin-123`)
   - Click **Authorize**

2. **Test List Utilities:**
   - Expand `GET /api/utilities/`
   - Click **Try it out**
   - Click **Execute**
   - Should return list of configured utilities

3. **Test Subscriptions:**
   - Expand `GET /test/subscriptions`
   - Click **Try it out**
   - Click **Execute**
   - Should return list of active Microsoft Graph subscriptions

### Test 4: PowerShell API Test

```powershell
# Test with authorization header
$headers = @{
    "X-Admin-Token" = "dev-admin-123"
}

Invoke-WebRequest -Uri http://localhost:8000/api/utilities/ -Headers $headers

# Should return list of utilities
```

---

## Step 6: View Logs

### Real-time Logs

In the PowerShell window where the app is running, you'll see real-time logs:

```
INFO:     127.0.0.1:xxxxx - "GET /health HTTP/1.1" 200 OK
DEBUG:    Returning cached utility configurations
```

### Log Files

```powershell
# View application logs
Get-Content C:\Webhook_mail\Webhook_\logs\app.log -Tail 50

# Watch logs in real-time
Get-Content C:\Webhook_mail\Webhook_\logs\app.log -Tail 50 -Wait
```

---

## Step 7: Test Webhook (Optional)

### Create a Test Subscription

1. Go to `http://localhost:8000/docs`
2. Authorize with your admin token
3. Expand `POST /test/create-subscription`
4. Click **Try it out**
5. Enter:
   - `mailbox`: Your email address (e.g., `it.ops@babajishivram.com`)
   - `folder`: `Inbox`
6. Click **Execute**

**Note:** This will only work if:
- Your Microsoft Graph credentials are valid
- The mailbox exists in your organization
- You have proper permissions

### Send Test Email

Send an email to the monitored mailbox and watch the logs for webhook notifications.

---

## Common Issues & Solutions

### Issue 1: Port 8000 Already in Use

**Error:**
```
OSError: [WinError 10048] Only one usage of each socket address is normally permitted
```

**Solution:**
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace <PID> with actual PID)
taskkill /PID <PID> /F

# Or use a different port in .env
# PORT=8001
```

### Issue 2: Module Not Found

**Error:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```powershell
# Reinstall dependencies
pip install -r requirements.txt
```

### Issue 3: 401 Unauthorized from Graph API

**Error:**
```
Failed to get access token: 401 Unauthorized
```

**Solution:**
```powershell
# Verify your .env credentials
Get-Content .env | Select-String "TENANT_ID|CLIENT_ID|CLIENT_SECRET"

# Check Azure Portal:
# - App Registration exists
# - Client secret is valid (not expired)
# - Correct Tenant ID and Client ID
```

### Issue 4: Config File Not Found

**Error:**
```
FileNotFoundError: config/utility_rules.json
```

**Solution:**
```powershell
# Check if file exists
Test-Path C:\Webhook_mail\Webhook_\config\utility_rules.json

# If missing, create from example
Copy-Item config\utility_rules_examples.json config\utility_rules.json
```

---

## Stopping the Application

### In the PowerShell window where the app is running:

Press `Ctrl + C`

**Expected output:**
```
INFO:     Shutting down
INFO:     Finished server process
```

---

## Development Workflow

### Making Code Changes

1. **Edit code** in your IDE
2. **Stop the app** (`Ctrl + C`)
3. **Restart the app** (`python main.py`)
4. **Test changes** at `http://localhost:8000/docs`

**OR** use auto-reload:
```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
# Changes will auto-restart the server
```

### Testing Changes

```powershell
# Test health endpoint
Invoke-WebRequest -Uri http://localhost:8000/health

# Test API docs
Start-Process http://localhost:8000/docs
```

---

## Local vs Production Differences

| Aspect | Local | Production |
|--------|-------|------------|
| URL | `http://localhost:8000` | `https://webhook.yourdomain.com` |
| Host | `127.0.0.1` | `127.0.0.1` (behind IIS) |
| HTTPS | No | Yes (via IIS) |
| Tokens | Simple OK | Strong required |
| Logging | `DEBUG` | `INFO` |
| Auto-start | Manual | Windows Service |

---

## Next Steps

Once local testing is complete:

1. ✅ Application runs without errors
2. ✅ Health check returns 200 OK
3. ✅ API documentation accessible
4. ✅ Can list utilities
5. ✅ Can create subscriptions (if Graph API configured)
6. 🔄 Ready for production deployment

**Then proceed to:** `docs/DEPLOYMENT.md` for production setup

---

## Quick Reference

### Start Application
```powershell
cd C:\Webhook_mail\Webhook_
python main.py
```

### Test Endpoints
- **Health:** `http://localhost:8000/health`
- **API Docs:** `http://localhost:8000/docs`
- **Utilities:** `http://localhost:8000/api/utilities/`

### View Logs
```powershell
Get-Content logs\app.log -Tail 50 -Wait
```

### Stop Application
Press `Ctrl + C` in the running PowerShell window

---

## Checklist

Before moving to production, verify:

- [ ] Python 3.10+ installed
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured with valid credentials
- [ ] Application starts without errors
- [ ] Health check returns 200 OK
- [ ] API documentation accessible at `/docs`
- [ ] Can authenticate with admin token
- [ ] Can list utilities via API
- [ ] Logs are being written
- [ ] Can stop and restart application cleanly

---

## Support

**Local URL:** `http://localhost:8000`  
**API Docs:** `http://localhost:8000/docs`  
**Logs:** `C:\Webhook_mail\Webhook_\logs\app.log`

For production deployment, see: `docs/DEPLOYMENT.md`
