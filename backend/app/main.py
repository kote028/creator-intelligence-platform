from routes.creators import router as creator_router
from routes.social_account import router as social_account_router
from routes.creator_metrics import router as creator_metric_router
from routes.brands import router as brand_router
from routes.campaigns import router as campaign_router
from routes.sponsorships import router as sponsorship_router
from routes.auth import router as auth_router

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.database import engine
from app.config import ALLOWED_ORIGINS

app = FastAPI(
    title="Creator Marketplace API",
    description="API for connecting brands with content creators",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


app.include_router(auth_router)
app.include_router(creator_router)
app.include_router(social_account_router)
app.include_router(creator_metric_router)
app.include_router(brand_router)
app.include_router(campaign_router)
app.include_router(sponsorship_router)

