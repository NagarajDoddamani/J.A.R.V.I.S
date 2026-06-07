# AI Agent Operating Contract

This file applies to Codex, Claude Code, Gemini CLI, Cursor, and any future coding agent operating in this repository.

## Required Context Load

Before changing files, read:

1. `docs/prompts/master_context.md`
2. `docs/status/development_status.md`
3. The active document in `docs/development/`
4. Relevant files in `docs/architecture/`, `docs/implementation/`, and `docs/decisions/`

## Operating Rules

- Preserve local-first, privacy-first, offline-first behavior.
- Do not introduce cloud services, remote telemetry, hosted AI, or external persistence.
- Do not bypass NATS with undocumented service-to-service coupling.
- Do not let agents access infrastructure clients directly; use application ports.
- Do not store secrets, raw credentials, or unrestricted sensitive content.
- Do not implement an unresolved cross-cutting choice without an ADR.
- Keep changes scoped to one coherent task.
- Add or update tests and contracts with behavior changes.
- Update `docs/status/development_status.md` before handoff.
- Record assumptions explicitly; never present an unverified assumption as fact.

## Definition of Done

A task is complete only when:

- Acceptance criteria are met.
- Architecture boundaries remain intact.
- Static checks and relevant tests pass.
- Event, API, and persistence contracts are updated if affected.
- Security, privacy, and offline behavior have been considered.
- Documentation and development status reflect the final state.
- No secrets, generated artifacts, or machine-specific paths are committed.

## Handoff Format

Every handoff must include:

```text
Objective:
Completed:
Files changed:
Contracts changed:
Validation performed:
Known issues:
Decisions required:
Recommended next action:
```

The durable handoff belongs in `docs/status/development_status.md`; chat history is not project memory.

