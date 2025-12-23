from fastapi import Header, HTTPException
import logging
import config

logger = logging.getLogger(__name__)

async def verify_bearer_token(authorization: str = Header(..., alias="Authorization")):
    """
    Verify Bearer token for admin/internal endpoints.
    
    Usage:
        @router.get("/test/endpoint")
        async def endpoint(auth: str = Depends(verify_bearer_token)):
            # Endpoint code
    
    Expected header:
        Authorization: Bearer <API_BEARER_KEY>
    """
    if not config.API_BEARER_KEY:
        logger.error("API_BEARER_KEY not configured in environment")
        raise HTTPException(
            status_code=500,
            detail="Server authentication not configured"
        )
    
    # Check if authorization header starts with "Bearer "
    if not authorization.startswith("Bearer "):
        logger.warning("Invalid authorization header format")
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected: 'Bearer <token>'"
        )
    
    # Extract token
    token = authorization.replace("Bearer ", "", 1).strip()
    
    # Verify token
    if token != config.API_BEARER_KEY:
        logger.warning("Invalid API bearer token attempt")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized - Invalid bearer token"
        )
    
    logger.debug("Bearer token verified successfully")
    return token
