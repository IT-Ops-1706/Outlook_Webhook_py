from fastapi import APIRouter, HTTPException, Header, Depends
from typing import List, Optional, Dict, Any
from models.utility_config import UtilityConfig
from services.config_service import config_service
from services.subscription_manager import subscription_manager
import json
import os
import logging
import re

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/utilities", tags=["Utility Management"])

CONFIG_FILE = "config/utility_rules.json"


# Authentication dependency
async def verify_admin_token(x_admin_token: str = Header(..., alias="X-Admin-Token")):
    """Verify admin API token from header"""
    admin_token = os.getenv("ADMIN_API_TOKEN")
    if not admin_token:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_API_TOKEN not configured on server"
        )
    if x_admin_token != admin_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin token"
        )
    return True


def validate_utility_id(utility_id: str) -> bool:
    """Validate utility ID format (alphanumeric + underscores)"""
    return bool(re.match(r'^[a-zA-Z0-9_]+$', utility_id))


def load_config() -> dict:
    """Load utility configuration from JSON file"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise HTTPException(status_code=500, detail="Failed to load configuration")


def save_config(config: dict) -> None:
    """Save utility configuration to JSON file"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info("Configuration saved successfully")
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        raise HTTPException(status_code=500, detail="Failed to save configuration")


@router.get("/", summary="List all utilities")
async def list_utilities():
    """
    Get all utility configurations.
    
    Returns a list of all configured utilities with their settings.
    No authentication required for read operations.
    """
    try:
        utilities = await config_service.get_all_utilities()
        return {
            "count": len(utilities),
            "utilities": [
                {
                    "id": u.id,
                    "name": u.name,
                    "enabled": u.enabled,
                    "subscriptions": u.subscriptions,
                    "pre_filters": u.pre_filters,
                    "endpoint": u.endpoint,
                    "timeout": u.timeout,
                    "enrich_employee_data": u.enrich_employee_data
                }
                for u in utilities
            ]
        }
    except Exception as e:
        logger.error(f"Error listing utilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{utility_id}", summary="Get utility by ID")
async def get_utility(utility_id: str):
    """
    Get a single utility configuration by ID.
    
    Args:
        utility_id: The unique identifier of the utility
        
    Returns:
        The utility configuration object
        
    Raises:
        404: If utility not found
    """
    try:
        utilities = await config_service.get_all_utilities()
        utility = next((u for u in utilities if u.id == utility_id), None)
        
        if not utility:
            raise HTTPException(
                status_code=404,
                detail=f"Utility '{utility_id}' not found"
            )
        
        return {
            "id": utility.id,
            "name": utility.name,
            "enabled": utility.enabled,
            "subscriptions": utility.subscriptions,
            "pre_filters": utility.pre_filters,
            "endpoint": utility.endpoint,
            "timeout": utility.timeout,
            "enrich_employee_data": utility.enrich_employee_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting utility {utility_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", status_code=201, summary="Create new utility")
async def create_utility(
    utility_data: Dict[str, Any],
    _: bool = Depends(verify_admin_token)
):
    """
    Create a new utility configuration.
    
    Requires X-Admin-Token header for authentication.
    Automatically creates necessary webhook subscriptions.
    
    Args:
        utility_data: Complete utility configuration object
        
    Returns:
        Success message with utility ID
        
    Raises:
        400: If validation fails or utility ID already exists
        401: If authentication fails
    """
    try:
        # Validate utility ID
        utility_id = utility_data.get('id')
        if not utility_id:
            raise HTTPException(status_code=400, detail="Utility ID is required")
        
        if not validate_utility_id(utility_id):
            raise HTTPException(
                status_code=400,
                detail="Utility ID must contain only alphanumeric characters and underscores"
            )
        
        # Check if utility already exists
        utilities = await config_service.get_all_utilities()
        if any(u.id == utility_id for u in utilities):
            raise HTTPException(
                status_code=400,
                detail=f"Utility '{utility_id}' already exists"
            )
        
        # Validate required fields
        required_fields = ['id', 'name', 'enabled', 'subscriptions', 'endpoint']
        missing = [f for f in required_fields if f not in utility_data]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields: {', '.join(missing)}"
            )
        
        # TRANSACTION PATTERN: Create subscription FIRST (can fail safely)
        # If subscription creation fails, config file remains unchanged
        new_utility = UtilityConfig.from_dict(utility_data)
        
        try:
            logger.info(f"Creating subscriptions for new utility: {utility_id}")
            await subscription_manager.ensure_all_subscriptions([new_utility])
        except Exception as e:
            logger.error(f"Failed to create subscriptions for {utility_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Subscription creation failed: {str(e)}. Config not modified."
            )
        
        # Only save config if subscription succeeded
        config = load_config()
        config['utilities'].append(utility_data)
        save_config(config)
        
        # Reload config service cache
        await config_service.reload()
        
        logger.info(f"Created new utility: {utility_id}")
        
        return {
            "message": "Utility created successfully",
            "utility_id": utility_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating utility: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{utility_id}", summary="Update entire utility")
async def update_utility(
    utility_id: str,
    utility_data: Dict[str, Any],
    _: bool = Depends(verify_admin_token)
):
    """
    Replace entire utility configuration.
    
    Requires X-Admin-Token header for authentication.
    Updates webhook subscriptions automatically.
    
    Args:
        utility_id: The utility ID to update
        utility_data: Complete new utility configuration
        
    Returns:
        Success message
        
    Raises:
        404: If utility not found
        401: If authentication fails
    """
    try:
        # Load current config
        config = load_config()
        
        # Find utility index
        idx = next(
            (i for i, u in enumerate(config['utilities']) if u['id'] == utility_id),
            None
        )
        
        if idx is None:
            raise HTTPException(
                status_code=404,
                detail=f"Utility '{utility_id}' not found"
            )
        
        # TRANSACTION PATTERN: Save old config for rollback
        old_utility_data = config['utilities'][idx].copy()
        
        # Preserve ID (cannot be changed)
        utility_data['id'] = utility_id
        
        # Update utility in config
        config['utilities'][idx] = utility_data
        
        # Save config
        save_config(config)
        
        # Reload and try to update subscriptions
        try:
            await config_service.reload()
            utilities = await config_service.get_all_utilities()
            logger.info(f"Updating subscriptions for utility: {utility_id}")
            await subscription_manager.ensure_all_subscriptions(utilities)
        except Exception as sub_error:
            # ROLLBACK: Restore old config
            logger.error(f"Subscription update failed for {utility_id}, rolling back: {sub_error}")
            config['utilities'][idx] = old_utility_data
            save_config(config)
            await config_service.reload()
            
            raise HTTPException(
                status_code=500,
                detail=f"Subscription update failed: {str(sub_error)}. Config rolled back."
            )
        
        logger.info(f"Updated utility: {utility_id}")
        
        return {
            "message": "Utility updated successfully",
            "utility_id": utility_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating utility {utility_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{utility_id}", summary="Partially update utility")
async def partial_update_utility(
    utility_id: str,
    updates: Dict[str, Any],
    _: bool = Depends(verify_admin_token)
):
    """
    Update specific fields of a utility.
    
    Requires X-Admin-Token header for authentication.
    Only updates the fields provided in the request body.
    
    Args:
        utility_id: The utility ID to update
        updates: Dictionary of fields to update
        
    Returns:
        Success message with list of updated fields
        
    Raises:
        404: If utility not found
        401: If authentication fails
    """
    try:
        # Prevent ID changes
        if 'id' in updates and updates['id'] != utility_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot change utility ID"
            )
        
        # Load current config
        config = load_config()
        
        # Find utility
        utility = next(
            (u for u in config['utilities'] if u['id'] == utility_id),
            None
        )
        
        if not utility:
            raise HTTPException(
                status_code=404,
                detail=f"Utility '{utility_id}' not found"
            )
        
        # TRANSACTION PATTERN: Save old utility for rollback
        old_utility = utility.copy()
        
        # Apply updates
        utility.update(updates)
        
        # Save config
        save_config(config)
        
        # Reload config
        await config_service.reload()
        
        # If subscriptions or enabled status changed, update subscriptions
        if 'subscriptions' in updates or 'enabled' in updates:
            try:
                logger.info(f"Updating subscriptions for utility: {utility_id}")
                utilities = await config_service.get_all_utilities()
                await subscription_manager.ensure_all_subscriptions(utilities)
            except Exception as sub_error:
                # ROLLBACK: Restore old utility
                logger.error(f"Subscription update failed for {utility_id}, rolling back: {sub_error}")
                idx = next(i for i, u in enumerate(config['utilities']) if u['id'] == utility_id)
                config['utilities'][idx] = old_utility
                save_config(config)
                await config_service.reload()
                
                raise HTTPException(
                    status_code=500,
                    detail=f"Subscription update failed: {str(sub_error)}. Config rolled back."
                )
        
        logger.info(f"Partially updated utility: {utility_id}, fields: {list(updates.keys())}")
        
        return {
            "message": "Utility updated successfully",
            "utility_id": utility_id,
            "fields_updated": list(updates.keys())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error partially updating utility {utility_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{utility_id}", summary="Delete utility")
async def delete_utility(
    utility_id: str,
    _: bool = Depends(verify_admin_token)
):
    """
    Delete a utility and cleanup its subscriptions.
    
    Requires X-Admin-Token header for authentication.
    Automatically removes associated webhook subscriptions.
    
    Args:
        utility_id: The utility ID to delete
        
    Returns:
        Success message
        
    Raises:
        404: If utility not found
        401: If authentication fails
    """
    try:
        # Load current config
        config = load_config()
        
        # Find and remove utility
        original_count = len(config['utilities'])
        config['utilities'] = [
            u for u in config['utilities']
            if u['id'] != utility_id
        ]
        
        if len(config['utilities']) == original_count:
            raise HTTPException(
                status_code=404,
                detail=f"Utility '{utility_id}' not found"
            )
        
        # Save config
        save_config(config)
        
        # Reload and cleanup orphaned subscriptions
        await config_service.reload()
        utilities = await config_service.get_all_utilities()
        await subscription_manager.ensure_all_subscriptions(utilities)
        
        logger.info(f"Deleted utility: {utility_id}")
        
        return {
            "message": "Utility deleted successfully",
            "utility_id": utility_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting utility {utility_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
