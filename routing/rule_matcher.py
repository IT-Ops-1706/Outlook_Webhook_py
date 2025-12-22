import re
import logging
from typing import List
from models.email_metadata import EmailMetadata
from models.utility_config import UtilityConfig

logger = logging.getLogger(__name__)

class RuleMatcher:
    """Match emails against utility filter rules"""
    
    @staticmethod
    async def find_matching_utilities(
        email: EmailMetadata,
        utilities: List[UtilityConfig]
    ) -> List[UtilityConfig]:
        """Find all utilities that match this email"""
        matched = []
        
        for utility in utilities:
            if not utility.enabled:
                continue
            
            if RuleMatcher._matches_utility(email, utility):
                matched.append(utility)
                logger.info(f"Email '{email.subject[:50]}' matched utility: {utility.name}")
        
        if not matched:
            logger.debug(f"Email '{email.subject[:50]}' matched no utilities")
        
        return matched
    
    @staticmethod
    def _matches_utility(email: EmailMetadata, utility: UtilityConfig) -> bool:
        """Check if email matches all utility filters"""
        filters = utility.pre_filters
        match_logic = filters.get('match_logic', 'AND')
        
        checks = [
            RuleMatcher._check_mailbox(email, utility),
            RuleMatcher._check_direction(email, filters),
            RuleMatcher._check_subject(email, filters.get('subject', {})),
            RuleMatcher._check_body(email, filters.get('body', {})),
            RuleMatcher._check_sender(email, filters.get('sender', {})),
            RuleMatcher._check_receiver(email, filters.get('receiver', {})),
            RuleMatcher._check_attachments(email, filters.get('attachments', {}))
        ]
        
        if match_logic == 'AND':
            return all(checks)
        else:  # OR
            return any(checks)
    
    @staticmethod
    def _check_mailbox(email: EmailMetadata, utility: UtilityConfig) -> bool:
        """Check if email is from monitored mailbox"""
        monitored = [m['address'] for m in utility.subscriptions.get('mailboxes', [])]
        return email.mailbox in monitored
    
    @staticmethod
    def _check_direction(email: EmailMetadata, filters: dict) -> bool:
        """Check email direction"""
        direction_filter = filters.get('direction', 'both')
        
        if direction_filter == 'both':
            return True
        elif direction_filter == 'received':
            return email.folder != 'Sent Items'
        elif direction_filter == 'sent':
            return email.folder == 'Sent Items'
        
        return True
    
    @staticmethod
    def _check_subject(email: EmailMetadata, subject_filters: dict) -> bool:
        """Check subject filters"""
        if not subject_filters:
            return True
        
        subject = email.subject.lower()
        
        # Contains check
        if 'contains' in subject_filters and subject_filters['contains']:
            if not any(kw.lower() in subject for kw in subject_filters['contains']):
                return False
        
        # Regex check
        if 'regex' in subject_filters and subject_filters['regex']:
            if not re.search(subject_filters['regex'], email.subject, re.IGNORECASE):
                return False
        
        return True
    
    @staticmethod
    def _check_body(email: EmailMetadata, body_filters: dict) -> bool:
        """Check body filters"""
        if not body_filters:
            return True
        
        body = email.body_content.lower()
        
        # Contains check
        if 'contains' in body_filters and body_filters['contains']:
            if not any(kw.lower() in body for kw in body_filters['contains']):
                return False
        
        # Regex check
        if 'regex' in body_filters and body_filters['regex']:
            if not re.search(body_filters['regex'], email.body_content, re.IGNORECASE):
                return False
        
        return True
    
    @staticmethod
    def _check_sender(email: EmailMetadata, sender_filters: dict) -> bool:
        """Check sender filters"""
        if not sender_filters:
            return True
        
        sender = email.from_address.lower()
        
        # Exact match
        if 'exact' in sender_filters and sender_filters['exact']:
            return sender == sender_filters['exact'].lower()
        
        # In list
        if 'in_list' in sender_filters and sender_filters['in_list']:
            allowed = [s.lower() for s in sender_filters['in_list']]
            if sender not in allowed:
                return False
        
        # Contains
        if 'contains' in sender_filters and sender_filters['contains']:
            if not any(p.lower() in sender for p in sender_filters['contains']):
                return False
        
        return True
    
    @staticmethod
    def _check_receiver(email: EmailMetadata, receiver_filters: dict) -> bool:
        """Check receiver filters"""
        if not receiver_filters:
            return True
        
        # Collect all recipients
        all_recipients = []
        all_recipients.extend([r['address'].lower() for r in email.to_recipients])
        all_recipients.extend([r['address'].lower() for r in email.cc_recipients])
        
        # In list
        if 'in_list' in receiver_filters and receiver_filters['in_list']:
            allowed = [r.lower() for r in receiver_filters['in_list']]
            if not any(r in allowed for r in all_recipients):
                return False
        
        # Contains
        if 'contains' in receiver_filters and receiver_filters['contains']:
            patterns = receiver_filters['contains']
            matched = any(
                any(p.lower() in recipient for p in patterns)
                for recipient in all_recipients
            )
            if not matched:
                return False
        
        return True
    
    @staticmethod
    def _check_attachments(email: EmailMetadata, attachment_filters: dict) -> bool:
        """Check attachment filters"""
        if not attachment_filters:
            return True
        
        # Required check
        if attachment_filters.get('required', False) and not email.has_attachments:
            return False
        
        # Filename contains
        if 'filename_contains' in attachment_filters and attachment_filters['filename_contains']:
            patterns = attachment_filters['filename_contains']
            if email.has_attachments:
                filenames = [att['name'].lower() for att in email.attachments]
                if not any(any(p.lower() in fn for p in patterns) for fn in filenames):
                    return False
        
        return True
