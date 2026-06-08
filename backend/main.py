import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.router import api_router
from backend.audit.nats import publish_outbox_events
from backend.settings.nats import publish_settings_outbox_events
from backend.core.config import settings
from backend.core.logging import logger, setup_logging
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

    outbox_tasks: list[asyncio.Task[None]] = []

    try:
        await nats_manager.connect()
        if settings.NATS_AUTO_BOOTSTRAP:
            try:
                await nats_manager.bootstrap_governance()
            except Exception as exc:
                logger.error("NATS governance bootstrap failed", error=str(exc))
        await redis_manager.connect()
        await qdrant_manager.connect()

        # Start the outbox publishers if NATS is healthy
        if nats_manager.js is not None:
            outbox_tasks.append(
                asyncio.create_task(
                    publish_outbox_events(
                        nats_manager.js,
                        interval_seconds=5.0,
                    )
                )
            )
            outbox_tasks.append(
                asyncio.create_task(
                    publish_settings_outbox_events(
                        nats_manager.js,
                        interval_seconds=5.0,
                    )
                )
            )
            logger.info("Outbox publishers started")
    except Exception as e:
        logger.error("Infrastructure initialization failed", error=str(e))

    yield

    # Cancel background tasks
    for task in outbox_tasks:
        task.cancel()
    for task in outbox_tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass

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
        reload=settings.ENVIRONMENT == "development"
    )
