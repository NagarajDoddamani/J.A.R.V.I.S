from contextlib import asynccontextmanager
from fastapi import FastAPI

from backend.api.router import api_router
from backend.core.config import settings
from backend.core.logging import setup_logging, logger
from backend.core.middleware import PayloadEnforcementMiddleware
from backend.core.nats import nats_manager
from backend.core.qdrant import qdrant_manager
from backend.core.redis import redis_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.LOG_LEVEL)
    logger.info(
        "Starting JARVIS Backend",
        environment=settings.ENVIRONMENT,
        project=settings.PROJECT_NAME,
        nats_max_payload_bytes=settings.NATS_MAX_PAYLOAD_BYTES,
    )

    try:
        await nats_manager.connect()
        if settings.NATS_AUTO_BOOTSTRAP:
            try:
                await nats_manager.bootstrap_governance()
            except Exception as exc:
                logger.error("NATS governance bootstrap failed", error=str(exc))
        await redis_manager.connect()
        await qdrant_manager.connect()
    except Exception as e:
        logger.error("Infrastructure initialization failed", error=str(e))

    yield

    logger.info("Shutting down JARVIS Backend")
    await nats_manager.close()
    await redis_manager.close()
    await qdrant_manager.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
)

# Add the JDOS v1.2 (Correction 5) payload policy enforcement.
# The middleware sits in front of every route and rejects POST/PUT/PATCH
# requests whose JSON bodies carry sensitive keys.
app.add_middleware(PayloadEnforcementMiddleware)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "JARVIS API v1.0 Foundation Active"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True if settings.ENVIRONMENT == "development" else False
    )
