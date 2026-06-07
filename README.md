# JARVIS Development Operating System

**Version:** 1.2  
**Status:** Documentation baseline  
**Last updated:** 2026-06-07

JARVIS is a local-first, privacy-first, offline-first AI operating environment.
This repository contains JDOS v1.2, including the architecture corrections in
[`docs/architecture/JDOS_v1.2_Architecture_Corrections_Addendum.md`](docs/architecture/JDOS_v1.2_Architecture_Corrections_Addendum.md).

No production code should be added until the relevant Phase 01 entry criteria and architecture decision records are approved.

## Non-Negotiable Constraints

- User data and durable memory remain on the user's machine.
- Core workflows operate without internet access.
- No cloud AI, cloud database, cloud memory, telemetry upload, or automatic external storage.
- Services communicate asynchronously through NATS where practical.
- Ollama is the only approved model runtime in the baseline architecture.
- PostgreSQL, Redis, and Qdrant have distinct, documented ownership roles.
- Security and privacy decisions fail closed.

## Repository Map

```text
JARVIS/
|-- AGENTS.md
|-- README.md
|-- SECURITY.md
|-- backend/
|   `-- README.md
|-- docs/
|   |-- README.md
|   |-- PRD/
|   |   `-- product_requirements.md
|   |-- architecture/
|   |   |-- JDOS_v1.2_Architecture_Corrections_Addendum.md
|   |   |-- memory_architecture.md
|   |   |-- research_architecture.md
|   |   |-- security_privacy.md
|   |   `-- system_architecture.md
|   |-- decisions/
|   |   |-- 0001-architecture-baseline.md
|   |   |-- 0002-jdos-v1.2-architecture-corrections.md
|   |   |-- README.md
|   |   `-- template.md
|   |-- development/
|   |   |-- Phase_01_Foundation.md
|   |   |-- Phase_02_Core_Services.md
|   |   |-- Phase_03_Agents.md
|   |   |-- Phase_04_Voice.md
|   |   |-- Phase_05_UI.md
|   |   |-- Phase_06_Integration.md
|   |   `-- development_workflow.md
    |   |-- implementation/
    |   |   |-- api_contracts.md
    |   |   |-- coding_standards.md
    |   |   |-- compose_operations.md
    |   |   |-- database_schema_foundation.md
    |   |   |-- database_strategy.md
    |   |   |-- event_contracts.md
    |   |   |-- lockfile_policy.md
    |   |   |-- nats_governance.md
    |   |   |-- ollama_adapter.md
    |   |   |-- qdrant_governance.md
    |   |   `-- redis_governance.md
|   |-- prompts/
|   |   |-- claude_code_prompt.md
|   |   |-- codex_prompt.md
|   |   |-- gemini_cli_prompt.md
|   |   `-- master_context.md
    |   `-- status/
    |       `-- development_status.md
    |-- frontend/
    |   |-- README.md
    |   `-- package.json
    |-- infrastructure/
    |   `-- README.md
    |-- shared/
    |   `-- README.md
    |-- tests/
    |   |-- README.md
    |   |-- test_architecture_fitness.py
    |   |-- test_backup_restore.py
    |   |-- test_compose_hardening.py
    |   |-- test_lockfile.py
    |   |-- test_model_verification.py
    |   |-- test_nats_governance.py
    |   |-- test_nats_payload_policy.py
    |   |-- test_ollama_adapter.py
    |   |-- test_payload_enforcement.py
    |   |-- test_qdrant_governance.py
    |   |-- test_redis_governance.py
    |   `-- test_sbom.py
    `-- tools/
        |-- README.md
        |-- backup/
        |   |-- backup.py
        |   |-- crypto.py
        |   |-- manifest.py
        |   `-- restore.py
        |-- lockfile/
        |   `-- verify.py
        |-- model_verification/
        |   |-- manifest.py
        |   |-- verify_models.py
        |   `-- verify_models.sh
        `-- sbom/
            `-- generate.py
```

## Phase 01 Tooling

* **Backend** — Python 3.12, `uv` workspace, Ruff, Mypy strict, pytest.
* **Frontend** — Node.js 22 LTS, `pnpm` workspaces, TypeScript, Tailwind.
* **Infrastructure** — Docker Compose (PostgreSQL 16, Redis 7, Qdrant,
  NATS JetStream, Ollama).
* **CI** — GitHub Actions (`.github/workflows/ci.yml`):
  foundation job (lockfile verify, Ruff, Mypy strict, pytest with
  coverage, gitleaks) and docker-smoke job (Compose up, healthchecks,
  SBOM).
* **Lockfile policy** — `tools/lockfile/verify.py` (uv + pnpm).
* **Compose hardening** — `docker-compose.yml` (loopback,
  `restart: unless-stopped`, healthchecks, resource limits,
  `stop_grace_period`, `depends_on.condition: service_healthy`).
* **Redis governance** — `backend/core/redis_governance.py`.
* **Qdrant governance** — `backend/core/qdrant_governance.py`.
* **Ollama adapter** — `backend/core/ollama.py` (ModelPort,
  EmbeddingPort, GenerationPort, VisionPort).
* **Backup** — `tools/backup/` (AES-256-GCM, PBKDF2-HMAC-SHA256
  600 000 iterations).
* **SBOM** — `tools/sbom/generate.py` (CycloneDX 1.5).
* **Model verification** — `tools/model_verification/` (manifest,
  digests, smoke inference).

## Document Precedence

When documents conflict, use this order:

1. Accepted architecture decision records.
2. `docs/prompts/master_context.md`.
3. Architecture and implementation contracts.
4. Product requirements.
5. Phase plans and status records.
6. Agent-specific prompts and local notes.

Conflicts must be resolved with an ADR, not silently interpreted.

## Starting a Work Session

1. Read `AGENTS.md`.
2. Read `docs/prompts/master_context.md`.
3. Read `docs/status/development_status.md`.
4. Read the active phase and relevant contracts.
5. Inspect the working tree and tests.
6. Declare the task, affected boundaries, verification plan, and unresolved decisions.

## Documentation Index

See [`docs/README.md`](docs/README.md) for the authoritative index and maintenance ownership.
