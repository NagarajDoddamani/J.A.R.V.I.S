# JARVIS Foundation Tests

The Phase 01 tests run without external services. They exercise the
in-process governance primitives: NATS envelope validation, payload
size boundaries, and the sensitive-payload scan. Integration tests
against the live Compose stack live in a later phase.
