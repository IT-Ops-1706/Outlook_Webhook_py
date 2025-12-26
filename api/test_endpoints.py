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

@router.get("/test/config")
async def view_config(auth: str = Depends(verify_bearer_token)):
    """View loaded utility configuration (for debugging)"""
    try:
        from services.config_service import config_service
        import asyncio
        
        utilities = await config_service.get_all_utilities()
        
        return {
            "count": len(utilities),
            "utilities": [
                {
                    "id": u.id,
                    "name": u.name,
                    "enabled": u.enabled,
                    "endpoint_url": u.endpoint.get('url'),
                    "has_auth": 'auth' in u.endpoint,
                    "mailboxes": [m['address'] for m in u.subscriptions.get('mailboxes', [])],
                    "filter_type": "advanced" if 'condition_groups' in u.pre_filters else "legacy"
                }
                for u in utilities
            ]
        }
    
    except Exception as e:
        logger.error(f"Error fetching config: {e}")
        return {"error": str(e)}

@router.get("/test/employee-details")
async def test_employee_details(
    email: str = "it.ops@babajishivram.com",
    auth: str = Depends(verify_bearer_token)
):
    """Test endpoint to fetch employee details from Microsoft 365"""
    try:
        from services.graph_service import graph_service
        
        logger.info(f"Fetching employee details for: {email}")
        
        # Fetch employee details
        employee_data = graph_service.fetch_user_details(email)
        
        if employee_data:
            return {
                "success": True,
                "email": email,
                "employee_details": employee_data,
                "message": "Employee data enrichment working!"
            }
        else:
            return {
                "success": False,
                "email": email,
                "employee_details": None,
                "message": "Employee not found or not an internal user"
            }
    
    except Exception as e:
        logger.error(f"Error fetching employee details: {e}")
        return {
            "success": False,
            "error": str(e),
            "email": email
        }

@router.post("/test/cleanup-subscriptions")
async def cleanup_subscriptions(auth: str = Depends(verify_bearer_token)):
    """Delete all webhook subscriptions and recreate them (fixes duplicates)"""
    try:
        logger.info("Starting subscription cleanup...")
        
        # Get all current subscriptions
        current_subs = subscription_manager.list_subscriptions()
        logger.info(f"Found {len(current_subs)} existing subscriptions")
        
        # Delete all
        deleted_count = 0
        for sub in current_subs:
            try:
                subscription_manager.delete_subscription(sub['id'])
                deleted_count += 1
                logger.info(f"Deleted subscription: {sub['id']}")
            except Exception as e:
                logger.error(f"Failed to delete subscription {sub['id']}: {e}")
        
        logger.info(f"Deleted {deleted_count} subscriptions")
        
        # Wait a moment for Microsoft to process
        import asyncio
        await asyncio.sleep(2)
        
        # Recreate fresh subscriptions
        from services.config_service import config_service
        utilities = await config_service.get_all_utilities()
        
        new_subs = subscription_manager.ensure_all_subscriptions(utilities)
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "recreated_count": len(new_subs),
            "subscriptions": [
                {
                    "id": sub.get('id'),
                    "resource": sub.get('resource'),
                    "expirationDateTime": sub.get('expirationDateTime')
                }
                for sub in new_subs
            ],
            "message": f"✅ Cleaned up {deleted_count} old subscriptions, created {len(new_subs)} fresh ones"
        }
    
    except Exception as e:
        logger.error(f"Error cleaning up subscriptions: {e}")
        return {
            "success": False,
            "error": str(e)
        }

