from fastapi import APIRouter

from backend.api.endpoints import audit, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(audit.router, tags=["audit"])
