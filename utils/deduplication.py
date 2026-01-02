# Minimal deduplication - safety net for Exchange duplicate webhooks
# Uses simple in-memory cache with internet_message_id as key
# NOTE: Folder is ignored, so sent + received versions of same email = 1 API call
# Entries expire after TTL (default 1 hour) or when cache exceeds max_size

import logging
import time
from collections import OrderedDict

logger = logging.getLogger(__name__)

class SimpleDeduplicator:
    """Lightweight deduplication for webhook notifications with TTL support"""
    
    def __init__(self, max_size=1000, ttl_seconds=3600):
        """
        Initialize deduplicator.
        
        Args:
            max_size: Maximum number of entries to store (FIFO eviction)
            ttl_seconds: Time-to-live in seconds (default 3600 = 1 hour)
        """
        self._cache = OrderedDict()  # {message_id: timestamp}
        self._max_size = max_size
        self._ttl = ttl_seconds
    
    def is_duplicate(self, internet_message_id: str, folder: str) -> bool:
        """
        Check if this message was recently processed.
        
        Uses only internet_message_id as key (folder is ignored).
        This means:
        - Same email to multiple mailboxes (same folder) → Processed once ✅
        - Same email in Sent Items + Inbox (internal) → Processed once ✅
        
        Entries expire after TTL or when cache is full.
        """
        if not internet_message_id:
            return False  # Allow messages without ID
        
        # Clean up expired entries first
        self._cleanup_expired()
        
        # Use only internet_message_id (ignore folder)
        key = internet_message_id
        
        if key in self._cache:
            logger.debug(f"⏭️  Duplicate detected: {internet_message_id} (folder: {folder})")
            return True
        
        # Add to cache with current timestamp
        self._cache[key] = time.time()
        
        # Keep cache size manageable (FIFO)
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)  # Remove oldest
        
        return False
    
    def _cleanup_expired(self):
        """Remove entries older than TTL"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self._cache.items()
            if current_time - timestamp > self._ttl
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired deduplication entries")

# Global instance (1000 entries, 1 hour TTL)
simple_deduplicator = SimpleDeduplicator(max_size=1000, ttl_seconds=3600)
