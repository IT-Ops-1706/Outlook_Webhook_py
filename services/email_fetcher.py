import logging
from datetime import datetime
from typing import Optional
from models.email_metadata import EmailMetadata
from services.graph_service import graph_service
from services.attachment_downloader import attachment_downloader

logger = logging.getLogger(__name__)

class EmailFetcher:
    """Fetch and parse email metadata from Microsoft Graph"""
    
    def __init__(self):
        self.graph = graph_service
    
    async def fetch_email(self, notification: dict) -> EmailMetadata:
        """Fetch full email from notification"""
        # Extract mailbox and message ID from notification
        resource = notification.get('resource', '')
        mailbox, message_id = self._parse_resource(resource)
        
        if not mailbox or not message_id:
            raise ValueError(f"Invalid notification resource: {resource}")
        
        # Fetch from Graph API
        email_data = self.graph.fetch_email(mailbox, message_id)
        
        # Download attachments if present
        attachments = []
        if email_data.get('hasAttachments'):
            try:
                attachments = await attachment_downloader.download_attachments(
                    mailbox,
                    message_id
                )
                logger.info(f"Downloaded {len(attachments)} attachments for message {message_id}")
            except Exception as e:
                logger.error(f"Failed to download attachments: {e}")
                # Continue without attachments rather than failing completely
        
        # Parse into EmailMetadata
        return self._parse_email_data(email_data, mailbox, attachments)
    
    def _parse_resource(self, resource: str) -> tuple:
        """Parse resource string to extract mailbox and message ID"""
        # Format: users/{mailbox}/messages/{messageId}
        # or: users/{mailbox}/mailFolders/{folder}/messages/{messageId}
        parts = resource.split('/')
        
        if len(parts) >= 4:
            mailbox = parts[1]
            message_id = parts[-1]
            return mailbox, message_id
        
        return None, None
    
    def _parse_email_data(self, data: dict, mailbox: str, attachments: list = []) -> EmailMetadata:
        """Parse Graph API response into EmailMetadata"""
        
        # Parse timestamps
        received_dt = None
        sent_dt = None
        
        if data.get('receivedDateTime'):
            received_dt = datetime.fromisoformat(data['receivedDateTime'].replace('Z', '+00:00'))
        if data.get('sentDateTime'):
            sent_dt = datetime.fromisoformat(data['sentDateTime'].replace('Z', '+00:00'))
        
        # Parse body
        body_obj = data.get('body', {})
        body_content = body_obj.get('content', '')
        body_type = body_obj.get('contentType', 'text').lower()
        
        # Parse sender
        from_obj = data.get('from', {}).get('emailAddress', {})
        from_address = from_obj.get('address', '')
        from_name = from_obj.get('name', '')
        
        # Parse recipients
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
        
        # Use downloaded attachments (already have full content)
        # If no attachments downloaded, fallback to empty list
        attachment_list = attachments if attachments else []
        
        # Determine folder (simplified - would need folder lookup for accuracy)
        folder = 'Inbox'  # Default, can be enhanced with folder API call
        
        return EmailMetadata(
            message_id=data.get('id', ''),
            internet_message_id=data.get('internetMessageId', ''),
            conversation_id=data.get('conversationId', ''),
            conversation_index=data.get('conversationIndex', ''),
            subject=data.get('subject', ''),
            body_preview=data.get('bodyPreview', ''),
            body_content=body_content,
            body_type=body_type,
            from_address=from_address,
            from_name=from_name,
            to_recipients=to_recipients,
            cc_recipients=cc_recipients,
            bcc_recipients=bcc_recipients,
            received_datetime=received_dt,
            sent_datetime=sent_dt,
            has_attachments=data.get('hasAttachments', False),
            attachments=attachment_list,
            mailbox=mailbox,
            folder=folder
        )

# Global instance
email_fetcher = EmailFetcher()
