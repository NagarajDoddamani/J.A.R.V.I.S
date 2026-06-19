"""Convenience helpers to register all service command handlers at once."""

from __future__ import annotations

from backend.runtime.registry import CommandRegistry


def register_service_handlers(
    registry: CommandRegistry,
    service_name: str,
    handler_pairs: list[tuple[str, object]],
) -> None:
    """Register a batch of handlers for a single service.

    Each pair is ``(command_type, handler_callable)``.  The
    ``command_type`` is the short name (e.g. ``"create_plan"``);
    it is automatically prefixed with ``"<service_name>."``.
    """
    for action, handler in handler_pairs:
        registry.register(f"{service_name}.{action}", handler)


def register_all_handlers(registry: CommandRegistry, **service_kwargs: object) -> None:
    """Register every available service handler in a single call.

    Deprecated — prefer calling the individual ``register_*_handlers``
    functions directly so that dependency injection is explicit.
    """
    from backend.runtime.adapters.automation import register_automation_handlers
    from backend.runtime.adapters.knowledge import register_knowledge_handlers
    from backend.runtime.adapters.memory import register_memory_handlers
    from backend.runtime.adapters.notification import register_notification_handlers
    from backend.runtime.adapters.orchestrator import register_orchestrator_handlers
    from backend.runtime.adapters.planner import register_planner_handlers
    from backend.runtime.adapters.policy import register_policy_handlers
    from backend.runtime.adapters.research import register_research_handlers

    registry_map = {
        "automation": register_automation_handlers,
        "knowledge": register_knowledge_handlers,
        "memory": register_memory_handlers,
        "notification": register_notification_handlers,
        "orchestrator": register_orchestrator_handlers,
        "planner": register_planner_handlers,
        "policy": register_policy_handlers,
        "research": register_research_handlers,
    }
    for service_name, register_fn in registry_map.items():
        use_cases = service_kwargs.get(service_name, {})
        if use_cases:
            register_fn(registry, **use_cases)
