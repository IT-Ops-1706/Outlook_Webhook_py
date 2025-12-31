from fastapi import APIRouter, Request, Query
from fastapi.responses import PlainTextResponse
import asyncio
import logging
from typing import Optional

from services.config_service import config_service
from services.email_fetcher import email_fetcher
from routing.rule_matcher import RuleMatcher
from routing.dispatcher import Dispatcher
import config

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/webhook")
async def webhook_notification(
    request: Request,
    validationToken: Optional[str] = Query(None)
):
    """Handle Microsoft Graph webhook notifications"""
    
    # Validation token challenge (subscription setup)
    if validationToken:
        logger.info(f"Validation token received")
        return PlainTextResponse(content=validationToken, status_code=200)
    
    data = await request.json()
    notifications = data.get('value', [])
    
    logger.info(f"📬 Received {len(notifications)} webhook notification(s)")
    
    # Fire and forget - respond immediately to Microsoft
    asyncio.create_task(process_notifications(notifications))
    
    return {"status": "accepted", "count": len(notifications)}

async def process_notifications(notifications: list):
    """Process all notifications - NO DEDUPLICATION, forward everything"""
    try:
        utilities = await config_service.get_all_utilities()
        
        if not utilities:
            logger.warning("No utilities configured")
            return
        
        # Process each notification
        for notification in notifications:
            await process_single_email(notification, utilities)
    
    except Exception as e:
        logger.error(f"Error in background processing: {e}", exc_info=True)

async def process_single_email(notification: dict, utilities: list):
    """Fetch email, match rules, forward to utilities"""
    try:
        # Step 1: Fetch email data from Graph API
        email = await email_fetcher.fetch_email(notification)
        
        if not email:
            logger.warning("Failed to fetch email data")
            return
        
        # Step 1.5: Check for duplicates (safety net for Exchange)
        from utils.deduplication import simple_deduplicator
        if simple_deduplicator.is_duplicate(email.internet_message_id, email.folder):
            logger.info(f"⏭️  Skipping duplicate: {email.subject[:50]}")
            return
        
        logger.info(f"📧 Email: '{email.subject}' | From: {email.from_address} | Folder: {email.folder}")
        
        # Step 2: Match against utility rules
        matched = await RuleMatcher.find_matching_utilities(email, utilities)
        
        if not matched:
            logger.debug(f"Email matched no utilities, skipping")
            return
        
        # Step 3: Load attachments if needed
        if email.has_attachments:
            email = await email_fetcher.load_attachments(email)
        
        # Step 4: Enrich employee data if any utility needs it
        needs_enrichment = any(u.enrich_employee_data for u in matched)
        if needs_enrichment:
            email = await enrich_employee_data(email)
        
        # Step 5: Forward to matched utilities
        await Dispatcher.dispatch_to_utilities(email, matched)
    
    except Exception as e:
        logger.error(f"Error processing email: {e}", exc_info=True)

async def enrich_employee_data(email):
    """Add employee details from Microsoft 365"""
    from services.graph_service import graph_service
    
    # Enrich sender
    if email.from_address:
        sender_details = graph_service.fetch_user_details(email.from_address)
        if sender_details:
            email.sender_employee_data = sender_details
    
    # Enrich recipients
    email.recipient_employee_data = []
    for recipient in email.to_recipients:
        recipient_email = recipient.get('address')
        if recipient_email:
            details = graph_service.fetch_user_details(recipient_email)
            if details:
                email.recipient_employee_data.append({
                    'email': recipient_email,
                    'name': recipient.get('name'),
                    **details
                })
    
    return email
