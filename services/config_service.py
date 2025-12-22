import json
import logging
from typing import List
from pathlib import Path
from models.utility_config import UtilityConfig
import config

logger = logging.getLogger(__name__)

class ConfigService:
    """Load utility configurations from JSON or database"""
    
    def __init__(self):
        self.use_database = config.USE_DATABASE_CONFIG
        self.json_path = Path('config/utility_rules.json')
        self._cache = None
        self._cache_time = 0
        self._cache_ttl = 300  # 5 minutes
    
    async def get_all_utilities(self) -> List[UtilityConfig]:
        """Load all utility configurations (cached)"""
        import time
        current_time = time.time()
        
        # Return cached if still valid
        if self._cache and (current_time - self._cache_time) < self._cache_ttl:
            logger.debug("Returning cached utility configurations")
            return self._cache
        
        logger.info("Loading utility configurations")
        
        if self.use_database:
            utilities = await self._load_from_database()
        else:
            utilities = self._load_from_json()
        
        # Update cache
        self._cache = utilities
        self._cache_time = current_time
        
        enabled_count = sum(1 for u in utilities if u.enabled)
        logger.info(f"Loaded {len(utilities)} utilities ({enabled_count} enabled)")
        
        return utilities
    
    def _load_from_json(self) -> List[UtilityConfig]:
        """Load from JSON file"""
        try:
            with open(self.json_path, 'r') as f:
                data = json.load(f)
            
            utilities = [
                UtilityConfig.from_dict(u)
                for u in data.get('utilities', [])
            ]
            
            return utilities
        
        except FileNotFoundError:
            logger.warning(f"Config file not found: {self.json_path}")
            return []
        except Exception as e:
            logger.error(f"Error loading JSON config: {e}")
            raise
    
    async def _load_from_database(self) -> List[UtilityConfig]:
        """Load from database via API (future implementation)"""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{config.DATABASE_API_URL}/api/utilities') as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    return [UtilityConfig.from_dict(u) for u in data]
        
        except Exception as e:
            logger.error(f"Error loading from database: {e}")
            raise

# Global instance
config_service = ConfigService()
