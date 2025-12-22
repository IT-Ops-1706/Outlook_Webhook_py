import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
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
            logger.info(f"Renewed subscription {subscription_id}")
            return subscription
        
        except Exception as e:
            logger.error(f"Failed to renew subscription: {e}")
            raise

# Global instance
subscription_manager = SubscriptionManager()
