# Coding Standards

## Universal Rules

- Prefer correctness, readability, and explicit boundaries over shortcuts.
- Apply SOLID and dependency inversion where they reduce coupling; do not create abstractions without a real boundary.
- Domain and application logic remain independent of frameworks and infrastructure.
- Public contracts are typed, versioned, validated, and documented.
- Functions and modules have one clear responsibility.
- Mutable global state, hidden I/O, wildcard imports, and catch-all error suppression are prohibited.
- Time is stored as UTC and serialized as RFC 3339; IDs use UUIDv7 where supported.
- Money, durations, sizes, and confidence values use explicit units.

## Python 3.12

- Use a `src/` layout and one package per deployable service.
- Ruff formats and lints; Pyright runs in strict mode; Pytest executes tests.
- Type all public and application-layer functions. Avoid `Any`; isolate unavoidable dynamic boundaries.
- Use Pydantic v2 for boundary DTOs and standard dataclasses or focused domain types internally.
- Use `Protocol` or abstract interfaces for ports and constructor injection for dependencies.
- Async code is used for I/O boundaries; never block the event loop with model, file, or CPU work.
- Exceptions are domain-specific. Translate exceptions to API/event errors at adapters.
- Use context managers for resources and explicit transaction scopes.
- Do not return ORM entities across repository boundaries.

Suggested package shape:

```text
src/jarvis_<service>/
|-- domain/
|-- application/
|   |-- ports/
|   `-- use_cases/
|-- adapters/
|   |-- inbound/
|   `-- outbound/
|-- bootstrap/
`-- config.py
```

## TypeScript and React

- Enable `strict`, `noUncheckedIndexedAccess`, and `exactOptionalPropertyTypes`.
- ESLint and Prettier are mandatory.
- Avoid `any`; use `unknown` and narrow it.
- Runtime-validate all backend, Tauri, storage, and event boundaries.
- Use named exports except framework-required entry points.
- Components render UI; hooks coordinate UI behavior; service modules own I/O.
- Keep server state separate from local UI state.
- Model workflows with discriminated unions/state machines, not scattered booleans.
- Effects must declare dependencies and clean up subscriptions.
- Never place secrets or sensitive persisted data in `localStorage`.

Suggested feature shape:

```text
src/
|-- app/
|-- features/<feature>/
|   |-- api/
|   |-- components/
|   |-- hooks/
|   |-- model/
|   `-- tests/
|-- shared/
`-- tauri/
```

## Naming

| Item | Convention | Example |
|---|---|---|
| Python module/function | `snake_case` | `create_memory` |
| Python class/protocol | `PascalCase` | `MemoryRepository` |
| TypeScript variable/function | `camelCase` | `createMemory` |
| React component/type | `PascalCase` | `MemoryPanel` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| NATS subject | lowercase dot segments | `jarvis.memory.created.v1` |
| Event type | uppercase snake case | `MEMORY_CREATED` |
| REST path | plural kebab-case nouns | `/v1/knowledge-sources` |
| Database object | `snake_case` | `memory_records` |
| Environment variable | `JARVIS_<AREA>_<NAME>` | `JARVIS_NATS_URL` |

## Folder and Dependency Standards

- Deployable applications live only in `backend/` and `frontend/`.
- Infrastructure definitions live in `infrastructure/`.
- Cross-language schemas and generated clients live in `shared/`.
- End-to-end and cross-service tests live in `tests/`; unit tests remain near owned code.
- Developer automation lives in `tools/`.
- Shared code cannot become a dumping ground for service business logic.
- Circular dependencies are prohibited.

## Testing Rules

- Follow a testing pyramid: domain unit, application unit, adapter contract, integration, then focused end-to-end tests.
- Tests use Arrange-Act-Assert and deterministic clocks, IDs, random seeds, and model fixtures.
- Mock ports, not internal implementation details.
- Every defect fix includes a regression test where practical.
- Required cases include success, validation, authorization, timeout, cancellation, retry, duplicate, and dependency failure.
- Core domain/application code has an 80% line coverage floor; security, policy, retention, and deletion behavior requires branch-focused coverage.
- Snapshot tests do not replace behavioral assertions.
- No test may require public internet access.

## Logging and Observability

- Emit structured JSON through a shared logging port.
- Required fields: timestamp, level, service, environment, event/action, correlation ID.
- Include trace, causation, actor, and resource IDs where applicable.
- Never log secrets, credentials, raw audio/images, full prompts, document bodies, embeddings, or Restricted data.
- Error logs include a stable error code and safe context, not raw payload dumps.
- Audit records are separate from diagnostic logs.

## Security Rules

- Validate and size-limit all boundary inputs.
- Use parameterized queries and safe subprocess argument arrays.
- Filesystem operations resolve canonical paths and enforce approved roots.
- Outbound hosts, executable paths, and Tauri commands are allowlisted.
- Use OS secret storage; never hardcode or commit credentials.
- Dependencies are pinned and scanned; new dependencies require justification.
- Model output and imported content are always untrusted.
- Sensitive actions require policy evaluation and, where specified, user confirmation.

## Documentation and Review

Public modules, non-obvious invariants, and ports require concise documentation. Comments explain why, not what. Reviewers prioritize correctness, boundaries, failure modes, security/privacy, tests, and operability.

