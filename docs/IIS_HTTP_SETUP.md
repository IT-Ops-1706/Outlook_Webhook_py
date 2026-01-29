# IIS Setup Guide - HTTP Only (Simple Start)

Quick guide to host the application on IIS with HTTP. HTTPS can be added later.

---

## Prerequisites

- ✅ IIS installed
- ✅ URL Rewrite Module installed
- ✅ Application Request Routing (ARR) installed
- ✅ Python installed

---

## Step 1: Install Application as Windows Service

### 1.1 Download NSSM

Download NSSM from [nssm.cc](https://nssm.cc/download) and extract to `C:\nssm`

### 1.2 Install Python App as Service

```powershell
# Navigate to project
cd C:\Webhook_mail\Webhook_

# Create logs directory
New-Item -Path "logs" -ItemType Directory -Force

# Install service
C:\nssm\nssm.exe install EmailWebhook "C:\Python310\python.exe" "C:\Webhook_mail\Webhook_\main.py"

# Configure service
C:\nssm\nssm.exe set EmailWebhook AppDirectory "C:\Webhook_mail\Webhook_"
C:\nssm\nssm.exe set EmailWebhook DisplayName "Email Webhook Service"
C:\nssm\nssm.exe set EmailWebhook Start SERVICE_AUTO_START

# Set up logging
C:\nssm\nssm.exe set EmailWebhook AppStdout "C:\Webhook_mail\Webhook_\logs\service-output.log"
C:\nssm\nssm.exe set EmailWebhook AppStderr "C:\Webhook_mail\Webhook_\logs\service-error.log"

# Auto-restart on failure
C:\nssm\nssm.exe set EmailWebhook AppExit Default Restart
C:\nssm\nssm.exe set EmailWebhook AppRestartDelay 5000

# Start service
C:\nssm\nssm.exe start EmailWebhook
```

### 1.3 Verify Service is Running

```powershell
# Check service status
Get-Service EmailWebhook

# Should show: Running

# Check if listening on port 8000
netstat -ano | findstr :8000

# Should show: TCP 127.0.0.1:8000

# Test directly
Invoke-WebRequest -Uri http://localhost:8000/health
```

---

## Step 2: Configure IIS

### 2.1 Enable ARR Proxy

1. Open **IIS Manager**
2. Click on **server name** (root level, not a site)
3. Double-click **Application Request Routing Cache**
4. Click **Server Proxy Settings** (right panel)
5. ✅ Check **Enable proxy**
6. Click **Apply**

### 2.2 Create Website Directory

```powershell
# Create website directory
New-Item -Path "C:\inetpub\wwwroot\webhook" -ItemType Directory -Force

# Copy web.config
Copy-Item C:\Webhook_mail\Webhook_\web.config C:\inetpub\wwwroot\webhook\web.config
```

### 2.3 Update web.config for HTTP Only

Edit `C:\inetpub\wwwroot\webhook\web.config` and **remove** the HTTPS redirect rule:
`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <rewrite>
            <rules>
                <!-- Reverse Proxy to Python App -->
                <rule name="Reverse Proxy to FastAPI" stopProcessing="true">
                    <match url="(.*)" />
                    <action type="Rewrite" url="http://localhost:8000/{R:1}" />
                    <serverVariables>
                        <set name="HTTP_X_FORWARDED_FOR" value="{REMOTE_ADDR}" />
                    </serverVariables>
                </rule>
            </rules>
        </rewrite>
        
        <!-- Security Headers -->
        <httpProtocol>
            <customHeaders>
                <add name="X-Content-Type-Options" value="nosniff" />
                <add name="X-Frame-Options" value="DENY" />
            </customHeaders>
        </httpProtocol>
        
        <!-- Request Limits (50MB for attachments) -->
        <security>
            <requestFiltering>
                <requestLimits maxAllowedContentLength="52428800" />
            </requestFiltering>
        </security>
    </system.webServer>
</configuration>
```

### 2.4 Create IIS Website

1. Open **IIS Manager**
2. Right-click **Sites** → **Add Website**
3. Configure:
   - **Site name:** `EmailWebhook`
   - **Physical path:** `C:\inetpub\wwwroot\webhook`
   - **Binding:**
     - Type: `http`
     - IP Address: `All Unassigned`
     - Port: `80`
     - Host name: Leave blank (or use `localhost` for local testing)
4. Click **OK**

---

## Step 3: Configure Firewall (Optional)

Only needed if accessing from other machines:

```powershell
# Allow HTTP on port 80
New-NetFirewallRule -DisplayName "HTTP Inbound" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
```

---

## Step 4: Test the Setup

### Test 1: Direct Python App

```powershell
# Test Python app directly
Invoke-WebRequest -Uri http://localhost:8000/health

# Should return: 200 OK
```

### Test 2: Through IIS

```powershell
# Test through IIS
Invoke-WebRequest -Uri http://localhost/health

# Should return: 200 OK
```

### Test 3: API Documentation

Open browser:
```
http://localhost/docs
```

You should see the Swagger UI with all endpoints.

### Test 4: Test API Endpoints

```powershell
# Test utilities endpoint
$headers = @{
    "X-Admin-Token" = "dev-admin-123"  # Use your ADMIN_TOKEN from .env
}

Invoke-WebRequest -Uri http://localhost/api/utilities/ -Headers $headers
```

---

## Step 5: Access from Other Machines (Optional)

If you want to access from other computers on your network:

### Find Your IP Address

```powershell
# Get your local IP
ipconfig | Select-String "IPv4"

# Example output: 192.168.1.100
```

### Update IIS Binding

1. IIS Manager → Select **EmailWebhook** site
2. **Bindings** → Select HTTP binding → **Edit**
3. Change:
   - IP Address: `All Unassigned`
   - Host name: Leave blank
4. Click **OK**

### Access from Other Machines

```
http://YOUR-IP-ADDRESS/health
http://YOUR-IP-ADDRESS/docs
```

Example: `http://192.168.1.100/docs`

---

## Troubleshooting

### Issue 1: Service Won't Start

```powershell
# Check error logs
Get-Content C:\Webhook_mail\Webhook_\logs\service-error.log -Tail 50

# Common fixes:
# 1. Wrong Python path - verify Python location
where.exe python

# 2. Missing dependencies
cd C:\Webhook_mail\Webhook_
pip install -r requirements.txt
```

### Issue 2: IIS Shows 502 Bad Gateway

```powershell
# 1. Verify service is running
Get-Service EmailWebhook

# 2. Check if port 8000 is listening
netstat -ano | findstr :8000

# 3. Test direct connection
Invoke-WebRequest -Uri http://localhost:8000/health

# 4. Restart both
Restart-Service EmailWebhook
iisreset
```

### Issue 3: Can't Access from Other Machines

```powershell
# 1. Check firewall
Get-NetFirewallRule -DisplayName "HTTP Inbound"

# 2. Verify IIS binding
Get-WebBinding -Name "EmailWebhook"

# 3. Test locally first
Invoke-WebRequest -Uri http://localhost/health
```

### Issue 4: Port 8000 Already in Use

```powershell
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill the process (replace <PID>)
taskkill /PID <PID> /F

# Or change port in .env
# PORT=8001
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

# View logs
Get-Content C:\Webhook_mail\Webhook_\logs\service-output.log -Tail 50 -Wait
```

---

## Architecture

```
Browser/Client (HTTP)
    ↓
IIS (Port 80)
    ↓
Reverse Proxy (web.config)
    ↓
Python App (127.0.0.1:8000)
    ↓
Microsoft Graph API
```

---

## Quick Reference

### URLs
- **Local:** `http://localhost/`
- **Health:** `http://localhost/health`
- **API Docs:** `http://localhost/docs`
- **Utilities:** `http://localhost/api/utilities/`

### Important Paths
- Application: `C:\Webhook_mail\Webhook_\`
- IIS Site: `C:\inetpub\wwwroot\webhook\`
- web.config: `C:\inetpub\wwwroot\webhook\web.config`
- Logs: `C:\Webhook_mail\Webhook_\logs\`

### Commands
```powershell
# Restart everything
Restart-Service EmailWebhook
iisreset

# Check status
Get-Service EmailWebhook
netstat -ano | findstr :8000

# View logs
Get-Content C:\Webhook_mail\Webhook_\logs\service-output.log -Tail 50
```

---

## Checklist

- [ ] NSSM downloaded and extracted
- [ ] Python app installed as Windows Service
- [ ] Service is running (Status: Running)
- [ ] Port 8000 is listening
- [ ] ARR proxy enabled in IIS
- [ ] Website directory created
- [ ] web.config copied and configured (HTTP only)
- [ ] IIS website created with HTTP binding
- [ ] Direct test works (`http://localhost:8000/health`)
- [ ] IIS test works (`http://localhost/health`)
- [ ] API docs accessible (`http://localhost/docs`)
- [ ] Can authenticate and call API endpoints

---

## Next Steps

Once HTTP is working:

1. ✅ Application accessible via IIS on HTTP
2. ✅ Service auto-starts on boot
3. ✅ All endpoints working
4. 🔄 Test with real webhook notifications
5. 🔄 Add HTTPS (see DEPLOYMENT.md)
6. 🔄 Configure domain name
7. 🔄 Update webhook URL in .env

---

## Adding HTTPS Later

When ready for HTTPS:

1. Get SSL certificate
2. Add HTTPS binding in IIS
3. Update web.config to add HTTPS redirect
4. Update .env with HTTPS webhook URL
5. Recreate subscriptions

See `docs/DEPLOYMENT.md` for full HTTPS setup.
