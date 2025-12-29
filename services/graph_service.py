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
                'id,subject,body,uniqueBody,bodyPreview,from,toRecipients,ccRecipients,bccRecipients,'
                'receivedDateTime,sentDateTime,hasAttachments,'
                'internetMessageId,conversationId,conversationIndex,parentFolderId'
            ),
            # Expand attachments to get metadata (name, size, type) but NOT content
            '$expand': 'attachments($select=id,name,size,contentType,isInline)'
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
    
    def fetch_user_details(self, email_address: str) -> Optional[dict]:
        """
        Fetch user details from Microsoft Graph (department, office, location)
        
        Only fetches for users in your organization (babajishivram.com).
        External users will return None.
        
        Returns:
            dict with keys: department, office_location, city, country, job_title
            None if user not found or external user
        """
        # Check if user is from your organization
        if not email_address.lower().endswith('@babajishivram.com'):
            logger.debug(f"Skipping employee data fetch for external user: {email_address}")
            return None
        
        token = self.get_access_token()
        
        url = f'https://graph.microsoft.com/v1.0/users/{email_address}'
        
        params = {
            '$select': 'department,officeLocation,city,country,jobTitle,displayName,mail'
        }
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            # User not found in organization
            if response.status_code == 404:
                logger.debug(f"User {email_address} not found in organization")
                return None
            
            response.raise_for_status()
            
            user_data = response.json()
            logger.debug(f"Fetched user details for: {email_address}")
            
            return {
                'email': user_data.get('mail', email_address),
                'display_name': user_data.get('displayName', ''),
                'department': user_data.get('department', ''),
                'office_location': user_data.get('officeLocation', ''),
                'city': user_data.get('city', ''),
                'country': user_data.get('country', ''),
                'job_title': user_data.get('jobTitle', '')
            }
        
        except Exception as e:
            logger.error(f"Failed to fetch user details for {email_address}: {e}")
            return None

# Global instance
graph_service = GraphService()
