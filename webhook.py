from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse
from typing import Optional
from .services import get_email_details, USER_EMAIL

router = APIRouter()

@router.post("/webhook")
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
