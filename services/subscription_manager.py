import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
import config
from services.graph_service import graph_service

logger = logging.getLogger(__name__)

class SubscriptionManager:
    """Manage Microsoft Graph webhook subscriptions"""
    
    def __init__(self):
        self.graph = graph_service
    
    def create_subscription(self, mailbox: str, folder: str = "Inbox") -> dict:
        """Create a new webhook subscription"""
        token = self.graph.get_access_token()
        
        # Determine resource based on folder
        if folder == "Inbox":
            resource = f'users/{mailbox}/messages'
        elif folder == "Sent Items":
            resource = f'users/{mailbox}/mailFolders/SentItems/messages'
        else:
            resource = f'users/{mailbox}/mailFolders/{folder}/messages'
        
        # Subscription expires in 3 days (max for messages)
        expiration = datetime.utcnow() + timedelta(days=2, hours=23)
        
        subscription_data = {
            'changeType': 'created',
            'notificationUrl': config.WEBHOOK_URL,
            'resource': resource,
            'expirationDateTime': expiration.isoformat() + 'Z',
            'clientState': 'SecretClientState'
        }
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                'https://graph.microsoft.com/v1.0/subscriptions',
                json=subscription_data,
                headers=headers
            )
            response.raise_for_status()
            
            subscription = response.json()
            logger.info(f"Created subscription {subscription['id']} for {mailbox}/{folder}")
            return subscription
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"Failed to create subscription: {e}")
            logger.error(f"Response: {e.response.text}")
            raise
    
    def list_subscriptions(self) -> List[dict]:
        """List all active subscriptions"""
        token = self.graph.get_access_token()
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(
                'https://graph.microsoft.com/v1.0/subscriptions',
                headers=headers
            )
            response.raise_for_status()
            
            subscriptions = response.json().get('value', [])
            logger.info(f"Found {len(subscriptions)} active subscriptions")
            return subscriptions
        
        except Exception as e:
            logger.error(f"Failed to list subscriptions: {e}")
            raise
    
    def delete_subscription(self, subscription_id: str) -> bool:
        """Delete a subscription"""
        token = self.graph.get_access_token()
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.delete(
                f'https://graph.microsoft.com/v1.0/subscriptions/{subscription_id}',
                headers=headers
            )
            response.raise_for_status()
            
            logger.info(f"Deleted subscription {subscription_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete subscription: {e}")
            raise
    
    def renew_subscription(self, subscription_id: str) -> dict:
        """Renew an existing subscription"""
        token = self.graph.get_access_token()
        
        # Extend by 3 days
        expiration = datetime.utcnow() + timedelta(days=2, hours=23)
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'expirationDateTime': expiration.isoformat() + 'Z'
        }
        
        try:
            response = requests.patch(
                f'https://graph.microsoft.com/v1.0/subscriptions/{subscription_id}',
                json=data,
                headers=headers
            )
            response.raise_for_status()
            
            subscription = response.json()
            logger.info(f"Renewed subscription {subscription_id} until {subscription['expirationDateTime']}")
            return subscription
        
        except Exception as e:
            logger.error(f"Failed to renew subscription: {e}")
            raise
    
    async def ensure_all_subscriptions(self, utilities: List) -> Dict[str, str]:
        """
        Ensure subscriptions exist for all unique mailboxes across all utilities.
        Returns dict mapping 'mailbox:folder' to subscription_id
        """
        # Collect unique mailbox/folder combinations
        needed_subscriptions: Set[tuple] = set()
        
        for utility in utilities:
            if not utility.enabled:
                continue
            
            mailboxes = utility.subscriptions.get('mailboxes', [])
            for mb in mailboxes:
                address = mb['address']
                folders = mb.get('folders', ['Inbox'])
                for folder in folders:
                    needed_subscriptions.add((address, folder))
        
        logger.info(f"Need subscriptions for {len(needed_subscriptions)} unique mailbox/folder combinations")
        
        # Get existing subscriptions
        existing = self.list_subscriptions()
        existing_map = {}
        
        for sub in existing:
            resource = sub['resource']
            # Parse resource to extract mailbox and folder
            mailbox, folder = self._parse_resource(resource)
            if mailbox and folder:
                existing_map[f"{mailbox}:{folder}"] = sub['id']
        
        # Create missing subscriptions
        subscription_map = {}
        for mailbox, folder in needed_subscriptions:
            key = f"{mailbox}:{folder}"
            
            if key in existing_map:
                logger.info(f"Subscription already exists for {key}")
                subscription_map[key] = existing_map[key]
            else:
                logger.info(f"Creating subscription for {mailbox}/{folder}")
                try:
                    sub = self.create_subscription(mailbox, folder)
                    subscription_map[key] = sub['id']
                except Exception as e:
                    logger.error(f"Failed to create subscription for {key}: {e}")
        
        return subscription_map
    
    def _parse_resource(self, resource: str) -> tuple:
        """Parse resource string to extract mailbox and folder"""
        # Format: users/{mailbox}/messages or users/{mailbox}/mailFolders/{folder}/messages
        parts = resource.split('/')
        
        if len(parts) >= 3:
            mailbox = parts[1]
            
            if 'mailFolders' in parts:
                # Extract folder name
                folder_idx = parts.index('mailFolders') + 1
                if folder_idx < len(parts):
                    folder = parts[folder_idx]
                    return mailbox, folder
            else:
                return mailbox, "Inbox"
        
        return None, None
    
    async def check_and_renew_subscriptions(self):
        """Check all subscriptions and renew those expiring soon"""
        try:
            subscriptions = self.list_subscriptions()
            
            now = datetime.utcnow()
            renewed_count = 0
            
            for sub in subscriptions:
                expiration_str = sub.get('expirationDateTime', '')
                if not expiration_str:
                    continue
                
                # Parse expiration datetime
                expiration = datetime.fromisoformat(expiration_str.replace('Z', '+00:00'))
                time_left = expiration - now
                
                # Renew if less than 24 hours left
                if time_left < timedelta(hours=24):
                    logger.info(f"Subscription {sub['id']} expires in {time_left}, renewing...")
                    try:
                        self.renew_subscription(sub['id'])
                        renewed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to renew subscription {sub['id']}: {e}")
            
            if renewed_count > 0:
                logger.info(f"Successfully renewed {renewed_count} subscriptions")
            else:
                logger.info("No subscriptions needed renewal")
        
        except Exception as e:
            logger.error(f"Error in subscription renewal check: {e}")

# Global instance
subscription_manager = SubscriptionManager()
