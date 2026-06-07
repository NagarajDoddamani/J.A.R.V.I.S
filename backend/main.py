from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.api.router import api_router
from backend.core.config import settings
from backend.core.logging import setup_logging, logger
from backend.core.nats import nats_manager
from backend.core.redis import redis_manager
from backend.core.qdrant import qdrant_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging(settings.LOG_LEVEL)
    logger.info("Starting JARVIS Backend", 
                environment=settings.ENVIRONMENT,
                project=settings.PROJECT_NAME)
    
    # Initialize infrastructure
    try:
        await nats_manager.connect()
        await redis_manager.connect()
        await qdrant_manager.connect()
    except Exception as e:
        logger.error("Infrastructure initialization failed", error=str(e))
        # We might want to still start but in degraded mode, 
        # but for hardening pass we ensure they are at least attempted.
    
    yield
    
    # Shutdown
    logger.info("Shutting down JARVIS Backend")
    await nats_manager.close()
    await redis_manager.close()
    await qdrant_manager.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
)

@app.middleware("http")
async def sensitive_payload_policy(request: Request, call_next):
    # Only check for POST/PUT requests which might contain payloads
    if request.method in ["POST", "PUT"]:
        # Validation framework hook
        # For actual implementation, we would parse body and call validate_event_payload
        pass
    
    response = await call_next(request)
    return response

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
