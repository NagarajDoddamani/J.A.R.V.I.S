# ADR-0001: Architecture Baseline

- **Status:** Accepted
- **Date:** 2026-06-07
- **Owners:** Product owner and architecture owner
- **Decision scope:** Entire JARVIS system

## Context

JARVIS needs a durable baseline that multiple human and AI agents can implement without introducing incompatible service coupling, remote data dependencies, or excessive model authority.

## Decision Drivers

- User ownership and privacy of personal data.
- Core availability without internet.
- Modular evolution of agents and experiences.
- Observable, recoverable workflows.
- Testable boundaries and least privilege.

## Considered Options

### Modular Monolith with Direct Calls

Simpler initial deployment, but encourages shared persistence, synchronous coupling, and limited isolation for long-running agent workflows.

### Local Event-Driven Services with Clean Internals

Adds operational components and contract discipline while supporting asynchronous agents, failure recovery, ownership boundaries, and future process isolation.

### Cloud-Native Hosted Platform

Offers elastic infrastructure but directly conflicts with local-first, privacy-first, and offline-first requirements.

## Decision

Adopt a local event-driven architecture with the following baseline decisions:

### Platform Support
- **Primary:** Windows 11
- **Secondary:** Ubuntu 24.04

### Toolchain and Monorepo
- **Monorepo Management:** `pnpm` workspaces
- **JavaScript Package Manager:** `pnpm` (Node.js 22 LTS)
- **Python Package Manager:** `uv` (Python 3.12)

### Infrastructure and Supervision
- **Process Supervision:** Docker Compose
- **Relational Database:** PostgreSQL 16
- **Ephemeral Coordination:** Redis 7
- **Vector Database:** Qdrant (latest stable)
- **Event Bus/Messaging:** NATS JetStream (latest stable)
- **Inference Engine:** Ollama (latest stable)

### Architecture Patterns
- Tauri, React, TypeScript, and Tailwind for the desktop experience.
- Python 3.12 and FastAPI for backend boundaries.
- Clean/hexagonal internals, service-owned schemas, dependency injection, typed contracts, and transactional outbox/inbox patterns.

Deploy initially on one machine. Bind services locally and deny outbound network by default.

## Consequences

### Positive

- Strong privacy and offline guarantees.
- Explicit, testable ownership and integration contracts.
- Better recovery, replay, and observability for agent workflows.
- Models remain replaceable adapters rather than architecture authorities.

### Negative

- More infrastructure and operational complexity than a single process.
- Eventual consistency and idempotency require disciplined implementation.
- Local hardware limits concurrency and model performance.

### Risks and Mitigations

- Resource overhead: define hardware profiles and resource budgets.
- Contract drift: generate schemas/clients and run compatibility tests.
- Event complexity: standard envelope, outbox/inbox, dead-letter, and replay tooling.
- Excessive service fragmentation: begin with bounded deployables and split only with measured need.

## Validation

Phase 01 must prove local startup, offline operation, NATS durability, migration, backup/restore, and resource use before Phase 02.

## Rollback or Supersession

Components may be co-located in processes without violating logical boundaries. Replacing a baseline technology or allowing remote infrastructure requires a superseding ADR; violating local/privacy/offline goals requires a new product charter.

## References

- `docs/PRD/product_requirements.md`
- `docs/architecture/system_architecture.md`
- `docs/prompts/master_context.md`

