import asyncio
import aiohttp
import logging
from typing import List
from models.email_metadata import EmailMetadata
from models.utility_config import UtilityConfig
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
        
        logger.info(f"Dispatching to {len(utilities)} utilities: {[u.name for u in utilities]}")
        
        tasks = [
            Dispatcher._forward_to_utility(email, utility)
            for utility in utilities
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log results
        for utility, result in zip(utilities, results):
            if isinstance(result, Exception):
                logger.error(f"Utility '{utility.name}' failed: {result}")
            else:
                logger.info(f"Utility '{utility.name}' succeeded")
    
    @staticmethod
    async def _forward_to_utility(email: EmailMetadata, utility: UtilityConfig):
        """POST to utility API with rate limiting"""
        async with semaphore:
            try:
                timeout = aiohttp.ClientTimeout(total=utility.timeout)
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        utility.endpoint['url'],
                        json=email.to_dict(),
                        timeout=timeout
                    ) as response:
                        response.raise_for_status()
                        return await response.json()
            
            except asyncio.TimeoutError:
                logger.error(f"Timeout calling utility '{utility.name}'")
                raise
            except Exception as e:
                logger.error(f"Error calling utility '{utility.name}': {e}")
                raise
