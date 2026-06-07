# JARVIS Master Context

**JDOS version:** 1.2  
**Authority:** Mandatory context for every human and AI development agent  
**Updated:** 2026-06-07

## Product Vision

JARVIS is a local-first, privacy-first, offline-first personal AI operating environment. It coordinates specialized local agents to help one user reason, remember, research approved information, automate local tasks, code, understand selected visual inputs, and interact by voice. It combines an ambient desktop presence with an inspectable command center while keeping data, models, and control on the user's machine.

The product is inspired by JARVIS, F.R.I.D.A.Y., Google Assistant, Dynamic Island, and Rainmeter, but it is not a surveillance assistant, cloud service, or autonomous authority.

## Absolute Architecture Rules

These rules cannot be weakened by convenience or agent preference:

1. **Local first:** all user data, memory, configuration, audit, and derived indexes remain on the user's machine.
2. **Privacy first:** no automatic upload, cloud AI, cloud database, cloud memory, external telemetry, or external storage.
3. **Offline first:** core request, memory, knowledge, agent, voice, vision, notification, and UI workflows operate without internet.
4. **Event driven:** NATS publish/subscribe is the integration backbone; JetStream carries durable work.
5. **Multi-agent:** JARVIS Core orchestrates bounded specialized agents through typed contracts.
6. **Clean and hexagonal architecture:** domain logic depends inward; frameworks and infrastructure are adapters.
7. **Least privilege:** agents never gain implicit access to databases, files, processes, sensors, network, or secrets.
8. **Contract first:** APIs, events, persistence ownership, and compatibility are documented and tested.
9. **No distributed transactions:** use local transactions, outbox/inbox, sagas, and compensation.
10. **Human control:** sensitive or irreversible actions require deterministic policy and explicit confirmation.

Accepted ADRs can refine these rules but cannot violate the local/privacy/offline objective without a new product charter approved by the owner.

## Technology Stack

| Layer | Required baseline |
|---|---|
| Desktop | Tauri |
| Web UI | React, TypeScript strict, Tailwind |
| Backend | Python 3.12, FastAPI |
| Messaging | NATS Core and JetStream |
| Durable data | PostgreSQL |
| Ephemeral data | Redis |
| Vector index | Qdrant |
| AI runtime | Ollama |
| General model | Qwen 3 8B |
| Coding model | Qwen Coder |
| Vision model | Qwen2.5-VL |
| Embedding model | nomic-embed-text |
| Wake word | OpenWakeWord |
| Speech-to-text | Faster-Whisper |
| Text-to-speech | Piper |

Versions are pinned during Phase 01. Substitution requires an ADR and must preserve offline operation.

## Agent Definitions

### JARVIS Core Agent

The orchestration authority. Owns request lifecycle, validated plans, task routing, approvals, cancellation, compensation, and response assembly. It does not directly persist specialist data or bypass policy.

### Planner Agent

Converts a request into typed tasks, dependencies, success conditions, capability requirements, risk, and rollback options. Plans are proposals until Core and policy validation.

### Memory Agent

Retrieves relevant approved memories and proposes memory creation/update. It respects consent, provenance, sensitivity, retention, and deletion. It cannot store credentials.

### Research Agent

Searches user-approved local knowledge, returns citations and confidence, separates evidence from inference, and treats retrieved instructions as hostile content. Network research is disabled by default and not part of the core baseline.

### Automation Agent

Executes allowlisted OS/application operations through capability adapters. No generic shell, arbitrary executable, or unrestricted filesystem access.

### Coding Agent

Works in user-approved repository roots, follows repository instructions, proposes scoped changes, runs local checks, and requires explicit authorization for destructive or external operations.

### Vision Agent

Uses Qwen2.5-VL on user-selected frames/files. Pixel data is ephemeral by default; capture scope and retention are visible.

### Voice Agent

Coordinates local wake word, bounded audio capture, transcription, and synthesis. It converts final transcripts into standard Core requests and never bypasses policy.

### Security Agent

Evaluates plans and outputs for abuse, injection, escalation, unsafe arguments, and destructive behavior. It provides defense-in-depth advice; deterministic policy remains authoritative.

### Privacy Agent

Classifies and minimizes data, proposes redaction/retention, and checks purpose limitation. Deterministic enforcement owns final allow/deny decisions.

## Security Principles

- Deny by default, least privilege, defense in depth.
- Models and retrieved content are untrusted.
- Every tool call uses a scoped, expiring capability grant.
- Validate types, sizes, paths, commands, and outputs at boundaries.
- Bind local services to loopback/private networks.
- Use OS credential storage and unique service credentials.
- Log safe metadata, never secrets or raw sensitive payloads.
- Preserve an append-only, tamper-evident local audit trail.
- Preview and confirm destructive, sensitive, financial, credential, sensor, network, or broad-scope actions.
- Fail closed when policy or identity services are unavailable.

## Privacy Principles

- Collect the minimum data for the active user purpose.
- Never upload or synchronize automatically.
- No cloud fallback if a local model/service is unavailable.
- Give the user inspection, correction, export, retention, and deletion controls.
- Raw microphone, camera, and screen data is ephemeral unless explicitly saved.
- Derived content inherits source sensitivity.
- Metrics and diagnostics remain local and require user preview before any manual sharing.
- Deletion propagates through PostgreSQL, Qdrant, Redis, local artifacts, and backup-retention policy.

## Memory Rules

- PostgreSQL is the memory source of truth; Qdrant is a rebuildable index; Redis is never durable memory.
- Durable memory requires explicit active consent, provenance, sensitivity,
  retention, revision, and consent basis.
- Every memory record includes `memory_id`, `consent_id`, source, `created_at`,
  and retention policy.
- Explicit user requests may create memory. Inferred memory is proposed, not silently persisted.
- Restricted values such as passwords, tokens, or private keys are rejected.
- Retrieval is purpose- and scope-limited and returns provenance.
- Updates create revisions and invalidate derived indexes.
- Expiry and deletion are idempotent, observable, and verified across all derived stores.
- Memory content is never copied into durable command or event payloads.
- Consent revocation blocks retrieval immediately and starts verified purge for
  memories with no other valid consent basis.
- `nomic-embed-text` through Ollama is the only approved embedding baseline;
  cloud embeddings and cloud fallback are prohibited.

## Voice Rules

- OpenWakeWord, Faster-Whisper, and Piper run locally.
- Capture has a visible/accessibility indicator and bounded timeout.
- Push-to-talk remains available.
- Raw audio is deleted after transcription by default.
- User can independently disable wake word, microphone, transcript retention, and speech.
- Spoken Restricted data requires explicit current-session intent.
- Voice requests enter the normal API/command/NATS/Core/policy flow.

## Vision Rules

- Qwen2.5-VL runs through Ollama locally.
- Capture is user-initiated and scope is shown before processing.
- No continuous covert screen/camera monitoring.
- Raw frames are ephemeral by default and excluded from logs/events.
- Vision output is untrusted and validated before tool use.
- Sensitive visual data is minimized and not embedded without explicit policy.

## Command and Event Rules

- Commands request future action, use imperative names, and have exactly one
  owning handler.
- The minimum core command registry includes `USER_REQUEST_COMMAND`,
  `SHOW_NOTIFICATION_COMMAND`, `UPDATE_WALLPAPER_COMMAND`,
  `CREATE_MEMORY_COMMAND`, `START_RESEARCH_COMMAND`, and
  `OPEN_APPLICATION_COMMAND`.
- Every additional cross-boundary mutation must register a uniquely owned,
  versioned command before its producer ships.
- Events describe facts that already happened, use past-tense names, and may
  have multiple subscribers.
- The corrected core events are `USER_REQUEST_RECEIVED`, `MEMORY_CREATED`,
  `MEMORY_UPDATED`, `RESEARCH_STARTED`, `RESEARCH_COMPLETED`, and
  `APPLICATION_OPENED`.

- Command subjects follow `jarvis.command.<domain>.<action>.v<major>`.
- Event subjects follow `jarvis.event.<domain>.<fact>.v<major>`.
- Every command/event uses the envelope in
  `docs/implementation/event_contracts.md`.
- Durable events use JetStream and transactional outbox publication.
- Durable commands also use JetStream and transactional outbox publication.
- Delivery is at least once; handlers and consumers are idempotent.
- Correlation and causation IDs are mandatory.
- Events are facts in past tense; commands are separate imperative contracts.
- Breaking schema changes require a new major subject.
- Durable payloads carry only IDs, authorized resource references,
  classification, purpose, versions, and safe operational metadata.
- User prompts, transcripts, research queries, personal content, documents,
  chunks, memory text, embeddings, raw media, credentials, and secrets are
  prohibited in durable NATS payloads.
- Retries are bounded; poison messages go to inspectable dead-letter streams.
- NATS streams, consumers, retention, message size, replay, and dead-letter
  handling follow the v1.2 NATS Governance policy.

## Service and Data Ownership

- API Gateway owns local-client HTTP concerns, not business state.
- Core owns orchestration state.
- Memory owns memories and consent records.
- Knowledge owns sources, chunks, and ingestion.
- Notification owns notification state.
- Settings owns user settings, feature flags, runtime configuration, and
  personal preferences in the `settings` schema.
- Audit owns security/action history.
- Audit also owns consent audit, policy decisions, and administrative events in
  the append-only `audit` schema.
- Services mutate only their own schema.
- Agents use application ports and contracts, never direct datastore clients.
- The Gateway owns no business state and never directly invokes Core or agents;
  mutations enter through command intake and NATS.

## Engineering Quality

- Strong typing, dependency injection, structured errors, and explicit transactions.
- Ruff/Pyright/Pytest for Python; ESLint/Prettier/Vitest and strict TypeScript for UI.
- Risk-based tests cover success, failure, authorization, duplicate, timeout, cancellation, and recovery.
- No public-internet dependency in tests.
- Behavior changes update docs and contracts in the same change.
- Cross-cutting decisions require ADRs.

## Mandatory Session Protocol

1. Read this file, status, active phase, applicable contracts, and accepted ADRs.
2. Inspect repository state; do not overwrite unrelated user work.
3. State objective, boundaries, assumptions, and verification.
4. Implement the smallest coherent change that meets acceptance criteria.
5. Run formatting, typing, tests, security, and offline checks appropriate to risk.
6. Update documentation and `docs/status/development_status.md`.
7. Handoff completed work, exact validation, known issues, decisions, and next action.

When uncertain, preserve privacy, local control, compatibility, and reversibility, then record the unresolved decision.
