from fastapi import FastAPI
import uvicorn
import logging
import asyncio
from contextlib import asynccontextmanager

from api.webhook import router as webhook_router
from api.test_endpoints import router as test_router
from api.utilities_management import router as utilities_router
from utils.logging_config import setup_logging
from services.subscription_manager import subscription_manager
from services.config_service import config_service
import config

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Background task for subscription renewal
async def subscription_maintenance_loop():
    """Background task to check and renew subscriptions every 12 hours"""
    while True:
        try:
            logger.info("Running subscription maintenance check")
            await subscription_manager.check_and_renew_subscriptions()
        except Exception as e:
            logger.error(f"Error in subscription maintenance: {e}")
        
        # Wait 12 hours
        await asyncio.sleep(12 * 3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    # Startup
    logger.info("============================================================")
    logger.info("Centralized Email Webhook System Starting")
    logger.info("============================================================")
    
    # Ensure webhook subscriptions exist
    logger.info("Ensuring webhook subscriptions...")
    utilities = await config_service.get_all_utilities()
    await subscription_manager.ensure_all_subscriptions(utilities)
    logger.info("Subscriptions verified")
    
    logger.info(f"Configuration loaded from: {config_service.json_path}")
    logger.info(f"Max concurrent forwards: {config.MAX_CONCURRENT_FORWARDS}")
    logger.info(f"Batch size: {config.BATCH_SIZE}")
    logger.info("Server ready to receive webhook notifications")
    
    # Start subscription renewal background task
    logger.info("Subscription auto-renewal active (every 12 hours)")
    maintenance_task = asyncio.create_task(subscription_maintenance_loop())
    
    yield
    
    # Shutdown
    logger.info("Shutting down Centralized Email Webhook System")
    maintenance_task.cancel()
    
    # Close Graph API session
    from services.graph_service import graph_service
    await graph_service.close()

# Create FastAPI app with lifespan
app = FastAPI(
    title="Centralized Email Webhook System",
    description="Real-time email processing with Microsoft Graph webhooks",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(webhook_router, tags=["webhook"])
app.include_router(test_router, tags=["testing"])
app.include_router(utilities_router, tags=["management"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Centralized Email Webhook",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "webhook": "/webhook",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint with dependency validation"""
    from services.graph_service import graph_service
    from services.subscription_manager import subscription_manager
    
    health_status = {
        "status": "healthy",
        "service": "email_webhook",
        "checks": {}
    }
    
    # Check 1: Graph API connectivity
    try:
        await graph_service.get_access_token()
        health_status["checks"]["graph_api"] = {
            "status": "ok",
            "message": "Successfully authenticated with Microsoft Graph"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["graph_api"] = {
            "status": "error",
            "message": f"Failed to authenticate: {str(e)}"
        }
    
    # Check 2: Active subscriptions
    try:
        subs = subscription_manager.list_subscriptions()
        health_status["checks"]["subscriptions"] = {
            "status": "ok" if len(subs) > 0 else "warning",
            "count": len(subs),
            "message": f"{len(subs)} active subscription(s)"
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["checks"]["subscriptions"] = {
            "status": "error",
            "message": f"Failed to list subscriptions: {str(e)}"
        }
    
    # Check 3: Config file accessibility
    try:
        utilities = await config_service.get_all_utilities()
        health_status["checks"]["config"] = {
            "status": "ok",
            "utilities_count": len(utilities),
            "message": f"{len(utilities)} utility(ies) configured"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["config"] = {
            "status": "error",
            "message": f"Failed to load config: {str(e)}"
        }
    
    # Determine HTTP status code
    status_code = 200
    if health_status["status"] == "degraded":
        status_code = 200  # Still operational
    elif health_status["status"] == "unhealthy":
        status_code = 503  # Service unavailable
    
    from fastapi.responses import JSONResponse
    return JSONResponse(content=health_status, status_code=status_code)

if __name__ == "__main__":
    logger.info("Starting server...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower()
    )