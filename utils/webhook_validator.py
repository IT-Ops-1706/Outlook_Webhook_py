import hmac
import hashlib
from fastapi import HTTPException, Request
import logging
import config

logger = logging.getLogger(__name__)

class WebhookValidator:
    """Validate Microsoft Graph webhook notifications"""
    
    def __init__(self):
        self.client_state = config.WEBHOOK_CLIENT_STATE if hasattr(config, 'WEBHOOK_CLIENT_STATE') else 'SecretClientState'
    
    async def validate_notification(self, data: dict) -> bool:
        """
        Validate webhook notification.
        Microsoft Graph includes clientState in notifications for validation.
        """
        try:
            # Check all notifications have correct client state
            for notification in data.get('value', []):
                received_state = notification.get('clientState')
                
                if received_state != self.client_state:
                    logger.error(
                        f"Invalid client state received: {received_state}, "
                        f"expected: {self.client_state}"
                    )
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid client state"
                    )
            
            logger.debug(f"Validated {len(data.get('value', []))} notifications")
            return True
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Validation error: {e}")
            raise HTTPException(
                status_code=400,
                detail="Validation failed"
            )

# Global instance
webhook_validator = WebhookValidator()
