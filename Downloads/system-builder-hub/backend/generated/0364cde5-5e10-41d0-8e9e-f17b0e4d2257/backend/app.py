from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from routers import accounts, contacts, deals, pipelines, activities

app = FastAPI(title="CRM Flagship", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])
app.include_router(contacts.router, prefix="/api/contacts", tags=["contacts"])
app.include_router(deals.router, prefix="/api/deals", tags=["deals"])
app.include_router(pipelines.router, prefix="/api/pipelines", tags=["pipelines"])
app.include_router(activities.router, prefix="/api/activities", tags=["activities"])

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "CRM Flagship"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
