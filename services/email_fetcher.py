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
        
        # Parse body - prefer uniqueBody (new content only) over body (full thread)
        import re
        from html import unescape
        
        unique_body_obj = data.get('uniqueBody', {})
        body_obj = data.get('body', {})
        body_preview = data.get('bodyPreview', '')
        
        # Use uniqueBody if available AND has actual TEXT content (not just whitespace/empty HTML)
        unique_html = unique_body_obj.get('content', '').strip() if unique_body_obj else ''
        
        # Extract actual text from uniqueBody HTML to verify it has real content
        unique_text = ''
        if unique_html:
            # Remove HTML tags and check for actual text
            text_only = re.sub(r'<[^>]+>', ' ', unique_html)
            text_only = re.sub(r'\s+', ' ', unescape(text_only)).strip()
            # Filter out just separator/boilerplate patterns
            if text_only and not re.match(r'^[\s_\-=]*$', text_only):
                unique_text = text_only
        
        # Check if uniqueBody has meaningful TEXT content (not just empty HTML structure)
        has_unique_content = bool(unique_text) and len(unique_text) > 5
        
        if has_unique_content:
            body_content = unique_body_obj.get('content', '')
            body_type = unique_body_obj.get('contentType', 'text').lower()
            
            # CRITICAL FIX: Check if bodyPreview has content that's missing from uniqueBody HTML
            # This happens when Microsoft Graph's uniqueBody HTML is malformed (missing first line)
            if body_preview and body_type == 'html':
                # Extract first meaningful line from bodyPreview (before newline or separator)
                # Skip if bodyPreview starts with separator pattern
                if not re.match(r'^[\s_\-=]+', body_preview.strip()):
                    first_line_match = re.match(r'^([^\r\n]+)', body_preview.strip())
                    if first_line_match:
                        first_line = first_line_match.group(1).strip()
                        
                        # Check if this first line is actually in the HTML body
                        if first_line and first_line not in body_content and len(first_line) > 3:
                            # First line is missing from HTML! Prepend it
                            # Insert after <body> tag
                            body_match = re.search(r'(<body[^>]*>)', body_content, re.IGNORECASE)
                            if body_match:
                                insert_pos = body_match.end()
                                new_content_html = f'<div style="font-family:Aptos,Aptos_EmbeddedFont,Aptos_MSFontService,Calibri,Helvetica,sans-serif; font-size:12pt; color:rgb(0,0,0)">{first_line}</div>'
                                body_content = body_content[:insert_pos] + new_content_html + body_content[insert_pos:]
                                logger.info(f"✅ Fixed missing first line in uniqueBody: '{first_line[:50]}...'")
            
            logger.debug("Using uniqueBody (new message only)")
        else:
            # uniqueBody is empty/useless - try to extract new content from body
            full_body = body_obj.get('content', '')
            body_type = body_obj.get('contentType', 'text').lower()
            
            # Try to extract content before the reply separator
            new_message_text = None
            
            if body_type == 'html' and full_body:
                # Try to find content before <hr> or "From:" separator
                # Pattern: Extract content between <body> and reply separator
                match = re.search(r'<body[^>]*>(.*?)(?:<hr|<div[^>]*id=["\']divRplyFwdMsg)', full_body, re.DOTALL | re.IGNORECASE)
                
                if match:
                    extracted = match.group(1).strip()
                    # Remove HTML tags and check for actual text
                    text_content = re.sub(r'<[^>]+>', ' ', extracted)
                    text_content = re.sub(r'\s+', ' ', unescape(text_content)).strip()
                    
                    if text_content and len(text_content) > 3:
                        new_message_text = text_content
                        logger.debug(f"Extracted new message from body HTML: '{new_message_text[:50]}...'")
            
            # If we couldn't extract from HTML, try bodyPreview
            if not new_message_text and body_preview:
                # Check if bodyPreview starts with actual content (not separator)
                preview_clean = body_preview.strip()
                if not re.match(r'^[\s_\-=]+', preview_clean):
                    # First line of bodyPreview might be the new message
                    first_line_match = re.match(r'^([^\r\n]+)', preview_clean)
                    if first_line_match:
                        first_line = first_line_match.group(1).strip()
                        # Verify it's not just "From:" header boilerplate
                        if first_line and not first_line.startswith('From:') and len(first_line) > 3:
                            new_message_text = first_line
                            logger.info(f"📝 Recovered new message from bodyPreview: '{first_line[:50]}...'")
            
            # Build the body content
            if new_message_text and body_type == 'html':
                # Prepend the extracted new message to the full body
                body_match = re.search(r'(<body[^>]*>)', full_body, re.IGNORECASE)
                if body_match:
                    insert_pos = body_match.end()
                    new_content_html = f'<div style="font-family:Aptos,Aptos_EmbeddedFont,Aptos_MSFontService,Calibri,Helvetica,sans-serif; font-size:12pt; color:rgb(0,0,0)">{new_message_text}</div>'
                    
                    # Check if this text is already in the body (avoid duplication)
                    if new_message_text not in full_body:
                        body_content = full_body[:insert_pos] + new_content_html + full_body[insert_pos:]
                        logger.info(f"✅ Prepended new message to body: '{new_message_text[:50]}...'")
                    else:
                        body_content = full_body
                else:
                    body_content = full_body
            else:
                body_content = full_body
                
            logger.debug("uniqueBody was empty/whitespace, using full body with extraction")
        
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
