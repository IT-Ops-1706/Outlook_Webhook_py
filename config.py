import os
from dotenv import load_dotenv

load_dotenv()

# Microsoft Graph
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
TENANT_ID = os.getenv('TENANT_ID')

# Webhook
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
WEBHOOK_CLIENT_STATE = os.getenv('WEBHOOK_CLIENT_STATE', 'SecretClientState')
PORT = int(os.getenv('PORT', 8000))

# Security - Admin API Authentication
API_BEARER_KEY = os.getenv('API_BEARER_KEY')

# Database API
DATABASE_API_URL = os.getenv('DATABASE_API_URL')
USE_DATABASE_CONFIG = os.getenv('USE_DATABASE_CONFIG', 'false').lower() == 'true'

# Processing
MAX_CONCURRENT_FORWARDS = int(os.getenv('MAX_CONCURRENT_FORWARDS', 25))
BATCH_SIZE = int(os.getenv('BATCH_SIZE', 10))
DEDUPLICATION_TTL = int(os.getenv('DEDUPLICATION_TTL', 300))

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
