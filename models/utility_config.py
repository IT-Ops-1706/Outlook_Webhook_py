from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class UtilityConfig:
    """Utility configuration loaded from JSON or database"""
    
    id: str
    name: str
    enabled: bool
    
    subscriptions: Dict
    pre_filters: Dict
    endpoint: Dict
    timeout: int = 10
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            enabled=data.get('enabled', True),
            subscriptions=data.get('subscriptions', {}),
            pre_filters=data.get('pre_filters', {}),
            endpoint=data.get('endpoint', {}),
            timeout=data.get('timeout', 10)
        )
