from fastapi import APIRouter

from backend.api.endpoints import audit, health, knowledge, memory, settings

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(audit.router, tags=["audit"])
api_router.include_router(settings.router, tags=["settings"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
