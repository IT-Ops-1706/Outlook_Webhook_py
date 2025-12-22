from dataclasses import dataclass, asdict, field
from typing import List, Optional
from datetime import datetime

@dataclass
class EmailMetadata:
    """Complete email metadata from Microsoft Graph"""
    
    # Microsoft Graph IDs
    message_id: str
    internet_message_id: str
    conversation_id: str
    conversation_index: str
    
    # Content
    subject: str
    body_preview: str
    body_content: str
    body_type: str  # 'html' or 'text'
    
    # Participants
    from_address: str
    from_name: str
    to_recipients: List[dict] = field(default_factory=list)
    cc_recipients: List[dict] = field(default_factory=list)
    bcc_recipients: List[dict] = field(default_factory=list)
    
    # Timestamps
    received_datetime: datetime = None
    sent_datetime: datetime = None
    
    # Attachments
    has_attachments: bool = False
    attachments: List[dict] = field(default_factory=list)
    
    # Context
    mailbox: str = ""
    folder: str = "Inbox"  # 'Inbox', 'Sent Items', etc.
    
    @property
    def direction(self) -> str:
        """Determine if email is received or sent"""
        return 'sent' if self.folder == 'Sent Items' else 'received'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        import base64
        
        data = asdict(self)
        data['direction'] = self.direction
        
        # Convert datetime to ISO format
        if self.received_datetime:
            data['received_datetime'] = self.received_datetime.isoformat()
        if self.sent_datetime:
            data['sent_datetime'] = self.sent_datetime.isoformat()
        
        # Handle attachment bytes - convert to base64 string for JSON
        if data.get('attachments'):
            for attachment in data['attachments']:
                if 'content' in attachment and isinstance(attachment['content'], bytes):
                    # Convert bytes to base64 string
                    attachment['content'] = base64.b64encode(attachment['content']).decode('utf-8')
        
        return data
