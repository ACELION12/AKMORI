
from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.db.dependencies import get_db
from app.api.organizations import router as organizations_router
app = FastAPI(
    title="AKMORI",
    description="Intelligent Work & Approval Management System",
    version="0.1.0",
)
app.include_router(users_router)
app.include_router(auth_router)
app.include_router(organizations_router)

@app.get("/")
def home():
    return {
        "message": "Welcome to AKMORI",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }
@app.get("/health/database")
def database_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected",
    }
