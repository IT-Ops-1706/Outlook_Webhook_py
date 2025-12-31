# Minimal deduplication - safety net for Exchange duplicate webhooks
# Uses simple in-memory cache with (internet_message_id, folder) as key

import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)

class SimpleDeduplicator:
    """Lightweight deduplication for webhook notifications"""
    
    def __init__(self, max_size=1000):
        self._cache = OrderedDict()
        self._max_size = max_size
    
    def is_duplicate(self, internet_message_id: str, folder: str) -> bool:
        """Check if this message was recently processed"""
        if not internet_message_id:
            return False  # Allow messages without ID
        
        key = f"{internet_message_id}:{folder}"
        
        if key in self._cache:
            logger.debug(f"⏭️  Duplicate detected: {internet_message_id} in {folder}")
            return True
        
        # Add to cache
        self._cache[key] = True
        
        # Keep cache size manageable (FIFO)
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)  # Remove oldest
        
        return False

# Global instance
simple_deduplicator = SimpleDeduplicator()
