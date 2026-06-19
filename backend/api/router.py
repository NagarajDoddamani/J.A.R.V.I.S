from fastapi import APIRouter

from backend.api.endpoints import agent, audit, automation, health, knowledge, memory, notification, orchestrator, planner, policy, research, settings

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(audit.router, tags=["audit"])
api_router.include_router(settings.router, tags=["settings"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(notification.router, prefix="/notification", tags=["notification"])
api_router.include_router(planner.router, prefix="/planner", tags=["planner"])
api_router.include_router(research.router, prefix="/research", tags=["research"])
api_router.include_router(orchestrator.router, prefix="/orchestrator", tags=["orchestrator"])
api_router.include_router(automation.router, prefix="/automation", tags=["automation"])
api_router.include_router(policy.router, prefix="/policy", tags=["policy"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
