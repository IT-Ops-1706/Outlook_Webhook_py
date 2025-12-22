from fastapi import FastAPI
import uvicorn
import logging
import asyncio
from contextlib import asynccontextmanager

from api.webhook import router as webhook_router
from api.test_endpoints import router as test_router
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
    logger.info("=" * 60)
    logger.info("Centralized Email Webhook System Starting")
    logger.info("=" * 60)
    
    # Wait for network to be ready
    await asyncio.sleep(5)
    
    # Ensure all subscriptions exist
    try:
        logger.info("Ensuring webhook subscriptions...")
        utilities = await config_service.get_all_utilities()
        await subscription_manager.ensure_all_subscriptions(utilities)
        logger.info("Subscriptions verified")
    except Exception as e:
        logger.error(f"Error setting up subscriptions: {e}")
    
    # Start maintenance loop
    maintenance_task = asyncio.create_task(subscription_maintenance_loop())
    
    logger.info(f"Configuration loaded from: config/utility_rules.json")
    logger.info(f"Max concurrent forwards: {config.MAX_CONCURRENT_FORWARDS}")
    logger.info(f"Batch size: {config.BATCH_SIZE}")
    logger.info("Server ready to receive webhook notifications")
    logger.info("Subscription auto-renewal active (every 12 hours)")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Centralized Email Webhook System")
    maintenance_task.cancel()

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
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "email_webhook"
    }

if __name__ == "__main__":
    logger.info("Starting server...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower()
    )