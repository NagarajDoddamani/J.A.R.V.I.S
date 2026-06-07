import redis.asyncio as redis

from backend.core.config import settings
from backend.core.logging import logger


class RedisManager:
    def __init__(self):
        self.pool = None
        self.client = None

    async def connect(self):
        if self.client:
            return
        
        try:
            self.pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=10,
                decode_responses=True
            )
            self.client = redis.Redis(connection_pool=self.pool)
            await self.client.ping()
            logger.info("Redis connected", url=settings.REDIS_URL)
        except Exception as e:
            logger.error("Redis connection failed", error=str(e))
            raise

    async def close(self):
        if self.client:
            await self.client.aclose()
        if self.pool:
            await self.pool.disconnect()
        logger.info("Redis connection closed")

    async def is_healthy(self) -> bool:
        if not self.client:
            return False
        try:
            return await self.client.ping()
        except Exception:
            return False

redis_manager = RedisManager()

async def get_redis_client():
    return redis_manager.client
