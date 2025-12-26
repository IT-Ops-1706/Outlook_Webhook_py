# Advanced Filter System - Quick Reference

## Overview

Power Automate/Zapier-style filtering with:
- ✅ Negation (NOT operator)
- ✅ 15+ operators
- ✅ Condition groups with AND/OR logic
- ✅ Backward compatible with legacy format

---

## Basic Structure

```json
{
  "pre_filters": {
    "condition_groups": [
      {
        "name": "Group Name",
        "logic": "AND",
        "conditions": [
          {
            "field": "subject",
            "operator": "contains",
            "value": "Invoice",
            "negate": false,
            "case_sensitive": false
          }
        ]
      }
    ],
    "group_logic": "AND"
  }
}
```

---

## Supported Fields

| Field | Type | Description |
|-------|------|-------------|
| `from_address` | string | Sender email |
| `from_name` | string | Sender name |
| `subject` | string | Email subject |
| `body_preview` | string | Body preview |
| `body_content` | string | Full body |
| `has_attachments` | boolean | Has attachments |
| `attachment_count` | number | Number of attachments |
| `attachment_names` | array | Attachment filenames |
| `to_recipients` | array | TO recipients |
| `cc_recipients` | array | CC recipients |
| `folder` | string | Folder name |
| `direction` | string | received/sent |
| `mailbox` | string | Mailbox address |

---

## Supported Operators

### String Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `equals` | Exact match | `"vendor@example.com"` |
| `not_equals` | Not equal | `"spam@example.com"` |
| `contains` | Contains substring | `"Invoice"` |
| `not_contains` | Does not contain | `"Spam"` |
| `starts_with` | Starts with | `"RE:"` |
| `ends_with` | Ends with | `".pdf"` |
| `regex` | Regex match | `"INV-\\d{5}"` |
| `in` | In list | `["vendor1@", "vendor2@"]` |
| `not_in` | Not in list | `["spam@", "junk@"]` |

### Numeric Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `greater_than` | > | `5` |
| `less_than` | < | `10` |
| `greater_than_or_equal` | >= | `1` |
| `less_than_or_equal` | <= | `100` |
| `between` | Between range | `[5, 10]` |

### Empty/Null Operators

| Operator | Description |
|----------|-------------|
| `is_empty` | Empty or null |
| `is_not_empty` | Not empty |

---

## Common Patterns

### Pattern 1: Simple Filter with Negation

**Requirement:** Subject contains "Invoice" but NOT "Spam"

```json
{
  "condition_groups": [
    {
      "logic": "AND",
      "conditions": [
        {"field": "subject", "operator": "contains", "value": "Invoice"},
        {"field": "subject", "operator": "contains", "value": "Spam", "negate": true}
      ]
    }
  ]
}
```

---

### Pattern 2: Multiple Senders (OR Logic)

**Requirement:** From vendor1 OR vendor2 OR vendor3

```json
{
  "condition_groups": [
    {
      "logic": "OR",
      "conditions": [
        {"field": "from_address", "operator": "equals", "value": "vendor1@example.com"},
        {"field": "from_address", "operator": "equals", "value": "vendor2@example.com"},
        {"field": "from_address", "operator": "equals", "value": "vendor3@example.com"}
      ]
    }
  ]
}
```

**Alternative (cleaner):**

```json
{
  "condition_groups": [
    {
      "logic": "AND",
      "conditions": [
        {
          "field": "from_address",
          "operator": "in",
          "value": ["vendor1@example.com", "vendor2@example.com", "vendor3@example.com"]
        }
      ]
    }
  ]
}
```

---

### Pattern 3: Complex Nested Logic

**Requirement:** (vendor1 OR vendor2) AND (Invoice OR Payment) AND NOT Spam

```json
{
  "condition_groups": [
    {
      "name": "Sender Group",
      "logic": "OR",
      "conditions": [
        {"field": "from_address", "operator": "equals", "value": "vendor1@example.com"},
        {"field": "from_address", "operator": "equals", "value": "vendor2@example.com"}
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
    }
  ],
  "group_logic": "AND"
}
```

---

### Pattern 4: Attachment Filters

**Requirement:** Has PDF attachments, more than 1 attachment

```json
{
  "condition_groups": [
    {
      "logic": "AND",
      "conditions": [
        {"field": "has_attachments", "operator": "equals", "value": true},
        {"field": "attachment_count", "operator": "greater_than", "value": 1},
        {"field": "attachment_names", "operator": "ends_with", "value": ".pdf"}
      ]
    }
  ]
}
```

---

### Pattern 5: Exclude Multiple Keywords

**Requirement:** Exclude emails with "Spam", "Newsletter", or "Unsubscribe"

```json
{
  "condition_groups": [
    {
      "logic": "AND",
      "conditions": [
        {"field": "subject", "operator": "contains", "value": "Spam", "negate": true},
        {"field": "subject", "operator": "contains", "value": "Newsletter", "negate": true},
        {"field": "body_content", "operator": "contains", "value": "unsubscribe", "negate": true}
      ]
    }
  ]
}
```

---

### Pattern 6: Regex Pattern Matching

**Requirement:** Subject contains ID pattern like "ID_12345" or "ID-67890"

```json
{
  "condition_groups": [
    {
      "logic": "AND",
      "conditions": [
        {
          "field": "subject",
          "operator": "regex",
          "value": "ID[_-]\\d+",
          "case_sensitive": false
        }
      ]
    }
  ]
}
```

---

## Migration from Legacy Format

### Legacy Format

```json
{
  "pre_filters": {
    "match_logic": "AND",
    "sender": {"exact": "vendor@example.com"},
    "subject": {"contains": ["Invoice"]},
    "attachments": {"required": true}
  }
}
```

### Advanced Format (Equivalent)

```json
{
  "pre_filters": {
    "condition_groups": [
      {
        "logic": "AND",
        "conditions": [
          {"field": "from_address", "operator": "equals", "value": "vendor@example.com"},
          {"field": "subject", "operator": "contains", "value": "Invoice"},
          {"field": "has_attachments", "operator": "equals", "value": true}
        ]
      }
    ],
    "group_logic": "AND"
  }
}
```

---

## Negation Examples

### Using `negate: true`

```json
// Subject does NOT contain "Spam"
{"field": "subject", "operator": "contains", "value": "Spam", "negate": true}

// From address is NOT vendor@example.com
{"field": "from_address", "operator": "equals", "value": "vendor@example.com", "negate": true}

// Does NOT have attachments
{"field": "has_attachments", "operator": "equals", "value": true, "negate": true}
```

### Using `not_contains` operator

```json
// Subject does NOT contain "Spam" (alternative)
{"field": "subject", "operator": "not_contains", "value": "Spam"}

// From address does NOT contain "noreply"
{"field": "from_address", "operator": "not_contains", "value": "noreply"}
```

**Both approaches work! Use whichever is clearer.**

---

## Logic Operators

### Condition Logic (within a group)

```json
{
  "logic": "AND",  // All conditions must match
  "conditions": [...]
}

{
  "logic": "OR",   // Any condition must match
  "conditions": [...]
}
```

### Group Logic (between groups)

```json
{
  "group_logic": "AND",  // All groups must match
  "condition_groups": [...]
}

{
  "group_logic": "OR",   // Any group must match
  "condition_groups": [...]
}
```

---

## Testing Tips

### Test with Logs

Enable debug logging to see filter evaluation:

```
DEBUG: Condition group 'Sender Group': True
DEBUG:   Condition from_address equals vendor@example.com: True
DEBUG: Condition group 'Subject Keywords': True
DEBUG:   Condition subject contains Invoice: True
DEBUG: Final filter result: True (group_logic=AND)
```

### Test Cases

1. **Positive match:** Email that should match
2. **Negative match:** Email that should NOT match
3. **Edge cases:** Empty fields, special characters
4. **Negation:** Test `negate: true` works correctly

---

## Common Mistakes

### ❌ Wrong: Using `contains` for exact match

```json
{"field": "from_address", "operator": "contains", "value": "@example.com"}
// Matches: vendor@example.com, spam@example.com, etc.
```

### ✅ Correct: Use `equals` for exact match

```json
{"field": "from_address", "operator": "equals", "value": "vendor@example.com"}
// Matches only: vendor@example.com
```

---

### ❌ Wrong: Forgetting case sensitivity

```json
{"field": "subject", "operator": "equals", "value": "INVOICE", "case_sensitive": true}
// Won't match: "Invoice", "invoice"
```

### ✅ Correct: Use case_sensitive: false (default)

```json
{"field": "subject", "operator": "equals", "value": "invoice"}
// Matches: "Invoice", "INVOICE", "invoice"
```

---

## Summary

**Key Features:**
- ✅ Negation with `negate: true`
- ✅ 15+ operators
- ✅ Condition groups
- ✅ AND/OR logic
- ✅ Backward compatible

**Common Operators:**
- `equals`, `contains`, `regex`
- `in`, `not_in`
- `greater_than`, `less_than`
- `is_empty`, `is_not_empty`

**Best Practices:**
- Use descriptive group names
- Test with debug logging
- Use `in` operator for multiple values
- Use `negate: true` for exclusions

**Files:**
- Implementation: `routing/rule_matcher.py`
- Examples: `config/utility_rules_examples.json`
- Current config: `config/utility_rules.json`
