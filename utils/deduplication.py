import time
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class EmailDeduplicator:
    """Deduplicate email notifications based on message ID"""
    
    def __init__(self, ttl_seconds=300):
        self._cache: Dict[str, float] = {}
        self._ttl = ttl_seconds
    
    def deduplicate(self, notifications: List[dict]) -> List[dict]:
        """Remove duplicate notifications"""
        unique = []
        current_time = time.time()
        
        # Cleanup old cache entries
        self._cleanup(current_time)
        
        for notification in notifications:
            msg_id = self._extract_message_id(notification)
            
            if msg_id and msg_id not in self._cache:
                self._cache[msg_id] = current_time
                unique.append(notification)
                logger.debug(f"New email: {msg_id}")
            else:
                logger.debug(f"Duplicate skipped: {msg_id}")
        
        logger.info(f"Deduplicated: {len(notifications)} → {len(unique)} unique emails")
        return unique
    
    def _extract_message_id(self, notification: dict) -> Optional[str]:
        """Extract message ID from notification resource"""
        resource = notification.get('resource', '')
        # Format: users/{mailbox}/messages/{messageId}
        parts = resource.split('/')
        return parts[-1] if len(parts) >= 4 else None
    
    def _cleanup(self, current_time: float):
        """Remove expired cache entries"""
        expired = [
            k for k, v in self._cache.items()
            if current_time - v > self._ttl
        ]
        for k in expired:
            del self._cache[k]
        
        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired cache entries")

class InternetMessageDeduplicator:
    """Deduplicate emails based on Internet Message ID (globally unique)"""
    
    def __init__(self, ttl_seconds=300):
        self._cache: Dict[str, float] = {}
        self._ttl = ttl_seconds
    
    def is_unique(self, internet_message_id: str, body_content: str = None) -> bool:
        """
        Check if this Internet Message ID has been seen before.
        Crucial update: If ID is same but body is different, treat as unique (update).
        """
        if not internet_message_id:
            return True  # Allow emails without Internet Message ID
        
        current_time = time.time()
        self._cleanup(current_time)
        
        # Create a composite key if body is present
        # Use simple length + first 50 chars as crude hash to avoid memory issues with full hash
        if body_content:
            body_hash = f"{len(body_content)}_{hash(body_content[:100])}"
            cache_key = f"{internet_message_id}_{body_hash}"
        else:
            cache_key = internet_message_id
            
        if cache_key in self._cache:
            # Check if it was strictly the ID or the composite
            logger.debug(f"Duplicate Internet Message ID detected: {cache_key}")
            return False
        
        # Mark as seen
        self._cache[cache_key] = current_time
        
        # Also cache the strict ID slightly differently if needed, but for now just using composite
        # If we get the same ID again with DIFFERENT body, the cache_key will differ -> allowed.
        # If we get the same ID with SAME body -> blocked.
        
        logger.debug(f"New Internet Message ID (or distinct content): {internet_message_id}")
        return True
    
    def _cleanup(self, current_time: float):
        """Remove expired cache entries"""
        expired = [
            k for k, v in self._cache.items()
            if current_time - v > self._ttl
        ]
        for k in expired:
            del self._cache[k]
        
        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired Internet Message ID cache entries")

# Global instances
deduplicator = EmailDeduplicator()
internet_message_deduplicator = InternetMessageDeduplicator()
