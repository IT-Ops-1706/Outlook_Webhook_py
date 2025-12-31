import logging
import os
from logging.handlers import RotatingFileHandler
from config import LOG_LEVEL, LOG_FILE

class ProductionFilter(logging.Filter):
    """Custom filter for PRODUCTION log level - shows only essential information"""
    
    def filter(self, record):
        # Always show ERROR and WARNING
        if record.levelno >= logging.WARNING:
            return True
        
        # For INFO level, filter to show only essential messages
        if record.levelno == logging.INFO:
            essential_keywords = [
                # Startup
                'Starting', 'ready', 'live', 'shutdown',
                # Subscriptions
                'subscription', 'renewed', 'created', 'verified',
                # Email processing
                '📧 Fetched:', '📎', 'matched utility',
                # Utility dispatch
                'succeeded', 'failed', 'Dispatching to',
                # Critical flow
                'Processing email:', 'Enriching employee',
                '✅ Fixed missing'
            ]
            
            message = record.getMessage().lower()
            return any(keyword.lower() in message for keyword in essential_keywords)
        
        # Block DEBUG messages in PRODUCTION mode
        return False

def setup_logging():
    """Configure application logging"""
    
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    # Determine if we're in PRODUCTION mode
    is_production = LOG_LEVEL == 'PRODUCTION'
    actual_level = logging.INFO if is_production else getattr(logging, LOG_LEVEL)
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(actual_level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(actual_level)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    
    # Add production filter if in PRODUCTION mode
    if is_production:
        console_handler.addFilter(ProductionFilter())
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(actual_level)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # Silence noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    
    return logger
