from routes.creators import router as creator_router
from routes.social_account import router as social_account_router
from routes.creator_metrics import router as creator_metric_router
from routes.brands import router as brand_router
from routes.campaigns import router as campaign_router
from routes.sponsorships import router as sponsorship_router
from routes.auth import router as auth_router
from routes.intelligence import router as intelligence_router

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.database import engine
from app.config import ALLOWED_ORIGINS
from app.retention import delete_expired_public_youtube_metrics

logger = logging.getLogger(__name__)


async def _youtube_metric_retention_worker():
    while True:
        try:
            await asyncio.to_thread(delete_expired_public_youtube_metrics)
        except Exception:
            # Keep the API available and retry soon after transient DB failures.
            logger.exception("YouTube metric retention cleanup failed")
            await asyncio.sleep(60 * 60)
        else:
            await asyncio.sleep(24 * 60 * 60)


@asynccontextmanager
async def lifespan(_: FastAPI):
    cleanup_task = asyncio.create_task(_youtube_metric_retention_worker())
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="Creator Marketplace API",
    description="API for connecting brands with content creators",
    version="1.1.0",
    lifespan=lifespan,
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
app.include_router(intelligence_router)
