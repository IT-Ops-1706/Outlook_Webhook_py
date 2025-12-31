from fastapi import APIRouter, Request, Query
from fastapi.responses import PlainTextResponse
import asyncio
import logging
import time
from typing import Optional

from services.config_service import config_service
from services.email_fetcher import email_fetcher
from routing.rule_matcher import RuleMatcher
from routing.dispatcher import Dispatcher
from utils.deduplication import deduplicator, internet_message_deduplicator
from utils.webhook_validator import webhook_validator
from utils.processing_logger import processing_logger
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
        logger.info(f"Validation token received: {validationToken}")
        return PlainTextResponse(content=validationToken, status_code=200)
    
    data = await request.json()
    notifications = data.get('value', [])
    
    # Validate webhook signature/client state
    try:
        await webhook_validator.validate_notification(data)
    except Exception as e:
        logger.error(f"Webhook validation failed: {e}")
        raise
    
    logger.info(f"Received {len(notifications)} webhook notifications")
    
    # Log notification received
    processing_logger.log_notification_received(len(notifications))
    
    # Fire and forget - respond immediately to Microsoft
    asyncio.create_task(process_notifications(notifications))
    
    return {"status": "accepted", "count": len(notifications)}

async def process_notifications(notifications: list):
    """Process notifications in background"""
    try:
        # Step 1: Deduplicate
        unique = deduplicator.deduplicate(notifications)
        
        if not unique:
            logger.info("No unique notifications to process")
            return
        
        # Step 2: Load utility configurations
        utilities = await config_service.get_all_utilities()
        
        if not utilities:
            logger.warning("No utilities configured")
            return
        
        # Step 3: Process in batches
        batch_size = config.BATCH_SIZE
        
        for i in range(0, len(unique), batch_size):
            batch = unique[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch)} emails")
            
            tasks = [process_single_email(n, utilities) for n in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    except Exception as e:
        logger.error(f"Error in background processing: {e}", exc_info=True)

async def process_single_email(notification: dict, utilities: list):
    """Process a single email notification"""
    start_time = time.time()
    
    try:
        # Step 1: Fetch metadata only (fast, small memory footprint)
        email = await email_fetcher.fetch_email_metadata(notification)
        
        # Step 1.5: Check for duplicate using Internet Message ID + Folder
        # Same email can appear in Inbox AND Sent Items - we need BOTH
        if not internet_message_deduplicator.is_unique(email.internet_message_id, email.folder):
            logger.info(f"⚠️  Duplicate email detected (Same ID in {email.folder}): {email.subject[:50]}")
            return  # Skip this duplicate
        
        # Log email fetched
        processing_logger.log_email_fetched(email.to_dict())
        
        logger.info(f"Processing email: '{email.subject[:50]}' from {email.from_address}")
        
        # Debug: Log basic processing info
        logger.debug(f"📬 WEBHOOK NOTIFICATION - Processing '{email.subject[:50]}'")
        logger.debug(f"   Internal ID: {email.message_id}")
        
        # Step 2: Match to utilities (uses metadata only, no attachments needed)
        matched = await RuleMatcher.find_matching_utilities(email, utilities)
        
        if not matched:
            logger.debug(f"Email matched no utilities, skipping")
            return  # Exit early - no attachment download! Memory saved ✓
        
        # Step 3: Enrich employee data if any matched utility needs it
        needs_enrichment = any(u.enrich_employee_data for u in matched)
        
        if needs_enrichment:
            logger.info(f"Enriching employee data for matched utilities")
            from services.graph_service import graph_service
            
            # Enrich sender if internal
            if email.from_address:
                sender_details = graph_service.fetch_user_details(email.from_address)
                if sender_details:
                    email.sender_employee_data = sender_details
                    logger.debug(f"Enriched sender: {email.from_address} → {sender_details}")
            
            # Enrich recipients if internal
            email.recipient_employee_data = []
            for recipient in email.to_recipients:
                recipient_email = recipient.get('address')
                if recipient_email:
                    recipient_details = graph_service.fetch_user_details(recipient_email)
                    if recipient_details:
                        email.recipient_employee_data.append({
                            'email': recipient_email,
                            'name': recipient.get('name'),
                            **recipient_details
                        })
                        logger.debug(f"Enriched recipient: {recipient_email}")

        
        # Step 4: Load attachments ONLY if email matched utilities
        if email.has_attachments and not email.attachments_loaded:
            logger.info(f"Loading {len(email.attachment_metadata)} attachments for matched email")
            email = await email_fetcher.load_attachments(email)
        
        # Step 5: Dispatch to matched utilities
        result = await Dispatcher.dispatch_to_utilities(email, matched)
        
        # Log processing complete
        total_time_ms = int((time.time() - start_time) * 1000)
        processing_logger.log_processing_complete(
            email.internet_message_id,
            total_time_ms,
            result.get('success_count', 0) if result else 0,
            result.get('failure_count', 0) if result else 0
        )
    
    except Exception as e:
        logger.error(f"Error processing email: {e}", exc_info=True)
