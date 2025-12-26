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
        
        logger.debug(f"Parsed: mailbox_id={mailbox_id}, message_id={message_id}, folder={folder}")
        
        # Resolve mailbox UUID to email address using configured mailboxes
        from services.config_service import config_service
        logger.debug("=" * 60)
        logger.debug("FETCHING UTILITY CONFIGURATIONS")
        logger.debug("=" * 60)
        
        utilities = await config_service.get_all_utilities()
        logger.debug(f"Loaded {len(utilities)} utilities from config")
        
        # Log each utility's details
        for idx, utility in enumerate(utilities, 1):
            logger.debug(f"\nUtility #{idx}:")
            logger.debug(f"  ID: {utility.id}")
            logger.debug(f"  Name: {utility.name}")
            logger.debug(f"  Enabled: {utility.enabled}")
            logger.debug(f"  Endpoint: {utility.endpoint.get('url')}")
            logger.debug(f"  Has Auth: {'auth' in utility.endpoint}")
            logger.debug(f"  Mailboxes: {[m['address'] for m in utility.subscriptions.get('mailboxes', [])]}")
            logger.debug(f"  Filter Type: {'advanced' if 'condition_groups' in utility.pre_filters else 'legacy'}")
        
        # Collect all unique mailbox addresses from all utilities
        all_mailboxes = {}
        for utility in utilities:
            for mb in utility.subscriptions.get('mailboxes', []):
                # Store email address (we'll use this for matching)
                all_mailboxes[mb['address'].lower()] = mb['address']
        
        logger.debug(f"\nConfigured mailboxes summary: {list(all_mailboxes.values())}")
        logger.debug(f"Total unique mailboxes: {len(all_mailboxes)}")
        
        # For single mailbox setup, use it directly
        # (This works because subscriptions are created for these mailboxes)
        if len(all_mailboxes) == 1:
            mailbox_email = list(all_mailboxes.values())[0]
            logger.debug(f"\n✅ SINGLE MAILBOX MODE")
            logger.debug(f"Mapping: {mailbox_id} → {mailbox_email}")
        else:
            # Multiple mailboxes - would need Graph API lookup or UUID mapping
            # For now, use the first one and log warning
            mailbox_email = list(all_mailboxes.values())[0] if all_mailboxes else mailbox_id
            logger.warning(f"\n⚠️  MULTIPLE MAILBOXES DETECTED")
            logger.warning(f"Using first mailbox: {mailbox_email}")
            logger.warning(f"This may need Graph API lookup for proper resolution")
        
        logger.info(f"\n🔄 MAILBOX RESOLUTION: {mailbox_id} → {mailbox_email}")
        logger.debug("=" * 60)

        
        # Fetch from Graph API
        email_data = self.graph.fetch_email(mailbox_id, message_id)
        
        # Get attachment metadata (names, sizes) but NOT content
        attachment_metadata = []
        if email_data.get('hasAttachments'):
            # Extract metadata from Graph API response
            attachment_metadata = self._extract_attachment_metadata(email_data)
            logger.info(f"Found {len(attachment_metadata)} attachments (metadata only)")
        
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
        
        # Folder is now passed as parameter
        logger.debug(f"Creating EmailMetadata: mailbox={mailbox}, folder={folder}, subject={data.get('subject', '')[:50]}")
        
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
            attachment_metadata=attachment_metadata,
            attachments=attachments,
            mailbox=mailbox,
            folder=folder
        )

# Global instance
email_fetcher = EmailFetcher()
