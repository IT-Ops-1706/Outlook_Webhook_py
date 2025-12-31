import base64
from typing import List, Dict
import aiohttp
import logging
from services.graph_service import graph_service

logger = logging.getLogger(__name__)

class AttachmentDownloader:
    """Download email attachments from Microsoft Graph"""
    
    def __init__(self):
        self.graph = graph_service
        self.max_size_mb = 25  # Microsoft Graph limit
    
    async def download_attachments(
        self, 
        mailbox: str, 
        message_id: str
    ) -> List[Dict]:
        """
        Download all attachments for an email.
        Returns list of attachment data with content.
        """
        token = self.graph.get_access_token()
        
        url = f'https://graph.microsoft.com/v1.0/users/{mailbox}/messages/{message_id}/attachments'
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    attachments_data = await response.json()
                    
                    attachments = []
                    for att in attachments_data.get('value', []):
                        attachment = {
                            'id': att.get('id'),
                            'name': att.get('name'),
                            'content_type': att.get('contentType'),
                            'size': att.get('size'),
                            'is_inline': att.get('isInline', False)
                        }
                        
                        # Get content for file attachments
                        if att.get('@odata.type') == '#microsoft.graph.fileAttachment':
                            # Content is base64 encoded from Graph API
                            content_bytes_b64 = att.get('contentBytes')
                            
                            # Decode to actual bytes (don't store both!)
                            if content_bytes_b64:
                                try:
                                    attachment['content'] = base64.b64decode(content_bytes_b64)
                                except Exception as e:
                                    logger.error(f"Failed to decode attachment {attachment['name']}: {e}")
                                    attachment['content'] = None
                        
                        attachments.append(attachment)
                        
                        logger.info(
                            f"Downloaded attachment: {attachment['name']} "
                            f"({attachment['size']} bytes)"
                        )
                    
                    return attachments
        
        except Exception as e:
            logger.error(f"Failed to download attachments for message {message_id}: {e}")
            return []  # Return empty list on error, don't crash

# Global instance
attachment_downloader = AttachmentDownloader()
