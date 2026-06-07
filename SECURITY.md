# Security Policy

**JDOS version:** 1.2 · **Effective date:** 2026-06-07

JARVIS is a local-first, privacy-first, offline-first personal AI
operating environment. Security is enforced at every trust boundary
and the foundation is locked to non-negotiable constraints.

## Supported Versions

The Foundation layer is the only release surface in Phase 01. The
current and only supported version is the contents of ``main`` on
the `J.A.R.V.I.S` repository. Older snapshots are not patched.

## Reporting a Vulnerability

Report security issues privately to the JARVIS security owner at
`<security-contact-placeholder>`. Do **not** file a public GitHub
issue. The security owner will:

1. Acknowledge the report within 72 hours.
2. Triage and assign a severity within 5 business days.
3. Coordinate disclosure timing with the reporter.
4. Credit the reporter in the release notes (unless anonymity is
   requested).

## Local-Only Security Posture

JARVIS never uploads, syncs, or stores user data on a remote
service. The threat model is therefore scoped to local actors
(malicious plugins, prompt-injection payloads in approved
documents, malicious models, and on-disk adversaries).

### Trust Boundaries

```
User Session  →  Local Runtime  →  Protected Local Data
   (UI)         (Agents, NATS)      (PostgreSQL, Qdrant,
                                     encrypted backups)
```

External network content is **untrusted** and disabled by default.

### Non-Negotiable Rules

* Deny-by-default for filesystem, process, sensor, and network access.
* No plaintext secrets in source control, logs, or durable events.
* All durable NATS payloads are reference-only; sensitive content
  is never serialised.
* All backups are encrypted with AES-256-GCM and a user-controlled
  passphrase (PBKDF2-HMAC-SHA256, 600 000 iterations).
* No cloud AI, cloud database, cloud memory, cloud embedding,
  cloud storage, or automatic external transfer is authorised.
* Failure of mandatory audit-write causes the action to fail closed.

## Threat Catalog and Mitigations

| Threat | Mitigation |
|---|---|
| Prompt injection in approved documents | Untrusted content is marked; instructions and evidence are separated; tool policy is outside model context. |
| Malicious model output | Schema validation, allowlisted tools, argument validation, confirmation gates. |
| Agent privilege escalation | Central policy decision, scoped capability grants, no direct infrastructure access. |
| Sensitive data in logs/events | Field classification, redaction, payload minimisation, automated tests. |
| Unauthorized local client | Loopback binding, per-install secret, OS user permissions, origin checks. |
| Database theft | OS full-disk encryption, least-privilege DB roles, encrypted backups. |
| Supply-chain compromise | Lockfiles, hashes/signatures where available, SBOM (FND-010), dependency scanning. |
| Event replay/duplication | Event IDs, idempotency store, timestamp windows for commands. |
| Destructive automation | Preview, confirmation, reversible operations, audit, compensating action. |
| Sensor surveillance | User activation, persistent indicator, timeout, hardware/OS permissions. |
| Secret leakage in source tree | gitleaks scan in CI, .gitleaks.toml allow-list, foundation secret-pattern test. |
| Backup tampering | AES-256-GCM auth tag, manifest SHA-256 cross-check, restore verification script. |

## Secret Management

* The initial product assumes one authenticated OS user.
* Tauri-to-API calls use a per-install secret in the OS credential
  manager.
* Service credentials are unique, rotated, and injected at runtime.
* The recovery passphrase for backups is held by the user outside
  the backup. Losing the passphrase is unrecoverable by design.
* Database and NATS ports bind to private local networks or
  loopback.

## Audit

* The Audit Service owns the ``audit`` PostgreSQL schema. It is
  append-only, hash-chained, and content-minimized.
* Agents have no general read access. Only the authenticated local
  user and narrowly scoped security administration ports may
  query audit data.
* Failure to persist a mandatory audit record causes the
  associated sensitive action to fail closed.

## Architecture Fitness Gates

The CI pipeline (``.github/workflows/ci.yml``) runs the following
checks on every push and pull request:

* Ruff lint
* Mypy strict
* Pytest (foundation in-process)
* Architecture fitness tests (including the secret-pattern test)
* gitleaks secret scan
* Compose smoke (when the docker service is available)

A red CI blocks merges. The exit criteria for Phase 01 are gated
by these checks.

## Security Gates Before Each Release

Before a release is tagged:

* Run dependency, secret, static, and container scans.
* Exercise abuse cases for prompts, events, files, and tool
  arguments.
* Verify outbound network denial.
* Verify complete deletion across PostgreSQL, Qdrant, caches, and
  backups policy.
* Verify durable NATS payloads contain only references and
  approved metadata.
* Verify backup manifests exclude all secret-bearing sources.
* Resolve all critical/high findings or document a time-bounded
  accepted risk through an ADR.

## Security Contacts

* Foundation security owner: see repository ``CODEOWNERS``.
* Vulnerability reports: see *Reporting a Vulnerability* above.

## Acknowledgements

JARVIS security is informed by OWASP LLM Top 10, NIST SP 800-53
(local-only profile), and the CWE catalogue.
