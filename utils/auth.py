from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
import config

logger = logging.getLogger(__name__)

# Define security scheme for Swagger UI
security = HTTPBearer()

async def verify_bearer_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify Bearer token for admin/internal endpoints.
    
    This will show a 🔒 lock icon in Swagger UI for easy auth.
    
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
    
    # Extract token from credentials
    token = credentials.credentials
    
    # Verify token
    if token != config.API_BEARER_KEY:
        logger.warning("Invalid API bearer token attempt")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized - Invalid bearer token"
        )
    
    logger.debug("Bearer token verified successfully")
    return token
