from backend.runtime.adapters.automation import register_automation_handlers
from backend.runtime.adapters.knowledge import register_knowledge_handlers
from backend.runtime.adapters.memory import register_memory_handlers
from backend.runtime.adapters.notification import register_notification_handlers
from backend.runtime.adapters.orchestrator import register_orchestrator_handlers
from backend.runtime.adapters.planner import register_planner_handlers
from backend.runtime.adapters.policy import register_policy_handlers
from backend.runtime.adapters.research import register_research_handlers
from backend.runtime.adapters.registration import (
    register_all_handlers,
    register_service_handlers,
)

__all__ = [
    "register_all_handlers",
    "register_automation_handlers",
    "register_knowledge_handlers",
    "register_memory_handlers",
    "register_notification_handlers",
    "register_orchestrator_handlers",
    "register_planner_handlers",
    "register_policy_handlers",
    "register_research_handlers",
    "register_service_handlers",
]
