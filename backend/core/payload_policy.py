from typing import Any, Dict
from backend.core.logging import logger

# Sensitive keys that should not be present in durable event payloads
SENSITIVE_KEYS = {
    "raw_memory",
    "memory_content",
    "raw_research",
    "research_content",
    "raw_prompt",
    "full_prompt",
    "api_key",
    "secret"
}

def validate_event_payload(payload: Dict[str, Any]) -> bool:
    """
    Validates that a payload does not contain sensitive raw content.
    Returns True if valid, raises ValueError if sensitive content is found.
    """
    for key in payload.keys():
        if key.lower() in SENSITIVE_KEYS:
            logger.error("Sensitive content detected in event payload", key=key)
            raise ValueError(f"Payload contains restricted sensitive key: {key}")
        
        # Recursive check for nested dicts
        if isinstance(payload[key], dict):
            validate_event_payload(payload[key])
        elif isinstance(payload[key], list):
            for item in payload[key]:
                if isinstance(item, dict):
                    validate_event_payload(item)
                    
    return True
