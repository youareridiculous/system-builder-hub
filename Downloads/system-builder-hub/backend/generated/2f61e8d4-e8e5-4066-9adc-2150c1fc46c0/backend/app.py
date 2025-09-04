from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from datetime import datetime
from routers import accounts, contacts, deals, pipelines, activities, communications, notes, templates, automations, analytics, webhooks, auth, settings

from db import check_db_exists
from seed import initialize_database
from seed_auth import seed_auth_data

app = FastAPI(title="CRM Flagship", version="1.0.1")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup if it doesn't exist"""
    if not check_db_exists():
        print("Database not found, initializing with seed data...")
        initialize_database()
        print("Seeding authentication data...")
        seed_auth_data()
    else:
        print("Database found, skipping initialization")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])
app.include_router(contacts.router, prefix="/api/contacts", tags=["contacts"])
app.include_router(deals.router, prefix="/api/deals", tags=["deals"])
app.include_router(pipelines.router, prefix="/api/pipelines", tags=["pipelines"])
app.include_router(activities.router, prefix="/api/activities", tags=["activities"])
app.include_router(communications.router, prefix="/api/communications", tags=["communications"])
app.include_router(notes.router, prefix="/api", tags=["notes"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
app.include_router(automations.router, prefix="/api/automations", tags=["automations"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])

@app.get("/api/health")
async def health_check():
    import os
    from db import get_db
    
    # Check database connectivity
    db_status = "ok"
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check auth status
    auth_status = "ok"
    auth_secret = os.getenv('AUTH_SECRET')
    if not auth_secret:
        auth_status = "warning: no AUTH_SECRET set"
    
    # Check provider modes
    sendgrid_key = os.getenv('SENDGRID_API_KEY')
    twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
    
    providers = {
        "email": "sendgrid" if sendgrid_key else "mock",
        "sms": "twilio" if twilio_sid else "mock", 
        "voice": "twilio" if twilio_sid else "mock"
    }
    
    return {
        "status": "healthy", 
        "service": "CRM Flagship",
        "version": "v1.0.1",
        "build_id": "2f61e8d4-e8e5-4066-9adc-2150c1fc46c0",
        "database": db_status,
        "auth": auth_status,
        "providers": providers,
        "webhooks_enabled": True,
        "environment": os.getenv('ENVIRONMENT', 'development'),
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
