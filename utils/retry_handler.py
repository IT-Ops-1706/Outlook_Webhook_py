import asyncio
import logging
from typing import Callable, Any
import aiohttp

logger = logging.getLogger(__name__)

class RetryHandler:
    """Simple retry handler for connection failures"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def execute_with_retry(
        self,
        func: Callable,
        utility_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with retry on connection failures only.
        Retries up to 3 times with exponential backoff.
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(
                        f"Retry successful for {utility_name} on attempt {attempt + 1}"
                    )
                
                return result
            
            except (
                aiohttp.ClientConnectorError,
                aiohttp.ServerTimeoutError,
                asyncio.TimeoutError
            ) as e:
                # Only retry on connection/timeout errors
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Connection failed for {utility_name}, "
                        f"retry {attempt + 1}/{self.max_retries} after {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retries} retries exhausted for {utility_name}: {e}"
                    )
            
            except Exception as e:
                # Don't retry on other errors (4xx, 5xx responses, etc.)
                logger.error(f"Non-retryable error for {utility_name}: {e}")
                raise
        
        # All retries exhausted
        raise last_exception

# Global instance
retry_handler = RetryHandler()
