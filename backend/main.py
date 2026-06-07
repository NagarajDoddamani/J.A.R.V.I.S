from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.api.router import api_router
from backend.core.config import settings
from backend.core.logging import setup_logging, logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging(settings.LOG_LEVEL)
    logger.info("Starting JARVIS Backend", 
                environment=settings.ENVIRONMENT,
                project=settings.PROJECT_NAME)
    yield
    # Shutdown
    logger.info("Shutting down JARVIS Backend")

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
)

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
