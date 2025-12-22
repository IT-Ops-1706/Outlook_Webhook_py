from fastapi import FastAPI
import uvicorn
import logging

from api.webhook import router as webhook_router
from api.test_endpoints import router as test_router
from utils.logging_config import setup_logging
import config

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Centralized Email Webhook System",
    description="Real-time email processing with Microsoft Graph webhooks",
    version="1.0.0"
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

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("=" * 60)
    logger.info("Centralized Email Webhook System Starting")
    logger.info("=" * 60)
    logger.info(f"Configuration loaded from: config/utility_rules.json")
    logger.info(f"Max concurrent forwards: {config.MAX_CONCURRENT_FORWARDS}")
    logger.info(f"Batch size: {config.BATCH_SIZE}")
    logger.info("Server ready to receive webhook notifications")

@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("Shutting down Centralized Email Webhook System")

if __name__ == "__main__":
    logger.info("Starting server...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower()
    )