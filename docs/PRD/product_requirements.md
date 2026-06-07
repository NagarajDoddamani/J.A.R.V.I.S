# JARVIS Product Requirements Document

**Document version:** 1.0  
**Product stage:** Pre-implementation  
**Baseline date:** 2026-06-07

Architecture corrections in
`../architecture/JDOS_v1.2_Architecture_Corrections_Addendum.md` are part of
this product baseline. The approved local embedding model is
`nomic-embed-text` through Ollama.

## Product Vision

JARVIS is a private AI operating environment that helps one user understand information, remember context, control local applications, and interact through text, voice, and vision without surrendering personal data to remote services. It should feel continuously available while remaining inspectable, interruptible, and under explicit user control.

## Target User

The initial release serves a technically capable single user on a desktop workstation who values privacy, offline availability, automation, and ownership of data. Multi-user and remote access are outside the v1 baseline.

## Outcomes

- Complete common assistant workflows without an internet connection.
- Provide durable, searchable memory with provenance and user controls.
- Coordinate specialized agents through observable, typed events.
- Accept text and voice requests and return text, voice, and native notifications.
- Offer a compact ambient interface and a detailed command center.
- Make every sensitive action explainable, authorized, and auditable locally.

## Functional Capabilities

| Capability | v1 expectation |
|---|---|
| Request orchestration | Plan, route, execute, and summarize multi-step local tasks |
| Memory | Create, search, update, expire, export, and delete user-approved memories |
| Knowledge | Index approved local content and answer with provenance |
| Research | Search approved local sources; internet research is a disabled-by-default extension |
| Automation | Open applications and execute allowlisted local actions with confirmation policies |
| Voice | Local wake word, speech-to-text, and text-to-speech |
| Vision | User-initiated analysis of screenshots or selected files |
| Notifications | Prioritized local notifications with action and dismissal state |
| Interface | Dynamic Island, JARVIS Orb, command center, and wallpaper controls |
| Audit | Local record of requests, decisions, permissions, and side effects |

## Non-Goals for v1

- Cloud-hosted models, storage, synchronization, or telemetry.
- Autonomous purchasing, financial trading, or irreversible high-risk actions.
- Covert monitoring, continuous screen capture, or ambient recording.
- Enterprise multi-tenancy, mobile clients, or public plugin marketplace.
- General operating-system replacement.

## Experience Principles

- **Consent before capture:** sensors and sensitive data require visible user intent.
- **Progressive disclosure:** ambient UI stays compact; details remain inspectable.
- **Reversible by default:** previews, confirmations, undo, and retention controls are preferred.
- **Honest uncertainty:** model confidence and missing evidence are exposed.
- **Offline clarity:** the UI distinguishes unavailable network enhancements from core failures.

## Core User Journeys

### Request to Action

The user submits a request, sees acknowledgement and progress, reviews any privileged action, and receives a result with provenance and an audit record.

### Remember and Recall

The user explicitly asks JARVIS to remember information. The system classifies sensitivity and retention, stores structured metadata and embeddings, and later retrieves it with source and confidence. The user can edit or delete it completely.

### Voice Interaction

An on-device wake-word detector activates a bounded recording window. Local transcription creates a request. JARVIS responds through the UI and optional local speech synthesis. Audio is discarded unless the user explicitly saves it.

### Vision Interaction

The user selects a screenshot, region, camera frame, or file. The system displays the capture boundary, performs local inference, and does not retain pixels by default.

## Quality Attributes

| Attribute | Initial target |
|---|---|
| Offline availability | All core journeys pass with outbound network blocked |
| Privacy | Zero automatic external data transfer |
| Reliability | Graceful degradation when an optional service is unavailable |
| Event durability | At-least-once delivery for durable workflows with idempotent consumers |
| API latency | p95 under 300 ms excluding model inference and heavy indexing |
| UI responsiveness | Visible acknowledgement within 150 ms of local input |
| Observability | Every request traceable by correlation ID across services and events |
| Recovery | Documented backup/restore with quarterly restore test |
| Accessibility | Keyboard operation, reduced motion, readable contrast, screen-reader labels |
| Test quality | Risk-based coverage; 80% line coverage floor for core domain/application code |

## Success Metrics

All metrics remain local and are displayed only to the user:

- Task completion and cancellation rates.
- Median and p95 request latency by workflow stage.
- Model and service failure rates.
- Memory retrieval relevance confirmed by user feedback.
- Permission prompts accepted, denied, and timed out.
- Offline integration suite pass rate.

Metrics MUST NOT be uploaded automatically.

## Release Criteria

v1 is releasable when:

- Every phase exit gate is satisfied.
- Required services install and start from documented local tooling.
- Core workflows pass with network access denied.
- Threat model findings rated critical or high are resolved.
- Backup, restore, export, and deletion tests pass.
- Voice and vision capture indicators and consent controls are verified.
- Installer, upgrade, rollback, and local uninstallation paths are documented.

## Risks

| Risk | Mitigation |
|---|---|
| Local model quality or latency | Model abstraction, evaluation suite, bounded context, hardware profiles |
| Excessive agent autonomy | Capability allowlists, policy engine, confirmation gates, audit trail |
| Memory leakage | Classification, least-privilege retrieval, retention, redaction, deletion verification |
| Event duplication or reordering | Idempotency keys, sequence metadata, transactional outbox |
| Resource contention | Work queues, quotas, backpressure, health-aware scheduling |
| Architectural drift across AI agents | Master context, ADRs, contracts, status handoff, CI architecture checks |
