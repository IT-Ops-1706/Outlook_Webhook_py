import asyncio
import aiohttp
import logging
import time
from typing import List
from models.email_metadata import EmailMetadata
from models.utility_config import UtilityConfig
from utils.retry_handler import retry_handler
from utils.processing_logger import processing_logger
import config

logger = logging.getLogger(__name__)

# Concurrency control
semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_FORWARDS)

class Dispatcher:
    """Dispatch emails to utility APIs"""
    
    @staticmethod
    async def dispatch_to_utilities(
        email: EmailMetadata,
        utilities: List[UtilityConfig]
    ):
        """Send email to all matched utilities in parallel"""
        if not utilities:
            return
        
        utility_names = [u.name for u in utilities]
        logger.info(f"Dispatching to {len(utilities)} utilities: {utility_names}")
        
        # Log matched utilities
        processing_logger.log_utilities_matched(
            email.internet_message_id,
            utility_names
        )
        
        tasks = [
            Dispatcher._forward_to_utility(email, utility)
            for utility in utilities
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes and failures
        success_count = 0
        failure_count = 0
        
        # Log results
        for utility, result in zip(utilities, results):
            if isinstance(result, Exception):
                logger.error(f"Utility '{utility.name}' failed: {result}")
                failure_count += 1
            else:
                logger.info(f"Utility '{utility.name}' succeeded")
                success_count += 1
        
        return {
            'success_count': success_count,
            'failure_count': failure_count
        }
    
    @staticmethod
    async def _forward_to_utility(email: EmailMetadata, utility: UtilityConfig):
        """POST to utility API with rate limiting, retry, and logging"""
        async with semaphore:
            start_time = time.time()
            
            # Log call start
            processing_logger.log_utility_call_start(
                email.internet_message_id,
                utility.name,
                utility.endpoint['url']
            )
            
            async def call_utility():
                timeout = aiohttp.ClientTimeout(total=utility.timeout)
                
                # Build headers
                headers = {'Content-Type': 'application/json'}
                
                # Add authentication if configured
                auth_config = utility.endpoint.get('auth', {})
                if auth_config:
                    auth_type = auth_config.get('type', '').lower()
                    if auth_type == 'bearer':
                        token = auth_config.get('token', '')
                        
                        # Support environment variable substitution
                        # Format: ${ENV_VAR_NAME} or {ENV_VAR_NAME}
                        if token.startswith('$') or (token.startswith('{') and token.endswith('}')):
                            import os
                            import re
                            # Extract env var name
                            match = re.match(r'\$?\{?([A-Z_0-9]+)\}?', token)
                            if match:
                                env_var = match.group(1)
                                token = os.getenv(env_var, '')
                                if not token:
                                    logger.warning(f"Environment variable {env_var} not found for utility {utility.name}")
                        
                        if token:
                            headers['Authorization'] = f'Bearer {token}'
                            logger.debug(f"Added bearer token auth for {utility.name}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        utility.endpoint['url'],
                        json=email.to_dict(),
                        headers=headers,
                        timeout=timeout
                    ) as response:
                        response.raise_for_status()
                        
                        # Try to parse JSON, but accept any successful response
                        try:
                            return await response.json()
                        except:
                            # Non-JSON response (e.g., webhook.site returns HTML)
                            return {"status": "success", "response": await response.text()}
            
            try:
                # Execute with retry (3 attempts for connection failures)
                result = await retry_handler.execute_with_retry(
                    call_utility,
                    utility.name
                )
                
                # Log success
                response_time_ms = int((time.time() - start_time) * 1000)
                processing_logger.log_utility_call_success(
                    email.internet_message_id,
                    utility.name,
                    response_time_ms
                )
                
                return result
            
            except Exception as e:
                # Log failure
                processing_logger.log_utility_call_failure(
                    email.internet_message_id,
                    utility.name,
                    str(e)
                )
                
                logger.error(f"Error calling utility '{utility.name}': {e}")
                raise
