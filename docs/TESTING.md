# Webhook Testing Guide

## Step 1: Email Fetching (WORKING)

You've confirmed this works:
```
http://localhost:8000/test/fetch-emails?mailbox=it.ops@babajishivram.com
```

---

## Step 2: Set Up Webhooks

### Prerequisites

IMPORTANT: Webhooks require a publicly accessible URL. You have 2 options:

#### Option A: Deploy to Render (Recommended)
1. Push code to GitHub
2. Deploy to Render
3. Get public URL (e.g., `https://your-app.onrender.com`)
4. Update `.env`: `WEBHOOK_URL=https://your-app.onrender.com/webhook`

#### Option B: Use ngrok for Local Testing
```bash
# Install ngrok: https://ngrok.com/download
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Update .env: WEBHOOK_URL=https://abc123.ngrok.io/webhook
```

---

## Step 3: Check Existing Subscriptions

```
http://localhost:8000/test/subscriptions
```

This will show all active subscriptions. You might see old ones from Render.

---

## Step 4: Create New Subscription

IMPORTANT: Only do this AFTER you have a public URL!

```
http://localhost:8000/test/create-subscription?mailbox=it.ops@babajishivram.com&folder=Inbox
```

What happens:
1. Microsoft Graph receives your subscription request
2. Microsoft sends a validation request to your webhook URL
3. Your `/webhook` endpoint must respond with the validation token
4. Subscription is created

Expected response:
```json
{
  "success": true,
  "subscription": {
    "id": "abc-123-def",
    "resource": "users/it.ops@babajishivram.com/messages",
    "expirationDateTime": "2025-12-25T18:00:00Z",
    "notificationUrl": "https://your-app.onrender.com/webhook"
  }
}
```

---

## Step 5: Test Webhook

Once subscription is created:

1. Send a test email to `it.ops@babajishivram.com`
2. Check your server logs - you should see:
   ```
   Received 1 webhook notifications
   Processing email: 'Your test subject' from sender@example.com
   Email matched utility: ...
   ```

---

## Troubleshooting

### "Subscription validation request failed"
- Your webhook URL is not publicly accessible
- Deploy to Render or use ngrok

### "403 Forbidden"
- App needs `Mail.Read` permission in Azure Portal

### "No notifications received"
- Check subscription is active: `/test/subscriptions`
- Verify webhook URL is correct in subscription
- Check server logs for errors

---

## Current Status

- Email fetching works
- Subscription creation (needs public URL)
- Webhook notifications (needs active subscription)

Next: Deploy to Render or use ngrok to get a public URL!
