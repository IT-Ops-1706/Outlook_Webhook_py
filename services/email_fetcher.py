import logging
import requests
from datetime import datetime
from typing import Optional
from models.email_metadata import EmailMetadata
from services.graph_service import graph_service
from services.attachment_downloader import attachment_downloader

logger = logging.getLogger(__name__)

class EmailFetcher:
    """Simple email fetcher - fetch from Graph API, return data"""
    
    def __init__(self):
        self.graph = graph_service
        self._folder_cache = {}  # Cache folder ID -> name mappings
    
    async def fetch_email(self, notification: dict) -> Optional[EmailMetadata]:
        """Fetch email data from Microsoft Graph"""
        try:
            # Extract IDs from notification
            resource = notification.get('resource', '')
            parts = resource.split('/')
            
            if len(parts) < 4:
                logger.error(f"Invalid resource format: {resource}")
                return None
            
            mailbox_id = parts[1]
            message_id = parts[-1]
            
            # Resolve mailbox email address
            mailbox_email = await self._resolve_mailbox(mailbox_id)
            
            # Fetch email from Graph API
            email_data = self.graph.fetch_email(mailbox_id, message_id)
            
            # Resolve folder name from parentFolderId
            folder = self._get_folder_name(email_data.get('parentFolderId', ''), mailbox_email)
            
            # Parse into EmailMetadata
            return self._parse_email(email_data, mailbox_email, folder)
        
        except Exception as e:
            logger.error(f"Error fetching email: {e}", exc_info=True)
            return None
    
    async def load_attachments(self, email: EmailMetadata) -> EmailMetadata:
        """Load full attachment content"""
        if not email.has_attachments or email.attachments_loaded:
            return email
        
        try:
            attachments = await attachment_downloader.download_attachments(
                email.mailbox,
                email.message_id
            )
            email.attachments = attachments
            logger.info(f"📎 Loaded {len(attachments)} attachment(s)")
        except Exception as e:
            logger.error(f"Failed to load attachments: {e}")
            email.attachments = []
        
        return email
    
    async def _resolve_mailbox(self, mailbox_id: str) -> str:
        """Resolve mailbox UUID to email address"""
        from services.config_service import config_service
        
        utilities = await config_service.get_all_utilities()
        all_mailboxes = {}
        for utility in utilities:
            for mb in utility.subscriptions.get('mailboxes', []):
                all_mailboxes[mb['address'].lower()] = mb['address']
        
        # For single mailbox, use it directly
        if len(all_mailboxes) == 1:
            return list(all_mailboxes.values())[0]
        
        return list(all_mailboxes.values())[0] if all_mailboxes else mailbox_id
    
    def _get_folder_name(self, folder_id: str, mailbox: str) -> str:
        """Get folder display name from ID"""
        if not folder_id:
            return "Inbox"
        
        cache_key = f"{mailbox}_{folder_id}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]
        
        try:
            token = self.graph.get_access_token()
            url = f'https://graph.microsoft.com/v1.0/users/{mailbox}/mailFolders/{folder_id}'
            
            response = requests.get(url, headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            })
            
            if response.status_code == 200:
                folder_name = response.json().get('displayName', 'Inbox')
                self._folder_cache[cache_key] = folder_name
                return folder_name
        except Exception as e:
            logger.debug(f"Could not resolve folder: {e}")
        
        return "Inbox"
    
    def _parse_email(self, data: dict, mailbox: str, folder: str) -> EmailMetadata:
        """Parse Graph API response into EmailMetadata"""
        
        # Timestamps
        received_dt = None
        sent_dt = None
        if data.get('receivedDateTime'):
            received_dt = datetime.fromisoformat(data['receivedDateTime'].replace('Z', '+00:00'))
        if data.get('sentDateTime'):
            sent_dt = datetime.fromisoformat(data['sentDateTime'].replace('Z', '+00:00'))
        
        # Body - always use full body
        body_obj = data.get('body', {})
        body_content = body_obj.get('content', '')
        body_type = body_obj.get('contentType', 'html').lower()
        
        # Unique Body - new content only (from Microsoft Graph)
        unique_body_obj = data.get('uniqueBody', {})
        unique_body_content = unique_body_obj.get('content', '')
        
        # Sender
        from_obj = data.get('from', {}).get('emailAddress', {})
        
        # Recipients
        to_recipients = [
            {'address': r['emailAddress']['address'], 'name': r['emailAddress'].get('name', '')}
            for r in data.get('toRecipients', [])
        ]
        cc_recipients = [
            {'address': r['emailAddress']['address'], 'name': r['emailAddress'].get('name', '')}
            for r in data.get('ccRecipients', [])
        ]
        bcc_recipients = [
            {'address': r['emailAddress']['address'], 'name': r['emailAddress'].get('name', '')}
            for r in data.get('bccRecipients', [])
        ]
        
        # Attachment metadata (not content)
        attachment_metadata = [
            {
                'id': att.get('id', ''),
                'name': att.get('name', ''),
                'size': att.get('size', 0),
                'content_type': att.get('contentType', ''),
                'is_inline': att.get('isInline', False)
            }
            for att in data.get('attachments', [])
        ]
        
        return EmailMetadata(
            message_id=data.get('id', ''),
            internet_message_id=data.get('internetMessageId', ''),
            conversation_id=data.get('conversationId', ''),
            conversation_index=data.get('conversationIndex', ''),
            subject=data.get('subject', ''),
            body_preview=data.get('bodyPreview', ''),
            body_content=body_content,
            unique_body_content=unique_body_content,
            body_type=body_type,
            from_address=from_obj.get('address', ''),
            from_name=from_obj.get('name', ''),
            to_recipients=to_recipients,
            cc_recipients=cc_recipients,
            bcc_recipients=bcc_recipients,
            received_datetime=received_dt,
            sent_datetime=sent_dt,
            has_attachments=data.get('hasAttachments', False),
            attachment_metadata=attachment_metadata,
            attachments=[],
            mailbox=mailbox,
            folder=folder
        )

# Global instance
email_fetcher = EmailFetcher()
