# Microsoft Graph Email Data Reference

## What Microsoft Graph Provides

### Core Email Properties

| Field | Type | Description | Currently Fetched | Stored in Utility DB |
|-------|------|-------------|-------------------|---------------------|
| `id` | string | Outlook message ID (unique per folder) | ✅ Yes | ✅ Yes (`message_id`) |
| `internetMessageId` | string | RFC-2822 Message-ID (globally unique) | ✅ Yes | ✅ Yes (`internet_message_id`) |
| `conversationId` | string | Thread/conversation identifier | ✅ Yes | ✅ Yes (`conversation_id`) |
| `conversationIndex` | string | Position in thread (for sorting) | ✅ Yes | ✅ Yes (`conversation_index`) |
| `subject` | string | Email subject line | ✅ Yes | ✅ Yes (`subject`) |
| `bodyPreview` | string | First ~255 chars of body (plain text) | ✅ Yes | ✅ Yes (`body_preview`) |
| `body.content` | string | Full email body (HTML or text) | ✅ Yes | ✅ Yes (`body_content`) |
| `body.contentType` | string | `html` or `text` | ✅ Yes | ✅ Yes (`body_type`) |
| `uniqueBody.content` | string | Only new content (excludes quoted text) | ✅ Yes | ✅ Yes (`unique_body`) |
| `uniqueBody.contentType` | string | Content type of unique body | ❌ No | ❌ No |

### Participants

| Field | Type | Description | Currently Fetched | Stored in Utility DB |
|-------|------|-------------|-------------------|---------------------|
| `from.emailAddress.address` | string | Sender email | ✅ Yes | ✅ Yes (`from_address`) |
| `from.emailAddress.name` | string | Sender display name | ✅ Yes | ✅ Yes (`from_name`) |
| `toRecipients` | array | To recipients (address + name) | ✅ Yes | ✅ Yes (JSON) |
| `ccRecipients` | array | CC recipients | ✅ Yes | ✅ Yes (JSON) |
| `bccRecipients` | array | BCC recipients | ✅ Yes | ✅ Yes (JSON) |
| `replyTo` | array | Reply-To addresses | ❌ No | ❌ No |
| `sender` | object | Actual sender (if different from `from`) | ❌ No | ❌ No |

### Timestamps

| Field | Type | Description | Currently Fetched | Stored in Utility DB |
|-------|------|-------------|-------------------|---------------------|
| `receivedDateTime` | datetime | When email was received | ✅ Yes | ✅ Yes (`received_at`) |
| `sentDateTime` | datetime | When email was sent | ✅ Yes | ✅ Yes (`sent_at`) |
| `createdDateTime` | datetime | When message was created in mailbox | ❌ No | ❌ No |
| `lastModifiedDateTime` | datetime | Last modification time | ❌ No | ❌ No |

### Attachments

| Field | Type | Description | Currently Fetched | Stored in Utility DB |
|-------|------|-------------|-------------------|---------------------|
| `hasAttachments` | boolean | Whether email has attachments | ✅ Yes | ✅ Yes (`has_attachments`) |
| `attachments[].id` | string | Attachment ID | ✅ Yes (metadata) | ✅ Yes (JSON) |
| `attachments[].name` | string | File name | ✅ Yes (metadata) | ✅ Yes (JSON) |
| `attachments[].size` | integer | File size in bytes | ✅ Yes (metadata) | ✅ Yes (JSON) |
| `attachments[].contentType` | string | MIME type | ✅ Yes (metadata) | ✅ Yes (JSON) |
| `attachments[].isInline` | boolean | Inline vs regular attachment | ✅ Yes (metadata) | ✅ Yes (JSON) |
| `attachments[].contentBytes` | base64 | Actual file content | ✅ Yes (lazy loaded) | ✅ Yes (base64 in JSON) |
| `attachments[].contentId` | string | Content-ID for inline images | ❌ No | ❌ No |
| `attachments[].lastModifiedDateTime` | datetime | When attachment was modified | ❌ No | ❌ No |

### Flags & Categories

| Field | Type | Description | Currently Fetched | Stored in Utility DB |
|-------|------|-------------|-------------------|---------------------|
| `isRead` | boolean | Read/unread status | ❌ No | ❌ No |
| `isDraft` | boolean | Draft status | ❌ No | ❌ No |
| `flag` | object | Follow-up flag | ❌ No | ❌ No |
| `importance` | string | `low`, `normal`, `high` | ❌ No | ❌ No |
| `categories` | array | Outlook categories | ❌ No | ❌ No |
| `inferenceClassification` | string | `focused` or `other` | ❌ No | ❌ No |

### Folder & Location

| Field | Type | Description | Currently Fetched | Stored in Utility DB |
|-------|------|-------------|-------------------|---------------------|
| `parentFolderId` | string | Folder ID (GUID) | ✅ Yes (resolved to name) | ✅ Yes (`folder`) |
| Folder display name | string | e.g., "Inbox", "Sent Items" | ✅ Yes (via API call) | ✅ Yes (`folder`) |
| `changeKey` | string | Version identifier | ❌ No | ❌ No |

### Thread & Reply Info

| Field | Type | Description | Currently Fetched | Stored in Utility DB |
|-------|------|-------------|-------------------|---------------------|
| `isDeliveryReceiptRequested` | boolean | Delivery receipt requested | ❌ No | ❌ No |
| `isReadReceiptRequested` | boolean | Read receipt requested | ❌ No | ❌ No |
| `inferenceClassification` | string | Focused inbox classification | ❌ No | ❌ No |

### Extended Properties (Advanced)

| Field | Type | Description | Currently Fetched | Stored in Utility DB |
|-------|------|-------------|-------------------|---------------------|
| `singleValueExtendedProperties` | array | Custom MAPI properties | ❌ No | ❌ No |
| `multiValueExtendedProperties` | array | Multi-value MAPI properties | ❌ No | ❌ No |
| `internetMessageHeaders` | array | Raw email headers | ❌ No | ❌ No |

---

## Recommended Database Schema

### For Email Thread Tracker Utility

```sql
-- Main emails table
CREATE TABLE emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Microsoft Graph IDs
    message_id TEXT NOT NULL,
    internet_message_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    conversation_index TEXT,
    
    -- Content
    subject TEXT NOT NULL,
    body_preview TEXT,
    body_content TEXT,
    unique_body TEXT,  -- New content only
    body_type TEXT DEFAULT 'html',
    
    -- Participants
    from_address TEXT NOT NULL,
    from_name TEXT,
    to_recipients JSON,  -- Array of {address, name}
    cc_recipients JSON,
    bcc_recipients JSON,
    
    -- Timestamps
    received_at DATETIME,
    sent_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Attachments
    has_attachments BOOLEAN DEFAULT 0,
    attachments JSON,  -- Array of attachment metadata + content
    
    -- Context
    mailbox TEXT NOT NULL,
    folder TEXT DEFAULT 'Inbox',
    direction TEXT CHECK(direction IN ('received', 'sent')),
    
    -- Employee enrichment (optional)
    sender_employee_data JSON,
    recipient_employee_data JSON,
    
    -- Indexes for performance
    UNIQUE(internet_message_id, direction)  -- Folder-aware uniqueness
);

-- Indexes
CREATE INDEX idx_conversation ON emails(conversation_id, received_at);
CREATE INDEX idx_mailbox ON emails(mailbox, received_at);
CREATE INDEX idx_internet_msg ON emails(internet_message_id);
CREATE INDEX idx_from ON emails(from_address);

-- Mailboxes table (for tracking which mailboxes are monitored)
CREATE TABLE mailboxes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT UNIQUE NOT NULL,
    display_name TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Separate attachments table for better normalization
CREATE TABLE attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER NOT NULL,
    attachment_id TEXT NOT NULL,
    name TEXT NOT NULL,
    size INTEGER,
    content_type TEXT,
    is_inline BOOLEAN DEFAULT 0,
    content_base64 TEXT,  -- Base64 encoded content
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE
);
```

---

## Database Recommendations

### SQLite (Current - Good for Small/Medium Scale)
- ✅ **Pros**: Simple, no server needed, file-based, perfect for single-instance apps
- ✅ **Use if**: < 100k emails, single server, simple queries
- ❌ **Cons**: Limited concurrency, no built-in replication

### PostgreSQL (Recommended for Production)
- ✅ **Pros**: Full-text search, JSON support, concurrent writes, replication
- ✅ **Use if**: > 100k emails, multiple servers, complex queries
- ✅ **Features**: `JSONB` for attachments, `tsvector` for full-text search

### MongoDB (Alternative for Document-Heavy)
- ✅ **Pros**: Native JSON storage, flexible schema, horizontal scaling
- ✅ **Use if**: Lots of attachments, varying email structures
- ❌ **Cons**: No ACID transactions (older versions), more complex queries

---

## Current Webhook → Utility Flow

```
Microsoft Graph Webhook
         ↓
Webhook Engine (FastAPI)
         ↓
Fetch Email Data (with uniqueBody)
         ↓
Match Rules (utility_rules.json)
         ↓
Enrich Employee Data (if needed)
         ↓
Load Attachments (if needed)
         ↓
Dispatch to Utility API
         ↓
Utility Stores in SQLite
```

---

## Fields You Could Add (Future Enhancements)

1. **`isRead`** - Track read status
2. **`importance`** - High/normal/low priority
3. **`categories`** - Outlook categories
4. **`flag`** - Follow-up flags
5. **`internetMessageHeaders`** - Raw headers (for advanced filtering)
6. **`replyTo`** - Reply-to addresses
7. **`webLink`** - Link to open in Outlook Web

To fetch these, update `services/graph_service.py` line 60-64:
```python
'$select': (
    'id,subject,body,uniqueBody,bodyPreview,from,toRecipients,ccRecipients,bccRecipients,'
    'receivedDateTime,sentDateTime,hasAttachments,'
    'internetMessageId,conversationId,conversationIndex,parentFolderId,'
    'isRead,importance,categories,flag,replyTo'  # Add these
),
```
