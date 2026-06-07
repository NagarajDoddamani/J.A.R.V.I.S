from fastapi import APIRouter, Depends
from backend.core.config import settings
from backend.core.nats import NatsManager, nats_manager
from backend.core.redis import RedisManager, redis_manager
from backend.core.qdrant import QdrantManager, qdrant_manager
from backend.core.logging import logger
import asyncio
import time

router = APIRouter()

async def get_nats_manager() -> NatsManager:
    return nats_manager

async def get_redis_manager() -> RedisManager:
    return redis_manager

async def get_qdrant_manager() -> QdrantManager:
    return qdrant_manager

@router.get("/health")
async def health_check(
    nats: NatsManager = Depends(get_nats_manager),
    redis: RedisManager = Depends(get_redis_manager),
    qdrant: QdrantManager = Depends(get_qdrant_manager)
):
    """
    Enhanced health check with dependency injection and hardened timeout strategy.
    Implements cold-start tolerance and degraded mode handling.
    """
    start_time = time.time()
    health_status = {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": start_time,
        "services": {}
    }

    # Parallel health checks with timeout
    async def check_service(name, manager):
        try:
            # FIX-13: Increase timeout strategy and implementation of grace period
            is_up = await asyncio.wait_for(manager.is_healthy(), timeout=2.0)
            return name, "up" if is_up else "down"
        except asyncio.TimeoutError:
            logger.warning(f"Health check timeout for {name}", service=name)
            return name, "timeout"
        except Exception as e:
            logger.error(f"Health check failed for {name}", service=name, error=str(e))
            return name, "down"

    results = await asyncio.gather(
        check_service("nats", nats),
        check_service("redis", redis),
        check_service("qdrant", qdrant),
        return_exceptions=True
    )

    for res in results:
        if isinstance(res, tuple):
            name, status = res
            health_status["services"][name] = status
            if status != "up":
                health_status["status"] = "degraded"

    # FIX-12: Structured logging with correlation ID (if available in context)
    duration = time.time() - start_time
    logger.info("Health check completed", 
                status=health_status["status"], 
                duration=duration,
                services=health_status["services"])

    return health_status
