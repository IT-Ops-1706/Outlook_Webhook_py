"""
Quick test to verify rule matching logic
"""
import asyncio
from models.email_metadata import EmailMetadata
from routing.rule_matcher import RuleMatcher
from services.config_service import config_service
from datetime import datetime

async def test_matching():
    # Create test email that matches your scenario
    test_email = EmailMetadata(
        message_id="test123",
        internet_message_id="<test@example.com>",
        conversation_id="conv123",
        conversation_index="index123",
        subject="rate request",  # Exact subject from logs
        body_preview="test",
        body_content="test body",
        unique_body_content="",
        body_type="html",
        from_address="it.ops@babajishivram.com",
        from_name="IT Ops",
        to_recipients=[],
        cc_recipients=[],
        bcc_recipients=[],
        received_datetime=datetime.now(),
        sent_datetime=datetime.now(),
        has_attachments=False,
        attachment_metadata=[],
        attachments=[],
        mailbox="it.ops@babajishivram.com",  # This is what should be in email.mailbox
        folder="Sent Items"
    )
    
    # Load utilities
    utilities = await config_service.get_all_utilities()
    
    print(f"Loaded {len(utilities)} utilities")
    for util in utilities:
        print(f"\nUtility: {util.name}")
        print(f"Enabled: {util.enabled}")
        print(f"Subscribed mailboxes: {util.subscriptions.get('mailboxes', [])}")
    
    # Test matching
    matched = await RuleMatcher.find_matching_utilities(test_email, utilities)
    
    print(f"\n{'='*60}")
    print(f"Test Email:")
    print(f"  Subject: {test_email.subject}")
    print(f"  From: {test_email.from_address}")
    print(f"  Mailbox: {test_email.mailbox}")
    print(f"  Folder: {test_email.folder}")
    print(f"\nMatched {len(matched)} utilities:")
    for util in matched:
        print(f"  - {util.name}")
    
    if not matched:
        print("\n❌ NO MATCH - This is the problem!")
    else:
        print("\n✅ MATCHED - Rule matching is working")

if __name__ == "__main__":
    asyncio.run(test_matching())
