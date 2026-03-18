from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.database import get_db  # re-export for convenience

_redis_client: Redis | None = None


def set_redis(client: Redis) -> None:
    global _redis_client
    _redis_client = client


async def get_redis() -> AsyncGenerator[Redis, None]:
    if _redis_client is None:
        raise RuntimeError("Redis client is not initialised")
    yield _redis_client
