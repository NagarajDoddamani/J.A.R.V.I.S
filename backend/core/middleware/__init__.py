"""FastAPI middleware enforcing the JARVIS payload policy.

The middleware is the gateway-side enforcement point for Correction 5.
It is intentionally conservative: it scans only documented content
types, rejects over-size bodies, and never logs the offending body.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.logging import logger
from backend.core.payload_policy import (
    PayloadPolicyError,
    assert_clean_bytes,
)

# Endpoints that are exempt from the policy because they don't carry a
# durable payload. Health, readiness, and version probes are public
# and must remain unauthenticated and payload-free.
_EXEMPT_PATH_SUFFIXES: tuple[str, ...] = (
    "/health",
    "/ready",
    "/system/status",
    "/openapi.json",
    "/docs",
    "/redoc",
)

# Methods that may carry a request body. The middleware short-circuits
# for read-only methods to keep the path fast.
_BODY_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH"})


def _is_exempt(path: str) -> bool:
    return any(path.endswith(suffix) for suffix in _EXEMPT_PATH_SUFFIXES)


class PayloadEnforcementMiddleware(BaseHTTPMiddleware):
    """Reject HTTP requests whose bodies violate the JARVIS policy.

    Behaviour:
    * Read-only methods bypass the scan.
    * Exempt paths (health, readiness, OpenAPI) bypass the scan.
    * Bodies larger than :data:`MAX_SCANNED_BODY_BYTES` are rejected.
    * Bodies whose ``Content-Type`` is not in
      :data:`SCANNED_CONTENT_TYPES` are forwarded untouched.
    * JSON bodies are parsed and scanned for sensitive keys.
    * The middleware NEVER logs the offending body; only the error code
      and a redacted summary are emitted.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method not in _BODY_METHODS or _is_exempt(request.url.path):
            return await call_next(request)

        body = await request.body()
        try:
            assert_clean_bytes(
                body,
                content_type=request.headers.get("content-type"),
            )
        except PayloadPolicyError as exc:
            logger.warning(
                "Payload policy violation rejected",
                method=request.method,
                path=request.url.path,
                code=exc.code,
                correlation_id=request.headers.get("x-correlation-id"),
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                    }
                },
            )

        # Starlette caches the body after .body() is consumed; we
        # rebuild a fresh request with the same body so downstream
        # handlers can read it.
        request = Request(request.scope, receive=lambda: {"type": "http.request", "body": body, "more_body": False})
        return await call_next(request)


__all__ = ["PayloadEnforcementMiddleware"]
