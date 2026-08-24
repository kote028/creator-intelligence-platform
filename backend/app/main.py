from routes.creators import router as creator_router
from fastapi import FastAPI
from sqlalchemy import text
from app.database import engine

app = FastAPI(
    title="Creator Marketplace API",
    description="API for connecting brands with content creators",
    version="1.0.0"
)
app.include_router(creator_router)


@app.get("/")
def root():
    return {
        "message": "Creator Marketplace API is running!"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


@app.get("/db-test")
def database_test():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return {
            "database": "connected",
            "result": result.scalar()
        }

