# Build Multi-Keyword Tracker Utility - Complete Guide

## Overview

**What it does:**
1. Searches for specific keywords in email subject and body
2. **Enriches with employee data** (department, office, location) from Microsoft 365
3. Tracks keyword matches with employee context
4. Stores conversation threading

**Use Case:** Track important keywords (e.g., "urgent", "critical", "escalation") and know which department/location they're from.

---

## Employee Data Enrichment

### Automatic Enrichment

The webhook system will automatically enrich emails with employee data for:
- **Sender** (from_address)
- **All recipients** (to_recipients, cc_recipients)

### Available Employee Fields

```json
{
  "sender_employee_data": {
    "email": "john.doe@company.com",
    "display_name": "John Doe",
    "department": "IT Operations",
    "office_location": "Building A, Floor 3",
    "city": "Mumbai",
    "country": "India",
    "job_title": "Senior Engineer"
  },
  "recipient_employee_data": [
    {
      "email": "jane.smith@company.com",
      "department": "Finance",
      ...
    }
  ]
}
```

**Note:** Only works for users in your Microsoft 365 organization. External emails will have `null`.

---

## Step 1: Project Setup (10 min)

```bash
cd c:\Webhook_mail
mkdir Keyword_Tracker
cd Keyword_Tracker
python -m venv venv
venv\Scripts\activate
pip install fastapi uvicorn python-dotenv httpx pydantic sqlalchemy aiosqlite
mkdir models services utils database
```

---

## Step 2: Configuration

**File: `config.py`**
```python
import os
from dotenv import load_dotenv

load_dotenv()

# Authentication
API_BEARER_KEY = os.getenv('API_BEARER_KEY')

# Database
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./keywords.db')

# Tracked Keywords (comma-separated)
TRACKED_KEYWORDS = os.getenv('TRACKED_KEYWORDS', 'urgent,critical,escalation,asap').split(',')

# Server
PORT = int(os.getenv('PORT', 8002))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
```

**File: `.env`**
```bash
API_BEARER_KEY=your-bearer-key-here
DATABASE_URL=sqlite+aiosqlite:///./keywords.db
TRACKED_KEYWORDS=urgent,critical,escalation,asap,important
PORT=8002
LOG_LEVEL=INFO
```

---

## Step 3: Database Models

**File: `database/models.py`**
```python
from sqlalchemy import Column, String, DateTime, Integer, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class KeywordMatch(Base):
    __tablename__ = "keyword_matches"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Email IDs
    message_id = Column(String, index=True)
    internet_message_id = Column(String, index=True)
    conversation_id = Column(String, index=True)
    
    # Email content
    subject = Column(String)
    body_preview = Column(Text)
    
    # Keyword info
    matched_keywords = Column(JSON)  # List of matched keywords
    keyword_locations = Column(JSON)  # Where keywords were found
    
    # Sender info
    from_address = Column(String, index=True)
    from_name = Column(String)
    
    # Employee data (if available)
    sender_department = Column(String, index=True)
    sender_office = Column(String)
    sender_city = Column(String)
    sender_country = Column(String)
    sender_job_title = Column(String)
    
    # Recipients
    to_recipients = Column(JSON)
    cc_recipients = Column(JSON)
    
    # Timestamps
    received_datetime = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Mailbox context
    mailbox = Column(String, index=True)
    folder = Column(String)
```

**File: `database/db.py`**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from database.models import Base
import config

engine = create_async_engine(config.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    """Initialize database"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        yield session
```

---

## Step 4: Input Models

**File: `models/email_input.py`**
```python
from pydantic import BaseModel
from typing import List, Optional

class EmployeeData(BaseModel):
    """Employee information from Microsoft 365"""
    email: str
    display_name: str = ""
    department: str = ""
    office_location: str = ""
    city: str = ""
    country: str = ""
    job_title: str = ""

class EmailRecipient(BaseModel):
    address: str
    name: str = ""

class EmailInput(BaseModel):
    """Email data from webhook with employee enrichment"""
    
    # Email IDs
    message_id: str
    internet_message_id: str
    conversation_id: str = ""
    
    # Content
    subject: str
    body_preview: str = ""
    body_content: str = ""
    
    # Sender
    from_address: str
    from_name: str = ""
    
    # Recipients
    to_recipients: List[EmailRecipient] = []
    cc_recipients: List[EmailRecipient] = []
    
    # Timestamps
    received_datetime: Optional[str] = None
    
    # Context
    mailbox: str
    folder: str = "Inbox"
    
    # Employee data (enriched by webhook)
    sender_employee_data: Optional[EmployeeData] = None
    recipient_employee_data: List[EmployeeData] = []
```

---

## Step 5: Keyword Processor

**File: `services/keyword_processor.py`**
```python
import re
import logging
from datetime import datetime
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import KeywordMatch
import config

logger = logging.getLogger(__name__)

class KeywordProcessor:
    """Process emails for keyword tracking"""
    
    def __init__(self):
        self.keywords = [kw.strip().lower() for kw in config.TRACKED_KEYWORDS]
    
    async def process_email(self, email_data: dict, db: AsyncSession) -> dict:
        """
        Process email for keyword matches
        
        Steps:
        1. Search for keywords in subject and body
        2. Extract employee data
        3. Store in database
        4. Return match summary
        """
        try:
            # Step 1: Find keyword matches
            matches = self._find_keywords(
                email_data['subject'],
                email_data.get('body_content', '')
            )
            
            if not matches['keywords']:
                return {
                    "status": "no_match",
                    "message": "No tracked keywords found"
                }
            
            logger.info(f"Found keywords: {matches['keywords']} in email from {email_data['from_address']}")
            
            # Step 2: Extract employee data
            sender_employee = email_data.get('sender_employee_data', {}) or {}
            
            # Step 3: Store in database
            keyword_match = KeywordMatch(
                message_id=email_data['message_id'],
                internet_message_id=email_data['internet_message_id'],
                conversation_id=email_data.get('conversation_id', ''),
                
                subject=email_data['subject'],
                body_preview=email_data.get('body_preview', ''),
                
                matched_keywords=matches['keywords'],
                keyword_locations=matches['locations'],
                
                from_address=email_data['from_address'],
                from_name=email_data.get('from_name', ''),
                
                # Employee data
                sender_department=sender_employee.get('department', ''),
                sender_office=sender_employee.get('office_location', ''),
                sender_city=sender_employee.get('city', ''),
                sender_country=sender_employee.get('country', ''),
                sender_job_title=sender_employee.get('job_title', ''),
                
                to_recipients=[r for r in email_data.get('to_recipients', [])],
                cc_recipients=[r for r in email_data.get('cc_recipients', [])],
                
                received_datetime=datetime.fromisoformat(email_data['received_datetime']) if email_data.get('received_datetime') else None,
                
                mailbox=email_data['mailbox'],
                folder=email_data.get('folder', 'Inbox')
            )
            
            db.add(keyword_match)
            await db.commit()
            await db.refresh(keyword_match)
            
            logger.info(f"Stored keyword match ID: {keyword_match.id}")
            
            return {
                "status": "success",
                "match_id": keyword_match.id,
                "keywords_found": matches['keywords'],
                "sender": {
                    "email": email_data['from_address'],
                    "department": sender_employee.get('department', 'Unknown'),
                    "office": sender_employee.get('office_location', 'Unknown'),
                    "city": sender_employee.get('city', 'Unknown')
                },
                "subject": email_data['subject'][:100]
            }
        
        except Exception as e:
            logger.error(f"Error processing email: {e}", exc_info=True)
            await db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _find_keywords(self, subject: str, body: str) -> Dict[str, List]:
        """Find keywords in subject and body"""
        
        subject_lower = subject.lower()
        body_lower = body.lower()
        
        found_keywords = []
        locations = {}
        
        for keyword in self.keywords:
            keyword_lower = keyword.lower()
            
            # Check subject
            if keyword_lower in subject_lower:
                found_keywords.append(keyword)
                locations[keyword] = locations.get(keyword, [])
                locations[keyword].append('subject')
            
            # Check body
            if keyword_lower in body_lower:
                if keyword not in found_keywords:
                    found_keywords.append(keyword)
                locations[keyword] = locations.get(keyword, [])
                locations[keyword].append('body')
        
        return {
            "keywords": found_keywords,
            "locations": locations
        }

# Global instance
processor = KeywordProcessor()
```

---

## Step 6: FastAPI App

**File: `main.py`**
```python
from fastapi import FastAPI, Depends, HTTPException
import logging
import uvicorn

from models.email_input import EmailInput
from services.keyword_processor import processor
from utils.auth import verify_bearer_token
from database.db import init_db, get_db
from sqlalchemy.ext.asyncio import AsyncSession
import config

# Configure logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Multi-Keyword Tracker",
    description="Track keywords in emails with employee context",
    version="1.0.0"
)

@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    await init_db()
    logger.info("Database initialized")
    logger.info(f"Tracking keywords: {config.TRACKED_KEYWORDS}")

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "service": "keyword_tracker",
        "version": "1.0.0",
        "tracked_keywords": config.TRACKED_KEYWORDS
    }

@app.post("/process")
async def process_email(
    email: EmailInput,
    db: AsyncSession = Depends(get_db),
    auth: str = Depends(verify_bearer_token)
):
    """
    Process email for keyword tracking
    
    Searches for tracked keywords and stores matches with employee context
    """
    try:
        logger.info(f"Processing email: {email.subject[:50]}... from {email.from_address}")
        
        # Convert to dict
        email_dict = email.model_dump()
        
        # Process email
        result = await processor.process_email(email_dict, db)
        
        logger.info(f"Processing result: {result['status']}")
        
        return result
    
    except Exception as e:
        logger.error(f"Error in process endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Multi-Keyword Tracker",
        "version": "1.0.0",
        "tracked_keywords": config.TRACKED_KEYWORDS,
        "endpoints": {
            "health": "/health",
            "process": "/process (POST, requires Bearer token)"
        }
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=True)
```

**File: `utils/auth.py`** - Same as before (Bearer token verification)

---

## Step 7: Webhook Configuration

**Update `config/utility_rules.json` in webhook:**

```json
{
  "id": "keyword_tracker",
  "name": "Multi-Keyword Tracker",
  "enabled": true,
  
  "subscriptions": {
    "mailboxes": [
      {"address": "it.ops@babajishivram.com", "folders": ["Inbox"]}
    ]
  },
  
  "pre_filters": {
    "condition_groups": [
      {
        "name": "Keyword Filters",
        "logic": "OR",
        "conditions": [
          {"field": "subject", "operator": "contains", "value": "urgent"},
          {"field": "subject", "operator": "contains", "value": "critical"},
          {"field": "subject", "operator": "contains", "value": "escalation"},
          {"field": "body_content", "operator": "contains", "value": "urgent"},
          {"field": "body_content", "operator": "contains", "value": "critical"}
        ]
      }
    ],
    "group_logic": "AND"
  },
  
  "endpoint": {
    "url": "https://keyword-tracker.onrender.com/process",
    "method": "POST",
    "auth": {
      "type": "bearer",
      "token": "your-utility-bearer-token"
    }
  },
  
  "timeout": 30,
  
  "enrich_employee_data": true
}
```

---

## Step 8: Deploy

**File: `requirements.txt`**
```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-dotenv==1.0.0
pydantic==2.5.0
httpx==0.26.0
sqlalchemy[asyncio]==2.0.23
aiosqlite==0.19.0
```

**Deploy to Render:**
1. Push to GitHub
2. Create Render web service
3. Set environment variables
4. Deploy

---

## Summary

**What you built:**
- ✅ Multi-keyword tracker
- ✅ Employee data enrichment (department, office, location)
- ✅ Database storage with threading
- ✅ Real-time keyword detection
- ✅ Queryable history

**Next steps:**
1. Add query endpoints (search by keyword, department, etc.)
2. Add notifications/alerts
3. Build dashboard UI

**Estimated time:** 2-3 hours
