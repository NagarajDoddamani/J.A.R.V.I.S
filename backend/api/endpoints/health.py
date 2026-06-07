from fastapi import APIRouter
from backend.core.config import settings
import httpx
import nats
from qdrant_client import QdrantClient
import redis.asyncio as redis

router = APIRouter()

@router.get("/health")
async def health_check():
    health_status = {
        "status": "healthy",
        "version": "0.1.0",
        "services": {}
    }

    # Check NATS
    try:
        nc = await nats.connect(settings.NATS_URL, timeout=1)
        await nc.close()
        health_status["services"]["nats"] = "up"
    except Exception:
        health_status["services"]["nats"] = "down"
        health_status["status"] = "degraded"

    # Check Qdrant
    try:
        client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=1)
        client.get_collections()
        health_status["services"]["qdrant"] = "up"
    except Exception:
        health_status["services"]["qdrant"] = "down"
        health_status["status"] = "degraded"

    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        health_status["services"]["redis"] = "up"
    except Exception:
        health_status["services"]["redis"] = "down"
        health_status["status"] = "degraded"

    return health_status
