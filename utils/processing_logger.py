import logging
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import os

logger = logging.getLogger(__name__)

class ProcessingLogger:
    """
    Log email processing flow from webhook notification to utility API calls.
    Logs to both file and optionally to database.
    """
    
    def __init__(self):
        self.log_dir = Path('logs/processing')
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if database API is configured
        self.db_api_url = os.getenv('DATABASE_API_URL')
        self.use_database = self.db_api_url is not None
    
    def log_notification_received(self, notification_count: int):
        """Log when webhook notification is received"""
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'notification_received',
            'notification_count': notification_count
        }
        self._write_log(entry)
    
    def log_email_fetched(self, email_data: dict):
        """Log when email is fetched from Graph API"""
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'email_fetched',
            'internet_message_id': email_data.get('internet_message_id'),
            'subject': email_data.get('subject', '')[:100],
            'from': email_data.get('from_address'),
            'mailbox': email_data.get('mailbox'),
            'has_attachments': email_data.get('has_attachments')
        }
        self._write_log(entry)
    
    def log_utilities_matched(
        self, 
        internet_message_id: str,
        utilities: List[str]
    ):
        """Log which utilities matched the email"""
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'utilities_matched',
            'internet_message_id': internet_message_id,
            'matched_utilities': utilities,
            'count': len(utilities)
        }
        self._write_log(entry)
    
    def log_utility_call_start(
        self,
        internet_message_id: str,
        utility_name: str,
        endpoint: str
    ):
        """Log when utility API call starts"""
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'utility_call_start',
            'internet_message_id': internet_message_id,
            'utility_name': utility_name,
            'endpoint': endpoint
        }
        self._write_log(entry)
    
    def log_utility_call_success(
        self,
        internet_message_id: str,
        utility_name: str,
        response_time_ms: int,
        retry_count: int = 0
    ):
        """Log successful utility API call"""
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'utility_call_success',
            'internet_message_id': internet_message_id,
            'utility_name': utility_name,
            'response_time_ms': response_time_ms,
            'retry_count': retry_count
        }
        self._write_log(entry)
    
    def log_utility_call_failure(
        self,
        internet_message_id: str,
        utility_name: str,
        error: str,
        retry_count: int = 0
    ):
        """Log failed utility API call"""
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'utility_call_failure',
            'internet_message_id': internet_message_id,
            'utility_name': utility_name,
            'error': str(error),
            'retry_count': retry_count
        }
        self._write_log(entry)
    
    def log_processing_complete(
        self,
        internet_message_id: str,
        total_time_ms: int,
        success_count: int,
        failure_count: int
    ):
        """Log when complete processing finishes"""
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'processing_complete',
            'internet_message_id': internet_message_id,
            'total_time_ms': total_time_ms,
            'success_count': success_count,
            'failure_count': failure_count
        }
        self._write_log(entry)
    
    def _write_log(self, entry: dict):
        """Write log entry to file and optionally database"""
        # Write to daily log file
        log_file = self.log_dir / f"processing_{datetime.utcnow().strftime('%Y%m%d')}.jsonl"
        
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write processing log: {e}")
        
        # TODO: Also write to database when DB API is ready
        # if self.use_database:
        #     await self._send_to_database(entry)

# Global instance
processing_logger = ProcessingLogger()
