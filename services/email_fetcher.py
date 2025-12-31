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
    
    async def fetch_email_metadata(self, notification: dict) -> EmailMetadata:
        """
        Fetch email metadata WITHOUT downloading attachments.
        Attachments can be loaded later with load_attachments().
        """
        # Extract mailbox and message ID from notification
        resource = notification.get('resource', '')
        logger.debug(f"Processing notification resource: {resource}")
        
        mailbox_id, message_id, folder = self._parse_resource(resource)
        
        if not mailbox_id or not message_id:
            raise ValueError(f"Invalid notification resource: {resource}")
        
        # Resolve mailbox UUID to email address using configured mailboxes
        from services.config_service import config_service
        
        utilities = await config_service.get_all_utilities()
        
        # Collect all unique mailbox addresses from all utilities
        all_mailboxes = {}
        for utility in utilities:
            for mb in utility.subscriptions.get('mailboxes', []):
                all_mailboxes[mb['address'].lower()] = mb['address']
        
        # For single mailbox setup, use it directly
        if len(all_mailboxes) == 1:
            mailbox_email = list(all_mailboxes.values())[0]
        else:
            # Multiple mailboxes - would need Graph API lookup or UUID mapping
            mailbox_email = list(all_mailboxes.values())[0] if all_mailboxes else mailbox_id
            logger.warning(f"Multiple mailboxes detected, using: {mailbox_email}")

        
        # Fetch from Graph API
        email_data = self.graph.fetch_email(mailbox_id, message_id)
        
        # Log email details
        subject = email_data.get('subject', '(no subject)')
        body_preview = email_data.get('bodyPreview', '')[:100]
        logger.info(f"📧 Fetched: '{subject}' | Preview: {body_preview}...")
        
        # Get attachment metadata (names, sizes) but NOT content
        attachment_metadata = []
        if email_data.get('hasAttachments'):
            attachment_metadata = self._extract_attachment_metadata(email_data)
            logger.info(f"📎 {len(attachment_metadata)} attachment(s): {[a['name'] for a in attachment_metadata]}")
        
        # Parse into EmailMetadata (without attachment content)
        return self._parse_email_data(
            email_data,
            mailbox_email,  # Use resolved email address
            folder,  # Use parsed folder
            attachment_metadata=attachment_metadata,
            attachments=[]  # Empty - not loaded yet
        )
    
    async def load_attachments(self, email: EmailMetadata) -> EmailMetadata:
        """
        Download and attach full attachment content.
        Only call this after pre-filter matching succeeds.
        """
        if not email.has_attachments:
            return email  # Nothing to load
        
        if email.attachments_loaded:
            logger.debug(f"Attachments already loaded for {email.message_id}")
            return email  # Already loaded
        
        try:
            # Download full attachments
            attachments = await attachment_downloader.download_attachments(
                email.mailbox,
                email.message_id
            )
            logger.info(f"Downloaded {len(attachments)} attachments for message {email.message_id}")
            
            # Update email object
            email.attachments = attachments
            
        except Exception as e:
            logger.error(f"Failed to download attachments: {e}")
            # Continue without attachments rather than failing completely
            email.attachments = []
        
        return email
    
    def _extract_text_from_html(self, html: str) -> str:
        """Extract plain text from HTML, removing tags and whitespace"""
        import re
        if not html:
            return ''
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove common separators (long underscores)
        text = text.replace('_' * 10, '').strip()
        return text
    
    def _extract_new_content_from_full_body(self, html: str) -> str:
        """
        Extract new message content from full body HTML.
        Stops at common reply separators.
        """
        import re
        
        if not html:
            return ''
        
        # Common reply separators (case-insensitive)
        separators = [
            r'<hr[^>]*>',  # Horizontal rule (Outlook reply separator)
            r'<div\s+id=["\']divRplyFwdMsg["\']',  # Outlook reply div
            r'_{20,}',  # Underscores (Outlook text)
            r'From:.*?Sent:.*?To:',  # Email headers
            r'On .+ wrote:',  # Gmail style
            r'<div class="gmail_quote">',  # Gmail quote div
            r'<blockquote',  # Quoted text
        ]
        
        # Find first separator
        earliest_pos = len(html)
        for sep in separators:
            match = re.search(sep, html, re.IGNORECASE | re.DOTALL)
            if match:
                earliest_pos = min(earliest_pos, match.start())
        
        # Extract content before separator
        new_content = html[:earliest_pos].strip()
        
        # If still has content, return it
        text = self._extract_text_from_html(new_content)
        if text and len(text) > 5:
            return new_content
        
        # No meaningful content found, return full body
        return html
    
    def _extract_attachment_metadata(self, email_data: dict) -> list:
        """Extract attachment names and sizes from email data"""
        # Graph API includes basic attachment info in the email response
        attachments_info = email_data.get('attachments', [])
        
        metadata = []
        for att in attachments_info:
            metadata.append({
                'id': att.get('id', ''),
                'name': att.get('name', ''),
                'size': att.get('size', 0),
                'content_type': att.get('contentType', ''),
                'is_inline': att.get('isInline', False)
            })
        
        return metadata
    
    def _parse_resource(self, resource: str) -> tuple:
        """Parse resource string to extract mailbox, message ID, and folder"""
        # Format: users/{mailbox}/messages/{messageId}
        # or: users/{mailbox}/mailFolders/{folder}/messages/{messageId}
        parts = resource.split('/')
        
        logger.debug(f"Parsing resource parts: {parts}")
        
        if len(parts) >= 4:
            mailbox = parts[1]
            message_id = parts[-1]
            
            # Default folder
            folder = 'Inbox'
            
            # Detect folder from resource path
            if 'mailFolders' in parts:
                folder_idx = parts.index('mailFolders') + 1
                if folder_idx < len(parts):
                    folder_name = parts[folder_idx]
                    # Map folder IDs to names
                    if folder_name == 'SentItems':
                        folder = 'Sent Items'
                    else:
                        folder = folder_name  # Keep as-is
            
            logger.debug(f"Parsed resource → mailbox={mailbox}, message_id={message_id}, folder={folder}")
            return mailbox, message_id, folder
        
        return None, None, 'Inbox'
    
    def _parse_email_data(
        self,
        data: dict,
        mailbox: str,
        folder: str = 'Inbox',
        attachment_metadata: list = [],
        attachments: list = []
    ) -> EmailMetadata:
        """Parse Graph API response into EmailMetadata"""
        
        # Parse timestamps
        received_dt = None
        sent_dt = None
        
        if data.get('receivedDateTime'):
            received_dt = datetime.fromisoformat(data['receivedDateTime'].replace('Z', '+00:00'))
        if data.get('sentDateTime'):
            sent_dt = datetime.fromisoformat(data['sentDateTime'].replace('Z', '+00:00'))
        
        # Parse body - Always use full body as requested
        # The utility will handle HTML structure and extraction if needed
        body_obj = data.get('body', {})
        body_content = body_obj.get('content', '')
        body_type = body_obj.get('contentType', 'text').lower()
        
        logger.debug(f"📧 Body: Using full body content by default ({len(body_content)} chars)")
        logger.debug(f"   Body Type: {body_type}")
        
        # Log preview for debugging
        if body_content:
            logger.debug(f"   Preview: {body_content[:200]}...")
        
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
        
        # Folder is now passed as parameter
        
        # --- DETAILED LOGGING (Requested by User) ---
        internet_message_id = data.get('internetMessageId', '')
        conversation_id = data.get('conversationId', '')
        subject = data.get('subject', '')
        
        logger.info(f"📄 EMAIL DETAILS FETCHED:")
        logger.info(f"   Internet Message ID: {internet_message_id}")
        logger.info(f"   Conversation ID:     {conversation_id}")
        logger.info(f"   Mailbox:             {mailbox}")
        logger.info(f"   Folder:              {folder}")
        logger.info(f"   Subject:             {subject}")
        logger.info(f"   Body Length:         {len(body_content)} chars")
        logger.info(f"   FULL BODY CONTENT:\n{body_content}")
        # ---------------------------------------------

        return EmailMetadata(
            message_id=data.get('id', ''),
            internet_message_id=internet_message_id,
            conversation_id=conversation_id,
            conversation_index=data.get('conversationIndex', ''),
            subject=subject,
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
            attachment_metadata=attachment_metadata,
            attachments=attachments,
            mailbox=mailbox,
            folder=folder
        )

# Global instance
email_fetcher = EmailFetcher()
