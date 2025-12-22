import requests
import time
import logging
from typing import Optional
import config

logger = logging.getLogger(__name__)

class GraphService:
    """Microsoft Graph API service"""
    
    def __init__(self):
        self.client_id = config.CLIENT_ID
        self.client_secret = config.CLIENT_SECRET
        self.tenant_id = config.TENANT_ID
        self._token = None
        self._token_expiry = 0
    
    def get_access_token(self) -> str:
        """Get OAuth access token with caching"""
        current_time = time.time()
        
        # Return cached token if still valid
        if self._token and current_time < self._token_expiry:
            return self._token
        
        logger.info("Fetching new access token from Microsoft")
        
        token_url = f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token'
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://graph.microsoft.com/.default',
            'grant_type': 'client_credentials'
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self._token = token_data['access_token']
            # Cache for 50 minutes (tokens valid for 60 minutes)
            self._token_expiry = current_time + 3000
            
            logger.info("Access token obtained successfully")
            return self._token
        
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            raise
    
    def fetch_email(self, mailbox: str, message_id: str) -> dict:
        """Fetch full email metadata from Microsoft Graph"""
        token = self.get_access_token()
        
        url = f'https://graph.microsoft.com/v1.0/users/{mailbox}/messages/{message_id}'
        
        params = {
            '$select': (
                'id,subject,body,bodyPreview,from,toRecipients,ccRecipients,bccRecipients,'
                'receivedDateTime,sentDateTime,hasAttachments,attachments,'
                'internetMessageId,conversationId,conversationIndex,parentFolderId'
            )
        }
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            email_data = response.json()
            logger.debug(f"Fetched email: {email_data.get('subject', 'No subject')[:50]}")
            return email_data
        
        except Exception as e:
            logger.error(f"Failed to fetch email {message_id}: {e}")
            raise

# Global instance
graph_service = GraphService()
