import base64
import asyncio
from typing import List, Dict
import aiohttp
import logging
from services.graph_service import graph_service

logger = logging.getLogger(__name__)

class AttachmentDownloader:
    """Download email attachments from Microsoft Graph with retry support"""
    
    def __init__(self):
        self.graph = graph_service
        self.max_size_mb = 25  # Microsoft Graph limit
        self.max_retries = 3   # Number of retry attempts
        self.retry_delay = 2   # Seconds to wait between retries
    
    async def download_attachments(
        self, 
        mailbox: str, 
        message_id: str
    ) -> List[Dict]:
        """
        Download all attachments for an email with retry logic.
        
        Microsoft Graph sometimes has a delay between when an email arrives
        and when attachments are accessible. This method retries on 404 errors.
        
        Returns list of attachment data with content.
        """
        url = f'https://graph.microsoft.com/v1.0/users/{mailbox}/messages/{message_id}/attachments'
        
        for attempt in range(self.max_retries):
            try:
                # Get fresh token for each attempt
                token = await self.graph.get_access_token()
                
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                
                # Use graph service's session for connection pooling
                session = await self.graph._get_session()
                async with session.get(url, headers=headers) as response:
                    # Check for 401 - authentication issue
                    if response.status == 401:
                        logger.error(f"Authentication failed for attachments (401 Unauthorized)")
                        return []
                    
                    # Check for 404 - attachments not yet available
                    if response.status == 404:
                        if attempt < self.max_retries - 1:
                            logger.warning(
                                f"Attachments not ready (attempt {attempt + 1}/{self.max_retries}), "
                                f"retrying in {self.retry_delay}s..."
                            )
                            await asyncio.sleep(self.retry_delay)
                            continue
                        else:
                            logger.error(f"Attachments still not available after {self.max_retries} attempts")
                            return []
                    
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
                            content_bytes_b64 = att.get('contentBytes')
                            
                            if content_bytes_b64:
                                try:
                                    attachment['content'] = base64.b64decode(content_bytes_b64)
                                except Exception as e:
                                    logger.error(f"Failed to decode attachment {attachment['name']}: {e}")
                                    attachment['content'] = None
                            
                            attachments.append(attachment)
                            
                            logger.info(
                                f"Downloaded: {attachment['name']} ({attachment['size']} bytes)"
                            )
                        
                        return attachments
            
            except aiohttp.ClientResponseError as e:
                if e.status == 404 and attempt < self.max_retries - 1:
                    logger.warning(
                        f"📎 Attachments not ready (attempt {attempt + 1}/{self.max_retries}), "
                        f"retrying in {self.retry_delay}s..."
                    )
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    logger.error(f"Failed to download attachments: {e}")
                    return []
            
            except Exception as e:
                logger.error(f"Failed to download attachments for message {message_id}: {e}")
                return []
        
        return []

# Global instance
attachment_downloader = AttachmentDownloader()
