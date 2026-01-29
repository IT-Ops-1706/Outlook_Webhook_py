# Production Deployment Guide - Windows Server with IIS

Quick deployment guide for production server with IIS already configured.

---

## Prerequisites ✅

You should already have:
- ✅ Windows Server with IIS installed
- ✅ URL Rewrite Module installed
- ✅ Application Request Routing (ARR) installed
- ✅ Domain name pointing to server
- ✅ Ports 80 and 443 open

---

## Step 1: Prepare Application Files

### 1.1 Copy Application to Server

```powershell
# Create application directory
New-Item -Path "C:\WebhookApp" -ItemType Directory -Force
cd C:\WebhookApp

# Copy your application files here
# (From your development machine: C:\Webhook_mail\Webhook_\)
```

### 1.2 Install Python (if not already installed)

Download Python 3.10+ from [python.org](https://www.python.org/downloads/windows/)

**Installation options:**
- ✅ Add Python to PATH
- ✅ Install for all users
- Location: `C:\Python310`

Verify:
```powershell
python --version
pip --version
```

### 1.3 Set Up Virtual Environment

```powershell
cd C:\WebhookApp

# Create virtual environment
python -m venv venv

# Activate
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2: Configure Environment

### 2.1 Create Production .env File

Create `C:\WebhookApp\.env`:

```env
# Microsoft Graph API (same as local)
TENANT_ID=your-tenant-id
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret

# Webhook Configuration (HTTPS!)
WEBHOOK_URL=https://webhook.yourdomain.com/webhook

# Security Tokens (generate new)
WEBHOOK_CLIENT_STATE=generate-strong-token
ADMIN_TOKEN=generate-strong-token

# Production Settings
LOG_LEVEL=INFO
PORT=8000
```

### 2.2 Generate Secure Tokens

```powershell
# Generate CLIENT_STATE
python -c "import secrets; print('WEBHOOK_CLIENT_STATE=' + secrets.token_urlsafe(32))"

# Generate ADMIN_TOKEN
python -c "import secrets; print('ADMIN_TOKEN=' + secrets.token_urlsafe(32))"

# Copy these to .env file
```

### 2.3 Test Application

```powershell
cd C:\WebhookApp
.\venv\Scripts\Activate.ps1
python main.py

# Should start on http://127.0.0.1:8000
# Test: http://localhost:8000/health
```

Press `Ctrl+C` when verified.

---

## Step 3: Configure IIS

### 3.1 Enable ARR Proxy

1. Open **IIS Manager**
2. Click on **server name** (root level)
3. Double-click **Application Request Routing Cache**
4. Click **Server Proxy Settings** (right panel)
5. ✅ Check **Enable proxy**
6. Click **Apply**

### 3.2 Create IIS Website

1. In IIS Manager, right-click **Sites** → **Add Website**
2. Configure:
   - **Site name:** `EmailWebhook`
   - **Physical path:** `C:\inetpub\wwwroot\webhook`
   - **Binding:**
     - Type: `http`
     - IP: `All Unassigned`
     - Port: `80`
     - Host name: `webhook.yourdomain.com`
3. Click **OK**

### 3.3 Create Website Directory

```powershell
# Create directory
New-Item -Path "C:\inetpub\wwwroot\webhook" -ItemType Directory -Force

# Copy web.config
Copy-Item C:\WebhookApp\web.config C:\inetpub\wwwroot\webhook\web.config
```

### 3.4 Verify web.config

Ensure `C:\inetpub\wwwroot\webhook\web.config` contains:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <rewrite>
            <rules>
                <!-- HTTP to HTTPS -->
                <rule name="HTTP to HTTPS redirect" stopProcessing="true">
                    <match url="(.*)" />
                    <conditions>
                        <add input="{HTTPS}" pattern="off" ignoreCase="true" />
                    </conditions>
                    <action type="Redirect" url="https://{HTTP_HOST}/{R:1}" redirectType="Permanent" />
                </rule>
                
                <!-- Reverse Proxy -->
                <rule name="Reverse Proxy to FastAPI" stopProcessing="true">
                    <match url="(.*)" />
                    <action type="Rewrite" url="http://localhost:8000/{R:1}" />
                    <serverVariables>
                        <set name="HTTP_X_FORWARDED_PROTO" value="https" />
                        <set name="HTTP_X_FORWARDED_FOR" value="{REMOTE_ADDR}" />
                    </serverVariables>
                </rule>
            </rules>
        </rewrite>
        
        <!-- Security Headers -->
        <httpProtocol>
            <customHeaders>
                <add name="Strict-Transport-Security" value="max-age=31536000" />
                <add name="X-Content-Type-Options" value="nosniff" />
                <add name="X-Frame-Options" value="DENY" />
            </customHeaders>
        </httpProtocol>
    </system.webServer>
</configuration>
```

---

## Step 4: SSL Certificate Setup

### Option A: Commercial SSL Certificate

1. **Generate Certificate Request:**
   - IIS Manager → Server Certificates → Create Certificate Request
   - Common Name: `webhook.yourdomain.com`
   - Save CSR file

2. **Submit to Certificate Provider:**
   - Submit CSR to GoDaddy, Namecheap, etc.
   - Download certificate files

3. **Install Certificate:**
   - IIS Manager → Server Certificates → Complete Certificate Request
   - Select downloaded certificate
   - Friendly name: `webhook.yourdomain.com`

### Option B: Let's Encrypt (Free)

```powershell
# Download win-acme
# From: https://www.win-acme.com/

# Extract to C:\win-acme
cd C:\win-acme

# Run as Administrator
.\wacs.exe

# Follow prompts:
# - N: Create new certificate
# - 2: Manual input
# - Domain: webhook.yourdomain.com
# - 1: HTTP validation
# - 2: IIS
# - Select your site: EmailWebhook
```

### Option C: Self-Signed (Testing Only)

```powershell
# Generate certificate
New-SelfSignedCertificate `
    -DnsName "webhook.yourdomain.com" `
    -CertStoreLocation "cert:\LocalMachine\My" `
    -NotAfter (Get-Date).AddYears(2)
```

### 4.2 Add HTTPS Binding

1. IIS Manager → Select **EmailWebhook** site
2. **Bindings** → **Add**
3. Configure:
   - Type: `https`
   - IP: `All Unassigned`
   - Port: `443`
   - Host name: `webhook.yourdomain.com`
   - SSL certificate: Select your certificate
4. Click **OK**

---

## Step 5: Windows Service Setup

### 5.1 Download NSSM

Download from [nssm.cc](https://nssm.cc/download) and extract to `C:\nssm`

### 5.2 Install Service

```powershell
# Create logs directory
New-Item -Path "C:\WebhookApp\logs" -ItemType Directory -Force

# Install service
C:\nssm\nssm.exe install EmailWebhook "C:\WebhookApp\venv\Scripts\python.exe" "C:\WebhookApp\main.py"

# Configure service
C:\nssm\nssm.exe set EmailWebhook AppDirectory "C:\WebhookApp"
C:\nssm\nssm.exe set EmailWebhook DisplayName "Email Webhook Service"
C:\nssm\nssm.exe set EmailWebhook Description "Microsoft Graph Email Webhook Processing"
C:\nssm\nssm.exe set EmailWebhook Start SERVICE_AUTO_START

# Configure logging
C:\nssm\nssm.exe set EmailWebhook AppStdout "C:\WebhookApp\logs\service-output.log"
C:\nssm\nssm.exe set EmailWebhook AppStderr "C:\WebhookApp\logs\service-error.log"

# Auto-restart on failure
C:\nssm\nssm.exe set EmailWebhook AppExit Default Restart
C:\nssm\nssm.exe set EmailWebhook AppRestartDelay 5000

# Start service
C:\nssm\nssm.exe start EmailWebhook
```

### 5.3 Verify Service

```powershell
# Check service status
Get-Service EmailWebhook

# Should show: Running

# Check if listening on port 8000
netstat -ano | findstr :8000

# View logs
Get-Content C:\WebhookApp\logs\service-output.log -Tail 50
```

---

## Step 6: Firewall Configuration

```powershell
# Allow HTTP (port 80)
New-NetFirewallRule -DisplayName "HTTP Inbound" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow

# Allow HTTPS (port 443)
New-NetFirewallRule -DisplayName "HTTPS Inbound" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow

# Verify rules
Get-NetFirewallRule -DisplayName "*HTTP*" | Select-Object DisplayName, Enabled
```

---

## Step 7: Testing & Verification

### 7.1 Test Python App Directly

```powershell
# Test local connection
Invoke-WebRequest -Uri http://localhost:8000/health

# Expected: 200 OK with health status
```

### 7.2 Test HTTP (Should Redirect)

```powershell
# Test HTTP redirect
Invoke-WebRequest -Uri http://webhook.yourdomain.com/health -MaximumRedirection 0

# Expected: 301 Moved Permanently
```

### 7.3 Test HTTPS

```powershell
# Test HTTPS endpoint
Invoke-WebRequest -Uri https://webhook.yourdomain.com/health

# Expected: 200 OK
```

### 7.4 Verify Subscriptions

1. Open browser: `https://webhook.yourdomain.com/docs`
2. Click **Authorize** → Enter your `ADMIN_TOKEN`
3. Test endpoint: `GET /test/subscriptions`
4. Verify `notificationUrl` shows HTTPS:
   ```json
   {
     "notificationUrl": "https://webhook.yourdomain.com/webhook"
   }
   ```

### 7.5 Test Webhook

Send a test email to monitored mailbox and check logs:

```powershell
Get-Content C:\WebhookApp\logs\service-output.log -Tail 100 -Wait
```

---

## Troubleshooting

### Service Won't Start

```powershell
# Check error logs
Get-Content C:\WebhookApp\logs\service-error.log -Tail 50

# Run manually to see errors
cd C:\WebhookApp
.\venv\Scripts\Activate.ps1
python main.py
```

**Common issues:**
- Missing dependencies: `pip install -r requirements.txt`
- Wrong Python path: Verify `C:\WebhookApp\venv\Scripts\python.exe` exists
- Port already in use: Check if another app is using port 8000

### IIS 502 Bad Gateway

```powershell
# 1. Verify service is running
Get-Service EmailWebhook

# 2. Check if port 8000 is listening
netstat -ano | findstr :8000

# 3. Test direct connection
Invoke-WebRequest -Uri http://localhost:8000/health

# 4. Restart both services
Restart-Service EmailWebhook
iisreset
```

### SSL Certificate Errors

```powershell
# Check installed certificates
Get-ChildItem -Path cert:\LocalMachine\My

# Verify IIS binding
Get-WebBinding -Name "EmailWebhook"

# Check certificate expiry
Get-ChildItem -Path cert:\LocalMachine\My | Where-Object {$_.Subject -like "*webhook*"} | Select-Object Subject, NotAfter
```

### Subscriptions Using HTTP Instead of HTTPS

```powershell
# 1. Verify .env has HTTPS URL
Get-Content C:\WebhookApp\.env | Select-String "WEBHOOK_URL"

# 2. Restart service
Restart-Service EmailWebhook

# 3. Delete old subscriptions and recreate
# Go to: https://webhook.yourdomain.com/docs
# Call: POST /test/cleanup-subscriptions
```

### 401 Unauthorized from Graph API

```powershell
# Verify credentials
Get-Content C:\WebhookApp\.env | Select-String "TENANT_ID|CLIENT_ID|CLIENT_SECRET"

# Test authentication
cd C:\WebhookApp
.\venv\Scripts\Activate.ps1
python -c "from services.graph_service import graph_service; import asyncio; print(asyncio.run(graph_service.get_access_token())[:50])"
```

---

## Service Management

```powershell
# Start service
Start-Service EmailWebhook

# Stop service
Stop-Service EmailWebhook

# Restart service
Restart-Service EmailWebhook

# Check status
Get-Service EmailWebhook

# View real-time logs
Get-Content C:\WebhookApp\logs\service-output.log -Tail 100 -Wait
```

---

## Architecture

```
Internet (HTTPS:443)
    ↓
IIS (web.config)
    ├─ HTTP → HTTPS redirect
    ├─ Security headers
    └─ Reverse proxy
        ↓
Python App (127.0.0.1:8000)
    ↓
Microsoft Graph API
```

---

## Important Files & Paths

| Component | Path |
|-----------|------|
| Application | `C:\WebhookApp\` |
| Environment | `C:\WebhookApp\.env` |
| Virtual Env | `C:\WebhookApp\venv\` |
| Logs | `C:\WebhookApp\logs\` |
| IIS Site | `C:\inetpub\wwwroot\webhook\` |
| web.config | `C:\inetpub\wwwroot\webhook\web.config` |
| NSSM | `C:\nssm\nssm.exe` |

---

## Post-Deployment Checklist

- [ ] Python app runs on `127.0.0.1:8000` (localhost only)
- [ ] Windows Service auto-starts on boot
- [ ] IIS site created with HTTP and HTTPS bindings
- [ ] SSL certificate installed and valid
- [ ] HTTP redirects to HTTPS
- [ ] `web.config` configured correctly
- [ ] Firewall allows ports 80 and 443
- [ ] `.env` has HTTPS webhook URL
- [ ] Health check returns 200 OK
- [ ] Subscriptions created with HTTPS URL
- [ ] Test email triggers webhook successfully
- [ ] Logs are being written
- [ ] `.env` backup stored securely

---

## Monitoring

### Health Check

```powershell
# Manual check
Invoke-WebRequest -Uri https://webhook.yourdomain.com/health

# Scheduled check (create script)
# C:\WebhookApp\health-check.ps1
```

### View Logs

```powershell
# Application logs
Get-Content C:\WebhookApp\logs\service-output.log -Tail 100 -Wait

# IIS logs
Get-Content C:\inetpub\logs\LogFiles\W3SVC*\*.log -Tail 100 -Wait
```

---

## Quick Reference

### URLs
- **Health:** `https://webhook.yourdomain.com/health`
- **API Docs:** `https://webhook.yourdomain.com/docs`
- **Admin API:** `https://webhook.yourdomain.com/api/utilities`

### Commands
```powershell
# Restart everything
Restart-Service EmailWebhook
iisreset

# Check status
Get-Service EmailWebhook
netstat -ano | findstr :8000

# View logs
Get-Content C:\WebhookApp\logs\service-output.log -Tail 50
```

---

## Next Steps

1. ✅ Application deployed and running
2. ✅ HTTPS configured with SSL
3. ✅ Service auto-starts on boot
4. 🔄 Monitor logs for first 24 hours
5. 🔄 Set up automated health checks
6. 🔄 Configure log rotation
7. 🔄 Document admin credentials securely
8. 🔄 Schedule regular backups of `.env` and `config/`

---

## Support

**Health Check:** `https://webhook.yourdomain.com/health`  
**API Documentation:** `https://webhook.yourdomain.com/docs`  
**Logs:** `C:\WebhookApp\logs\`
