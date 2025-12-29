import re
import logging
from typing import List, Any
from models.email_metadata import EmailMetadata
from models.utility_config import UtilityConfig

logger = logging.getLogger(__name__)

class RuleMatcher:
    """
    Advanced email filtering system with Power Automate/Zapier-style capabilities.
    
    Supports:
    - Negation (NOT operator)
    - Multiple conditions with AND/OR logic
    - Nested condition groups
    - 15+ field operators
    - Backward compatibility with legacy filters
    """
    
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
        """Check if email matches utility filters (supports both old and new formats)"""
        filters = utility.pre_filters
        
        # First check: Mailbox subscription
        subscribed_mailboxes = [
            mb['address'].lower() 
            for mb in utility.subscriptions.get('mailboxes', [])
        ]
        
        mailbox_match = email.mailbox.lower() in subscribed_mailboxes
        
        if not mailbox_match:
            return False
        
        # Check if using new advanced filter format
        if 'condition_groups' in filters:
            result = RuleMatcher._matches_advanced_filters(email, filters, utility)
            return result
        
        # Fallback to legacy filter format (backward compatibility)
        return RuleMatcher._matches_legacy_filters(email, filters, utility)
    
    # ==================== ADVANCED FILTER SYSTEM ====================
    
    @staticmethod
    def _matches_advanced_filters(email: EmailMetadata, filters: dict, utility: UtilityConfig) -> bool:
        """Match using advanced condition groups"""
        
        # First check mailbox (always required)
        if not RuleMatcher._check_mailbox(email, utility):
            return False
        
        condition_groups = filters.get('condition_groups', [])
        group_logic = filters.get('group_logic', 'AND')
        
        if not condition_groups:
            return True  # No conditions = match all
        
        # Evaluate each condition group
        group_results = []
        for group in condition_groups:
            result = RuleMatcher._evaluate_condition_group(email, group)
            group_results.append(result)
        
        # Combine group results
        if group_logic == 'AND':
            final_result = all(group_results)
        elif group_logic == 'OR':
            final_result = any(group_results)
        else:
            logger.warning(f"Unknown group_logic: {group_logic}, defaulting to AND")
            final_result = all(group_results)
        
        return final_result
    
    @staticmethod
    def _evaluate_condition_group(email: EmailMetadata, group: dict) -> bool:
        """Evaluate a single condition group"""
        
        conditions = group.get('conditions', [])
        logic = group.get('logic', 'AND')
        
        if not conditions:
            return True
        
        # Evaluate each condition
        results = []
        for condition in conditions:
            result = RuleMatcher._evaluate_condition(email, condition)
            results.append(result)
        
        # Combine results
        if logic == 'AND':
            return all(results)
        elif logic == 'OR':
            return any(results)
        else:
            logger.warning(f"Unknown logic: {logic}, defaulting to AND")
            return all(results)
    
    @staticmethod
    def _evaluate_condition(email: EmailMetadata, condition: dict) -> bool:
        """Evaluate a single condition"""
        
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        negate = condition.get('negate', False)
        case_sensitive = condition.get('case_sensitive', False)
        
        # Get field value from email
        field_value = RuleMatcher._get_field_value(email, field)
        
        # Apply operator
        result = RuleMatcher._apply_operator(
            field_value,
            operator,
            value,
            case_sensitive
        )
        
        # Apply negation
        if negate:
            result = not result
        
        return result
    
    @staticmethod
    def _get_field_value(email: EmailMetadata, field: str) -> Any:
        """Get field value from email"""
        
        field_map = {
            'from_address': email.from_address,
            'from_name': email.from_name,
            'subject': email.subject,
            'body_preview': email.body_preview,
            'body_content': email.body_content,
            'has_attachments': email.has_attachments,
            'attachment_count': len(email.attachment_metadata),
            'folder': email.folder,
            'direction': email.direction,
            'to_recipients': [r['address'] for r in email.to_recipients],
            'cc_recipients': [r['address'] for r in email.cc_recipients],
            'bcc_recipients': [r['address'] for r in email.bcc_recipients],
            'attachment_names': [a['name'] for a in email.attachment_metadata],
            'mailbox': email.mailbox,
        }
        
        return field_map.get(field)
    
    @staticmethod
    def _apply_operator(field_value: Any, operator: str, value: Any, case_sensitive: bool) -> bool:
        """Apply operator to field value"""
        
        # Handle None/empty field values
        if field_value is None:
            field_value = ""
        
        # Handle case sensitivity for strings
        if isinstance(field_value, str) and not case_sensitive:
            field_value_compare = field_value.lower()
            value_compare = value.lower() if isinstance(value, str) else value
        else:
            field_value_compare = field_value
            value_compare = value
        
        try:
            # String operators
            if operator == 'equals':
                return field_value_compare == value_compare
            
            elif operator == 'not_equals':
                return field_value_compare != value_compare
            
            elif operator == 'contains':
                if isinstance(field_value_compare, str):
                    return value_compare in field_value_compare
                elif isinstance(field_value_compare, list):
                    # Check if any list item contains the value
                    return any(value_compare in str(item).lower() if not case_sensitive else value_compare in str(item) 
                              for item in field_value_compare)
                return False
            
            elif operator == 'not_contains':
                if isinstance(field_value_compare, str):
                    return value_compare not in field_value_compare
                elif isinstance(field_value_compare, list):
                    return not any(value_compare in str(item).lower() if not case_sensitive else value_compare in str(item)
                                  for item in field_value_compare)
                return True
            
            elif operator == 'starts_with':
                return isinstance(field_value_compare, str) and field_value_compare.startswith(value_compare)
            
            elif operator == 'ends_with':
                return isinstance(field_value_compare, str) and field_value_compare.endswith(value_compare)
            
            elif operator == 'regex':
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(value, flags)
                return bool(pattern.search(str(field_value)))
            
            elif operator == 'in':
                # Check if field value is in the provided list
                if not case_sensitive and isinstance(field_value, str):
                    value_list_lower = [v.lower() if isinstance(v, str) else v for v in value]
                    return field_value_compare in value_list_lower
                return field_value in value
            
            elif operator == 'not_in':
                if not case_sensitive and isinstance(field_value, str):
                    value_list_lower = [v.lower() if isinstance(v, str) else v for v in value]
                    return field_value_compare not in value_list_lower
                return field_value not in value
            
            # Numeric operators
            elif operator == 'greater_than':
                return float(field_value) > float(value)
            
            elif operator == 'less_than':
                return float(field_value) < float(value)
            
            elif operator == 'greater_than_or_equal':
                return float(field_value) >= float(value)
            
            elif operator == 'less_than_or_equal':
                return float(field_value) <= float(value)
            
            elif operator == 'between':
                # Value should be [min, max]
                return float(value[0]) <= float(field_value) <= float(value[1])
            
            # Empty/null operators
            elif operator == 'is_empty':
                return not field_value or field_value == '' or field_value == []
            
            elif operator == 'is_not_empty':
                return bool(field_value) and field_value != '' and field_value != []
            
            else:
                logger.warning(f"Unknown operator: {operator}")
                return False
        
        except Exception as e:
            logger.error(f"Error applying operator {operator}: {e}")
            return False
    
    # ==================== LEGACY FILTER SYSTEM (Backward Compatibility) ====================
    
    @staticmethod
    def _matches_legacy_filters(email: EmailMetadata, filters: dict, utility: UtilityConfig) -> bool:
        """Check if email matches legacy filter format"""
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
                filenames = [att['name'].lower() for att in email.attachment_metadata]
                if not any(any(p.lower() in fn for p in patterns) for fn in filenames):
                    return False
        
        return True
