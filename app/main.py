
from fastapi import FastAPI

app = FastAPI(
    title="AKMORI",
    description="Intelligent Work & Approval Management System",
    version="0.1.0",
)


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
