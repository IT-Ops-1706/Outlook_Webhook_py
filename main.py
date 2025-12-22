from fastapi import FastAPI, Query, HTTPException
import uvicorn
import os
import asyncio
from typing import Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from .services import get_latest_emails, get_email_details, USER_EMAIL, ensure_subscription
from .webhook import router as webhook_router

load_dotenv()

async def subscription_loop():
    """Background loop to ensure subscription is always active"""
    while True:
        try:
            await ensure_subscription()
        except Exception as e:
            print(f"Error in background subscription loop: {e}")
        
        # Check every 12 hours
        await asyncio.sleep(12 * 3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("Server starting up. Initiating subscription check...")
    # Run initial check immediately
    await ensure_subscription()
    # Start the background loop
    background_task = asyncio.create_task(subscription_loop())
    
    yield
    
    # Shutdown logic
    print("Server shutting down. Cancelling background tasks...")
    background_task.cancel()

app = FastAPI(title="Outlook Webhook Server", lifespan=lifespan)

# Include the webhook router
app.include_router(webhook_router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Outlook Webhook Server",
        "endpoints": {
            "health": "/health",
            "latest_emails": "/emails/latest",
            "email_details": "/emails/{message_id}",
            "webhook": "/webhook"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/emails/latest")
async def fetch_latest_emails(
    top: int = Query(10, ge=1, le=50),
    user_email: Optional[str] = Query(None)
):
    """Manually fetch latest emails"""
    try:
        email = user_email or USER_EMAIL
        emails = get_latest_emails(email, top)
        
        return {
            "success": True,
            "count": len(emails),
            "emails": emails
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/emails/{message_id}")
async def fetch_email_details(
    message_id: str,
    user_email: Optional[str] = Query(None)
):
    """Fetch details of a specific email"""
    try:
        email = user_email or USER_EMAIL
        email_data = get_email_details(email, message_id)
        
        return {
            "success": True,
            "email": email_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("Starting Outlook Webhook Server with FastAPI...")
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)