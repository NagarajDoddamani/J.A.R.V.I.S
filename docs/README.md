# Documentation Index

JDOS v1.2 is the durable source of project context. Documentation is versioned
with code and reviewed through the same change process.

Current architecture correction authority:
[`architecture/JDOS_v1.2_Architecture_Corrections_Addendum.md`](architecture/JDOS_v1.2_Architecture_Corrections_Addendum.md).

| Area | Purpose | Primary owner |
|---|---|---|
| `PRD/` | Product outcomes, users, scope, and acceptance criteria | Product/architecture |
| `architecture/` | System topology, boundaries, security, and quality attributes | Architecture |
| `development/` | Ordered delivery phases and engineering workflow | Engineering lead |
| `implementation/` | Enforceable API, event, database, and coding contracts | Service owners |
| `decisions/` | Immutable architecture decision history | Architecture council |
| `status/` | Current operational handoff state | Active task owner |
| `prompts/` | Shared and tool-specific AI context | Architecture/AI systems |

## Maintenance Rules

- Update documentation in the same change as behavior.
- Use RFC 2119 terms (`MUST`, `SHOULD`, `MAY`) deliberately.
- Prefer diagrams and schemas that can be reviewed as text.
- Every contract has a version and compatibility policy.
- Dates use ISO 8601. Identifiers use UUIDv7 when ordering is useful.
- Remove stale statements rather than appending contradictory notes.
- ADRs are superseded, never rewritten to hide prior decisions.

## Review Cadence

- Status document: every completed task and every agent handoff.
- Phase document: at phase entry, weekly during execution, and at exit.
- Contracts: whenever producers, consumers, endpoints, or storage behavior change.
- Architecture and PRD: at milestone boundaries or through an ADR-backed change.
- Master context and agent prompts: after any accepted architectural change.
