from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
import requests
import os
from dotenv import load_dotenv
from typing import Optional
import uvicorn

load_dotenv()

app = FastAPI(title="Outlook Webhook Server")

# Configuration
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
TENANT_ID = os.getenv('TENANT_ID')
USER_EMAIL = os.getenv('USER_EMAIL')

def get_access_token():
    """Get access token using client credentials flow"""
    try:
        token_url = f'https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token'
        
        data = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'scope': 'https://graph.microsoft.com/.default',
            'grant_type': 'client_credentials'
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        return token_data['access_token']
    
    except Exception as e:
        print(f"Error getting access token: {e}")
        raise HTTPException(status_code=500, detail=f"Token error: {str(e)}")

def get_latest_emails(user_email: str, top: int = 10):
    """Fetch latest emails for a user"""
    try:
        token = get_access_token()
        
        url = f'https://graph.microsoft.com/v1.0/users/{user_email}/messages'
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        params = {
            '$top': top,
            '$orderby': 'receivedDateTime DESC',
            '$select': 'id,subject,from,receivedDateTime,bodyPreview,isRead,hasAttachments'
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        return response.json()['value']
    
    except Exception as e:
        print(f"Error fetching emails: {e}")
        raise HTTPException(status_code=500, detail=f"Email fetch error: {str(e)}")

def get_email_details(user_email: str, message_id: str):
    """Get detailed information for a specific email"""
    try:
        token = get_access_token()
        
        url = f'https://graph.microsoft.com/v1.0/users/{user_email}/messages/{message_id}'
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()
    
    except Exception as e:
        print(f"Error fetching email details: {e}")
        raise HTTPException(status_code=500, detail=f"Email details error: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Outlook Webhook Server",
        "endpoints": {
            "health": "/health",
            "latest_emails": "/emails/latest",
            "email_details": "/emails/{message_id}",
            "webhook": "/webhook"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/webhook")
async def webhook_notification(
    request: Request,
    validationToken: Optional[str] = Query(None)
):
    """Handle webhook notifications from Microsoft Graph"""
    
    # Validation token challenge (first time setup)
    if validationToken:
        print(f"Received validation token: {validationToken}")
        return PlainTextResponse(content=validationToken, status_code=200)
    
    # Handle actual notification
    try:
        data = await request.json()
        print(f"Received notification: {data}")
        
        # Process notifications
        if 'value' in data:
            for notification in data['value']:
                resource = notification.get('resource')
                change_type = notification.get('changeType')
                
                print(f"Change type: {change_type}")
                print(f"Resource: {resource}")
                
                # Fetch the actual email details
                if resource:
                    # Extract message ID from resource path
                    # Format: users/{user}/messages/{messageId}
                    parts = resource.split('/')
                    if len(parts) >= 4:
                        message_id = parts[-1]
                        try:
                            email_details = get_email_details(USER_EMAIL, message_id)
                            print(f"New email subject: {email_details.get('subject')}")
                            print(f"From: {email_details.get('from', {}).get('emailAddress', {}).get('address')}")
                        except Exception as e:
                            print(f"Error fetching email details: {e}")
        
        return {"status": "success"}
    
    except Exception as e:
        print(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/emails/latest")
async def fetch_latest_emails(
    top: int = Query(10, ge=1, le=50),
    user_email: Optional[str] = Query(None)
):
    """Manually fetch latest emails"""
    try:
        email = user_email or USER_EMAIL
        emails = get_latest_emails(email, top)
        
        return {
            "success": True,
            "count": len(emails),
            "emails": emails
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/emails/{message_id}")
async def fetch_email_details(
    message_id: str,
    user_email: Optional[str] = Query(None)
):
    """Fetch details of a specific email"""
    try:
        email = user_email or USER_EMAIL
        email_data = get_email_details(email, message_id)
        
        return {
            "success": True,
            "email": email_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("Starting Outlook Webhook Server with FastAPI...")
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)