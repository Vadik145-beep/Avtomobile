import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.config import settings
from app.core.distributor import init_exclusive_queue
from app.database import AsyncSessionLocal
from app.dependencies import set_redis
from app.routers import admin, webhook
from app.routers.bot import miniapp_router, router as bot_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    set_redis(redis)
    logger.info("Redis connected: %s", settings.redis_url)

    async with AsyncSessionLocal() as db:
        added = await init_exclusive_queue(db, redis)
        if added:
            logger.info("Exclusive queue populated with %d users on startup", added)

    yield
    await redis.aclose()
    logger.info("Redis connection closed")


app = FastAPI(
    title="Авто-Лид API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook.router)
app.include_router(admin.router)
app.include_router(bot_router)
app.include_router(miniapp_router)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok"}
