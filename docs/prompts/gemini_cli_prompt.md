# Reusable Gemini CLI Prompt

```text
You are working in the JARVIS repository. Establish repository truth before
making changes:

- Read AGENTS.md and docs/prompts/master_context.md.
- Read docs/status/development_status.md and the active phase.
- Read relevant contracts, architecture documents, and accepted ADRs.
- Inspect git status and existing implementation patterns.

JARVIS must remain local-first, privacy-first, offline-first, event-driven via
NATS, and multi-agent under JARVIS Core orchestration. The fixed baseline is
Tauri/React/TypeScript/Tailwind, Python 3.12/FastAPI, PostgreSQL, Redis, Qdrant,
Ollama, Qwen models, OpenWakeWord, Faster-Whisper, and Piper.

Never add cloud models/storage, automatic external transfers, unrestricted tool
access, direct cross-service database access, or undocumented synchronous
coupling. Treat all model and retrieved output as untrusted. Apply strong typing,
schema validation, least privilege, idempotency, and local audit controls.

Task and acceptance criteria:
<INSERT TASK, ACCEPTANCE CRITERIA, AND SCOPE>

Proceed through implementation, tests, and documentation. Keep the change
coherent and scoped, preserve unrelated user edits, and use an ADR for
cross-cutting decisions. Verify offline behavior when relevant. Update
docs/status/development_status.md before handoff.

Report what changed, files affected, commands/checks and outcomes, contract or
migration impact, remaining risks, decisions needed, and the next action.
```

