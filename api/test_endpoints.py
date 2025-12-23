from fastapi import APIRouter, Depends
import logging
from services.graph_service import graph_service
from services.subscription_manager import subscription_manager
from utils.auth import verify_bearer_token

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/test/fetch-emails")
async def test_fetch_emails(
    mailbox: str = "it.ops@babajishivram.com",
    limit: int = 5,
    auth: str = Depends(verify_bearer_token)
):
    """Test endpoint to fetch latest emails from a mailbox"""
    try:
        token = graph_service.get_access_token()
        
        url = f'https://graph.microsoft.com/v1.0/users/{mailbox}/messages'
        params = {
            '$top': limit,
            '$select': 'id,subject,from,receivedDateTime,bodyPreview',
            '$orderby': 'receivedDateTime DESC'
        }
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        import requests
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        emails = response.json().get('value', [])
        
        # Format for display
        result = {
            "mailbox": mailbox,
            "count": len(emails),
            "emails": [
                {
                    "subject": email.get('subject', 'No subject'),
                    "from": email.get('from', {}).get('emailAddress', {}).get('address', 'Unknown'),
                    "received": email.get('receivedDateTime', ''),
                    "preview": email.get('bodyPreview', '')[:100]
                }
                for email in emails
            ]
        }
        
        logger.info(f"Successfully fetched {len(emails)} emails from {mailbox}")
        return result
    
    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        return {
            "error": str(e),
            "mailbox": mailbox
        }

@router.get("/test/subscriptions")
async def list_subscriptions(auth: str = Depends(verify_bearer_token)):
    """List all active webhook subscriptions"""
    try:
        subscriptions = subscription_manager.list_subscriptions()
        
        return {
            "count": len(subscriptions),
            "subscriptions": [
                {
                    "id": sub.get('id'),
                    "resource": sub.get('resource'),
                    "changeType": sub.get('changeType'),
                    "expirationDateTime": sub.get('expirationDateTime'),
                    "notificationUrl": sub.get('notificationUrl')
                }
                for sub in subscriptions
            ]
        }
    
    except Exception as e:
        logger.error(f"Error listing subscriptions: {e}")
        return {"error": str(e)}

@router.post("/test/create-subscription")
async def create_subscription(
    mailbox: str = "it.ops@babajishivram.com",
    folder: str = "Inbox",
    auth: str = Depends(verify_bearer_token)
):
    """Create a new webhook subscription"""
    try:
        subscription = subscription_manager.create_subscription(mailbox, folder)
        
        return {
            "success": True,
            "subscription": {
                "id": subscription.get('id'),
                "resource": subscription.get('resource'),
                "expirationDateTime": subscription.get('expirationDateTime'),
                "notificationUrl": subscription.get('notificationUrl')
            }
        }
    
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.delete("/test/delete-subscription/{subscription_id}")
async def delete_subscription(
    subscription_id: str,
    auth: str = Depends(verify_bearer_token)
):
    """Delete a webhook subscription"""
    try:
        subscription_manager.delete_subscription(subscription_id)
        return {"success": True, "message": f"Deleted subscription {subscription_id}"}
    
    except Exception as e:
        logger.error(f"Error deleting subscription: {e}")
        return {"success": False, "error": str(e)}

