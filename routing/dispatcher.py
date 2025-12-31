import asyncio
import aiohttp
import logging
import os
import re
from typing import List
from models.email_metadata import EmailMetadata
from models.utility_config import UtilityConfig
import config

logger = logging.getLogger(__name__)

# Concurrency control
semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_FORWARDS)

class Dispatcher:
    """Simple dispatcher - forward emails to utility APIs"""
    
    @staticmethod
    async def dispatch_to_utilities(email: EmailMetadata, utilities: List[UtilityConfig]):
        """Send email to all matched utilities"""
        if not utilities:
            return
        
        logger.info(f"📤 Dispatching to {len(utilities)} utility(ies)")
        
        tasks = [
            Dispatcher._forward(email, utility)
            for utility in utilities
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log results
        for utility, result in zip(utilities, results):
            if isinstance(result, Exception):
                logger.error(f"❌ {utility.name}: {result}")
            else:
                logger.info(f"✅ {utility.name}: Success")
    
    @staticmethod
    async def _forward(email: EmailMetadata, utility: UtilityConfig):
        """POST email to utility API"""
        async with semaphore:
            timeout = aiohttp.ClientTimeout(total=utility.timeout)
            
            # Build headers
            headers = {'Content-Type': 'application/json'}
            
            # Add auth if configured
            auth_config = utility.endpoint.get('auth', {})
            if auth_config.get('type', '').lower() == 'bearer':
                token = auth_config.get('token', '')
                
                # Support env variable substitution: ${VAR_NAME}
                if token.startswith('$') or (token.startswith('{') and token.endswith('}')):
                    match = re.match(r'\$?\{?([A-Z_0-9]+)\}?', token)
                    if match:
                        token = os.getenv(match.group(1), '')
                
                if token:
                    headers['Authorization'] = f'Bearer {token}'
            
            # Prepare payload
            payload = email.to_dict()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    utility.endpoint['url'],
                    json=payload,
                    headers=headers,
                    timeout=timeout
                ) as response:
                    response.raise_for_status()
                    
                    try:
                        return await response.json()
                    except:
                        return {"status": "success"}
