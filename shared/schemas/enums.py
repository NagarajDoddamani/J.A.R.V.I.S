from __future__ import annotations

from enum import StrEnum


class Classification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"


class ActorType(StrEnum):
    USER = "user"
    SERVICE = "service"
    AGENT = "agent"


class RequestStatus(StrEnum):
    RECEIVED = "received"
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class DisplayScope(StrEnum):
    ALL = "all"
    PRIMARY = "primary"
    SECONDARY = "secondary"


class InputMode(StrEnum):
    TEXT = "text"
    VOICE = "voice"
    VISION = "vision"


class ResearchStatus(StrEnum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApplicationResult(StrEnum):
    SUCCESS = "success"
    ALREADY_RUNNING = "already_running"
    FAILED = "failed"


class MemoryType(StrEnum):
    PREFERENCE = "preference"
    FACT = "fact"
    CONVERSATION = "conversation"
    CUSTOM = "custom"


class ConsentStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class RetentionPolicyType(StrEnum):
    UNTIL_DELETED = "until_deleted"
    EXPIRES = "expires"


class LaunchMode(StrEnum):
    USER_APPROVED = "user_approved"
    POLICY = "policy"


class KnowledgeSourceKind(StrEnum):
    DIRECTORY = "directory"
    FILE = "file"


class KnowledgeSourceRetention(StrEnum):
    REFERENCE_SOURCE = "reference_source"


class WallpaperState(StrEnum):
    PROCESSING = "processing"
    APPLIED = "applied"
    FAILED = "failed"


class TransitionType(StrEnum):
    CROSSFADE = "crossfade"
    INSTANT = "instant"


class DeletionJobStatus(StrEnum):
    PURGE_PENDING = "purge_pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PolicyDecision(StrEnum):
    GRANT = "grant"
    DENY = "deny"
    REQUIRE_CONFIRMATION = "require_confirmation"


class AgentTaskStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalDecision(StrEnum):
    APPROVE_ONCE = "approve_once"
    DENY = "deny"
