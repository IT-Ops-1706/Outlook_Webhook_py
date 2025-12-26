# Advanced Filter System - Power Automate/Zapier Style

## Overview

**Goal:** Create flexible, powerful filtering like Power Automate/Zapier

**Features:**
- ✅ Negation (does NOT contain, is NOT equal to)
- ✅ Multiple conditions with AND/OR logic
- ✅ Nested condition groups
- ✅ Field-level operators (contains, equals, regex, etc.)
- ✅ Future-ready for automation UI

---

## Current vs. Proposed System

### Current (Limited)

```json
{
  "pre_filters": {
    "match_logic": "AND",
    "sender": {"exact": "vendor@example.com"},
    "subject": {"contains": ["Invoice"]},
    "body": {"contains": [], "regex": null}
  }
}
```

**Limitations:**
- ❌ Can't do "does NOT contain"
- ❌ Can't do complex logic (A AND (B OR C))
- ❌ Limited operators per field
- ❌ Hard to extend

---

### Proposed (Power Automate Style)

```json
{
  "pre_filters": {
    "condition_groups": [
      {
        "logic": "AND",
        "conditions": [
          {
            "field": "from_address",
            "operator": "equals",
            "value": "vendor@example.com",
            "negate": false
          },
          {
            "field": "subject",
            "operator": "contains",
            "value": "Invoice",
            "negate": false
          },
          {
            "field": "subject",
            "operator": "contains",
            "value": "Spam",
            "negate": true
          }
        ]
      }
    ],
    "group_logic": "AND"
  }
}
```

**Benefits:**
- ✅ Negation support
- ✅ Multiple conditions
- ✅ Extensible
- ✅ UI-friendly

---

## Complete Filter Schema

### Top-Level Structure

```json
{
  "id": "utility_1",
  "name": "Invoice Processor",
  "enabled": true,
  
  "subscriptions": {
    "mailboxes": [
      {"address": "it.ops@babajishivram.com", "folders": ["Inbox"]}
    ]
  },
  
  "pre_filters": {
    "condition_groups": [
      {
        "name": "Main Filters",
        "logic": "AND",
        "conditions": [...]
      }
    ],
    "group_logic": "AND"
  },
  
  "endpoint": {...}
}
```

---

### Condition Structure

```json
{
  "field": "subject",           // Which field to check
  "operator": "contains",       // How to check
  "value": "Invoice",          // What to check for
  "negate": false,             // Reverse the result
  "case_sensitive": false      // Case sensitivity (optional)
}
```

---

### Supported Fields

```json
{
  "field": "from_address"       // Sender email
  "field": "from_name"          // Sender name
  "field": "to_recipients"      // TO recipients (any)
  "field": "cc_recipients"      // CC recipients (any)
  "field": "subject"            // Email subject
  "field": "body_preview"       // Body preview
  "field": "body_content"       // Full body
  "field": "has_attachments"    // Boolean
  "field": "attachment_names"   // Attachment filenames (any)
  "field": "attachment_count"   // Number of attachments
  "field": "received_datetime"  // When received
  "field": "sent_datetime"      // When sent
  "field": "folder"             // Inbox, Sent Items, etc.
  "field": "direction"          // received or sent
}
```

---

### Supported Operators

| Operator | Description | Value Type | Example |
|----------|-------------|------------|---------|
| `equals` | Exact match | string | "vendor@example.com" |
| `not_equals` | Not equal | string | "spam@example.com" |
| `contains` | Contains substring | string | "Invoice" |
| `not_contains` | Does not contain | string | "Spam" |
| `starts_with` | Starts with | string | "RE:" |
| `ends_with` | Ends with | string | ".pdf" |
| `regex` | Regex match | string | "INV-\\d{5}" |
| `in` | In list | array | ["vendor1@", "vendor2@"] |
| `not_in` | Not in list | array | ["spam@", "junk@"] |
| `greater_than` | > | number | 5 |
| `less_than` | < | number | 10 |
| `between` | Between range | array | [5, 10] |
| `is_empty` | Empty/null | null | null |
| `is_not_empty` | Not empty | null | null |

---

## Example Configurations

### Example 1: Simple Invoice Filter

**Requirements:**
- From vendor@example.com
- Subject contains "Invoice"
- Subject does NOT contain "Spam"
- Has attachments

```json
{
  "pre_filters": {
    "condition_groups": [
      {
        "name": "Invoice Filters",
        "logic": "AND",
        "conditions": [
          {
            "field": "from_address",
            "operator": "equals",
            "value": "vendor@example.com",
            "negate": false
          },
          {
            "field": "subject",
            "operator": "contains",
            "value": "Invoice",
            "negate": false
          },
          {
            "field": "subject",
            "operator": "contains",
            "value": "Spam",
            "negate": true
          },
          {
            "field": "has_attachments",
            "operator": "equals",
            "value": true,
            "negate": false
          }
        ]
      }
    ],
    "group_logic": "AND"
  }
}
```

---

### Example 2: Multiple Senders (OR Logic)

**Requirements:**
- From vendor1@example.com OR vendor2@example.com
- Subject contains "Invoice"

```json
{
  "pre_filters": {
    "condition_groups": [
      {
        "name": "Sender Group",
        "logic": "OR",
        "conditions": [
          {
            "field": "from_address",
            "operator": "equals",
            "value": "vendor1@example.com"
          },
          {
            "field": "from_address",
            "operator": "equals",
            "value": "vendor2@example.com"
          }
        ]
      },
      {
        "name": "Subject Filter",
        "logic": "AND",
        "conditions": [
          {
            "field": "subject",
            "operator": "contains",
            "value": "Invoice"
          }
        ]
      }
    ],
    "group_logic": "AND"
  }
}
```

**Logic:** (vendor1 OR vendor2) AND (subject contains Invoice)

---

### Example 3: Complex Nested Logic

**Requirements:**
- (From vendor@example.com OR finance@example.com)
- AND (Subject contains "Invoice" OR "Payment")
- AND Subject does NOT contain "Spam"
- AND Has attachments

```json
{
  "pre_filters": {
    "condition_groups": [
      {
        "name": "Sender Group",
        "logic": "OR",
        "conditions": [
          {"field": "from_address", "operator": "equals", "value": "vendor@example.com"},
          {"field": "from_address", "operator": "equals", "value": "finance@example.com"}
        ]
      },
      {
        "name": "Subject Keywords",
        "logic": "OR",
        "conditions": [
          {"field": "subject", "operator": "contains", "value": "Invoice"},
          {"field": "subject", "operator": "contains", "value": "Payment"}
        ]
      },
      {
        "name": "Exclusions",
        "logic": "AND",
        "conditions": [
          {"field": "subject", "operator": "contains", "value": "Spam", "negate": true}
        ]
      },
      {
        "name": "Requirements",
        "logic": "AND",
        "conditions": [
          {"field": "has_attachments", "operator": "equals", "value": true}
        ]
      }
    ],
    "group_logic": "AND"
  }
}
```

**Logic:** (vendor OR finance) AND (Invoice OR Payment) AND NOT Spam AND has_attachments

---

### Example 4: Attachment Filters

**Requirements:**
- Has attachments
- Attachment name contains "invoice"
- Attachment name ends with ".pdf"
- More than 1 attachment

```json
{
  "pre_filters": {
    "condition_groups": [
      {
        "name": "Attachment Filters",
        "logic": "AND",
        "conditions": [
          {
            "field": "has_attachments",
            "operator": "equals",
            "value": true
          },
          {
            "field": "attachment_names",
            "operator": "contains",
            "value": "invoice",
            "case_sensitive": false
          },
          {
            "field": "attachment_names",
            "operator": "ends_with",
            "value": ".pdf"
          },
          {
            "field": "attachment_count",
            "operator": "greater_than",
            "value": 1
          }
        ]
      }
    ],
    "group_logic": "AND"
  }
}
```

---

### Example 5: Time-Based Filters

**Requirements:**
- Received in last 24 hours
- Sent during business hours (9 AM - 5 PM)

```json
{
  "pre_filters": {
    "condition_groups": [
      {
        "name": "Time Filters",
        "logic": "AND",
        "conditions": [
          {
            "field": "received_datetime",
            "operator": "greater_than",
            "value": "{{now - 24h}}",
            "value_type": "relative_time"
          },
          {
            "field": "sent_datetime",
            "operator": "between",
            "value": ["09:00", "17:00"],
            "value_type": "time_of_day"
          }
        ]
      }
    ],
    "group_logic": "AND"
  }
}
```

---

## Implementation

### Updated Rule Matcher

```python
# routing/rule_matcher.py

class RuleMatcher:
    """Match emails to utilities using advanced filters"""
    
    @staticmethod
    async def find_matching_utilities(email: EmailMetadata, utilities: list) -> list:
        """Find utilities that match the email"""
        matched = []
        
        for utility in utilities:
            if not utility.get('enabled', True):
                continue
            
            # Check pre-filters
            if RuleMatcher._matches_filters(email, utility.get('pre_filters', {})):
                matched.append(utility)
        
        return matched
    
    @staticmethod
    def _matches_filters(email: EmailMetadata, filters: dict) -> bool:
        """Check if email matches filter conditions"""
        
        if not filters:
            return True  # No filters = match all
        
        condition_groups = filters.get('condition_groups', [])
        group_logic = filters.get('group_logic', 'AND')
        
        if not condition_groups:
            return True
        
        # Evaluate each condition group
        group_results = []
        for group in condition_groups:
            result = RuleMatcher._evaluate_condition_group(email, group)
            group_results.append(result)
        
        # Combine group results
        if group_logic == 'AND':
            return all(group_results)
        elif group_logic == 'OR':
            return any(group_results)
        else:
            return False
    
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
            return False
    
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
    def _get_field_value(email: EmailMetadata, field: str):
        """Get field value from email"""
        
        field_map = {
            'from_address': email.from_address,
            'from_name': email.from_name,
            'subject': email.subject,
            'body_preview': email.body_preview,
            'body_content': email.body_content,
            'has_attachments': email.has_attachments,
            'attachment_count': len(email.attachments),
            'folder': email.folder,
            'direction': email.direction,
            'to_recipients': [r['address'] for r in email.to_recipients],
            'cc_recipients': [r['address'] for r in email.cc_recipients],
            'attachment_names': [a['name'] for a in email.attachment_metadata],
        }
        
        return field_map.get(field)
    
    @staticmethod
    def _apply_operator(field_value, operator: str, value, case_sensitive: bool) -> bool:
        """Apply operator to field value"""
        
        # Handle case sensitivity for strings
        if isinstance(field_value, str) and not case_sensitive:
            field_value = field_value.lower()
            if isinstance(value, str):
                value = value.lower()
        
        # Apply operator
        if operator == 'equals':
            return field_value == value
        
        elif operator == 'not_equals':
            return field_value != value
        
        elif operator == 'contains':
            if isinstance(field_value, str):
                return value in field_value
            elif isinstance(field_value, list):
                return any(value in item for item in field_value)
            return False
        
        elif operator == 'not_contains':
            if isinstance(field_value, str):
                return value not in field_value
            elif isinstance(field_value, list):
                return not any(value in item for item in field_value)
            return True
        
        elif operator == 'starts_with':
            return isinstance(field_value, str) and field_value.startswith(value)
        
        elif operator == 'ends_with':
            return isinstance(field_value, str) and field_value.endswith(value)
        
        elif operator == 'regex':
            import re
            pattern = re.compile(value, re.IGNORECASE if not case_sensitive else 0)
            return bool(pattern.search(str(field_value)))
        
        elif operator == 'in':
            return field_value in value
        
        elif operator == 'not_in':
            return field_value not in value
        
        elif operator == 'greater_than':
            return field_value > value
        
        elif operator == 'less_than':
            return field_value < value
        
        elif operator == 'between':
            return value[0] <= field_value <= value[1]
        
        elif operator == 'is_empty':
            return not field_value or field_value == '' or field_value == []
        
        elif operator == 'is_not_empty':
            return bool(field_value)
        
        return False
```

---

## Migration Path

### Phase 1: Support Both Formats

```python
def _matches_filters(email: EmailMetadata, filters: dict) -> bool:
    """Support both old and new filter formats"""
    
    # New format (condition_groups)
    if 'condition_groups' in filters:
        return RuleMatcher._matches_advanced_filters(email, filters)
    
    # Old format (backward compatibility)
    else:
        return RuleMatcher._matches_legacy_filters(email, filters)
```

### Phase 2: Migrate Existing Rules

Convert old format to new format:

```python
# Old
{
  "sender": {"exact": "vendor@example.com"},
  "subject": {"contains": ["Invoice"]}
}

# New
{
  "condition_groups": [
    {
      "logic": "AND",
      "conditions": [
        {"field": "from_address", "operator": "equals", "value": "vendor@example.com"},
        {"field": "subject", "operator": "contains", "value": "Invoice"}
      ]
    }
  ]
}
```

---

## Future: Automation UI

### Visual Filter Builder (Like Power Automate)

```
┌─────────────────────────────────────────────────────────┐
│ Add Condition                                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ [Field ▼] [Operator ▼] [Value      ] [🗑️]             │
│ Subject    contains     Invoice                         │
│                                                         │
│ [AND ▼]                                                 │
│                                                         │
│ [Field ▼] [Operator ▼] [Value      ] [🗑️] [NOT ☐]     │
│ Subject    contains     Spam                   ☑        │
│                                                         │
│ [+ Add Condition] [+ Add Group]                         │
└─────────────────────────────────────────────────────────┘
```

---

## Summary

### Current Limitations
- ❌ No negation
- ❌ Limited operators
- ❌ Simple AND logic only

### New Capabilities
- ✅ Negation (NOT)
- ✅ Multiple operators (15+)
- ✅ Complex logic (AND/OR/nested)
- ✅ Condition groups
- ✅ UI-friendly structure
- ✅ Future-ready for automation tool

### Implementation
- Backward compatible
- Easy migration
- Extensible design
- Power Automate/Zapier style

**Ready to implement this advanced filtering system?** 🚀
