# Ollama Adapter Boundary (Phase 01, FND-007)

JARVIS has a single, non-bypassable boundary for the local model
runtime. The boundary is `backend/core/ollama.py`. Every consumer
must go through the `OllamaAdapter`. No other module in the
backend may import `httpx`, open a socket to the model daemon, or
spawn a subprocess against the Ollama CLI.

## Ports

The adapter implements four port interfaces:

| Port | Purpose |
|---|---|
| `ModelPort` | health, listing, and availability checks |
| `EmbeddingPort` | text → vector (used by the Memory and Knowledge services) |
| `GenerationPort` | text → text (used by the Orchestration and Coding services) |
| `VisionPort` | image bytes → text (used by the Vision Agent) |

Every method on the adapter:

* validates the model name against the canonical manifest
  (`tools/model_verification/manifest.py`),
* enforces the loopback-only URL guard (refuses any non-
  `127.0.0.1` / `localhost` / `::1` host),
* enforces a hard `request_timeout` and a smaller `connect_timeout`,
* retries transient errors with bounded exponential backoff
  (3 attempts by default, capped at 8 seconds),
* fails closed on every non-success response with a typed
  exception.

## URL Guard

The adapter parses `OLLAMA_BASE_URL` and refuses to start when
the host is not on the loopback. This is a defense-in-depth
check on top of the docker-compose loopback binding. The URL is
configured in `backend/core/config.py` and may be overridden by
environment; the loopback check is unconditional.

## Manifest Reconciliation

`OllamaAdapter.resolve_spec(name)` returns the canonical
`ModelSpec` for a name, or raises `OllamaUnsupportedModelError`.
Aliases declared in `MODEL_ALIASES` are accepted; unknown names
are rejected before any HTTP call is made.

## Errors

| Error | When |
|---|---|
| `OllamaError` | base class |
| `OllamaConnectionError` | daemon unreachable after all retries |
| `OllamaTimeoutError` | request exceeded the per-request timeout |
| `OllamaUnsupportedModelError` | model is not approved or not installed |
| `OllamaResponseError` | daemon returned 4xx / 5xx with a meaningful body |

## Tests

`tests/test_ollama_adapter.py` covers:

* the manifest reconciliation logic (alias-aware),
* the loopback URL guard,
* retry behaviour on transient connection errors,
* 404 → `OllamaUnsupportedModelError`,
* 5xx → retry-then-error,
* timeout → `OllamaTimeoutError`,
* embed / generate / describe happy paths with a mocked
  `httpx.AsyncClient`.

## CI Gate

`tests/test_architecture_fitness.py` enforces:

* the `OllamaAdapter` is the only place that imports `httpx`
  outside `tests/` (the verification tool and the bootstrap
  scripts are exempt),
* the loopback URL guard is non-bypassable.

## Out of Scope (Phase 02+)

* Service-internal model selection and prompt templating live
  in Phase 02 service code; the adapter only exposes the model
  ports.
* Streaming generation, tool-use, and function calling land in
  Phase 02; Phase 01 uses non-streaming `stream: false` calls.
