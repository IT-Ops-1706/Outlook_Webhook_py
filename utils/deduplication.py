# Deduplication disabled - utility handles all duplicate logic
# This file kept for backward compatibility but does nothing

class EmailDeduplicator:
    def deduplicate(self, notifications):
        return notifications  # Pass everything through

class InternetMessageDeduplicator:
    def is_unique(self, *args, **kwargs):
        return True  # Everything is unique

# Global instances (no-op)
deduplicator = EmailDeduplicator()
internet_message_deduplicator = InternetMessageDeduplicator()
