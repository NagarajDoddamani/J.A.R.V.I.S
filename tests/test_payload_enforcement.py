"""HTTP-level tests for the payload policy enforcement middleware.

The tests use FastAPI's ``TestClient`` to drive real HTTP requests
through the middleware. They prove the five proof points required by
FND-012:

* Prompts are rejected.
* Raw memory is rejected.
* Documents are rejected.
* Embeddings are rejected.
* Secrets are rejected.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.core.middleware import PayloadEnforcementMiddleware  # noqa: E402
from backend.core.payload_policy import (  # noqa: E402
    PayloadPolicyError,
    SENSITIVE_KEYS,
    assert_clean,
    assert_clean_bytes,
    scan_dict,
)


# ---------------------------------------------------------------------------
# In-process scan tests
# ---------------------------------------------------------------------------


def test_scan_dict_finds_top_level_prompt() -> None:
    paths = scan_dict({"prompt": "hello"})
    assert paths == ["prompt"]


def test_scan_dict_finds_nested_raw_memory() -> None:
    paths = scan_dict({"meta": {"raw_memory": "x"}})
    assert paths == ["meta.raw_memory"]


def test_scan_dict_finds_embedding_inside_list() -> None:
    paths = scan_dict({"vectors": [{"embedding": [0.1, 0.2]}]})
    assert paths == ["vectors[0].embedding"]


def test_scan_dict_is_case_insensitive() -> None:
    paths = scan_dict({"API_KEY": "x"})
    assert paths == ["API_KEY"]


def test_scan_dict_finds_secret_password_token() -> None:
    paths = scan_dict({"password": "x", "token": "y", "secret": "z"})
    assert set(paths) == {"password", "token", "secret"}


def test_scan_dict_returns_empty_for_clean_payload() -> None:
    assert scan_dict({"request_id": "uuid", "metadata": {"a": 1}}) == []


def test_assert_clean_raises_on_prompt() -> None:
    with pytest.raises(PayloadPolicyError) as exc:
        assert_clean({"prompt": "leak"})
    assert exc.value.code == "SENSITIVE_KEY_DETECTED"


def test_assert_clean_raises_on_document() -> None:
    with pytest.raises(PayloadPolicyError):
        assert_clean({"document_body": "secret"})


def test_assert_clean_raises_on_embedding() -> None:
    with pytest.raises(PayloadPolicyError):
        assert_clean({"embedding": [0.1, 0.2]})


def test_assert_clean_raises_on_secret() -> None:
    with pytest.raises(PayloadPolicyError):
        assert_clean({"api_key": "leak"})


def test_assert_clean_raises_on_raw_memory() -> None:
    with pytest.raises(PayloadPolicyError):
        assert_clean({"raw_memory": "leak"})


def test_assert_clean_passes_for_clean_payload() -> None:
    assert_clean({"request_id": "uuid", "metadata": {}})


def test_assert_clean_handles_none_payload() -> None:
    assert_clean(None)


def test_assert_clean_rejects_non_dict_payload() -> None:
    with pytest.raises(PayloadPolicyError) as exc:
        assert_clean("just a string")
    assert exc.value.code == "INVALID_PAYLOAD"


def test_assert_clean_handles_cyclic_payload() -> None:
    # Build a cyclic structure manually. The scanner detects cycles
    # via id() and skips them gracefully.
    a: dict = {}
    b: dict = {"inner": a}
    a["back"] = b
    assert_clean(a)


# ---------------------------------------------------------------------------
# Bytes-level scan
# ---------------------------------------------------------------------------


def test_assert_clean_bytes_accepts_empty_body() -> None:
    assert_clean_bytes(b"", content_type="application/json")


def test_assert_clean_bytes_rejects_oversize() -> None:
    big = b"x" * (256 * 1024 + 1)
    with pytest.raises(PayloadPolicyError) as exc:
        assert_clean_bytes(big, content_type="application/json")
    assert exc.value.code == "BODY_TOO_LARGE"


def test_assert_clean_bytes_rejects_invalid_json() -> None:
    with pytest.raises(PayloadPolicyError) as exc:
        assert_clean_bytes(b"{not-json", content_type="application/json")
    assert exc.value.code == "INVALID_JSON"


def test_assert_clean_bytes_bypasses_non_scanned_content_type() -> None:
    # text/plain is not scanned; even if it contained a sensitive key
    # by accident, the policy does not inspect it.
    assert_clean_bytes(b"prompt=hello", content_type="text/plain")


def test_assert_clean_bytes_rejects_prompt_in_json() -> None:
    body = json.dumps({"prompt": "leak"}).encode("utf-8")
    with pytest.raises(PayloadPolicyError):
        assert_clean_bytes(body, content_type="application/json")


# ---------------------------------------------------------------------------
# FastAPI middleware HTTP tests
# ---------------------------------------------------------------------------


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(PayloadEnforcementMiddleware)

    @app.post("/v1/memories")
    async def create_memory(payload: dict) -> dict:
        return {"status": "accepted", "echo": payload}

    @app.get("/v1/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.post("/v1/health")
    async def health_post() -> dict:
        return {"status": "ok"}

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_build_test_app())


def test_middleware_rejects_prompt_in_request_body(client: TestClient) -> None:
    response = client.post(
        "/v1/memories",
        json={"prompt": "Tell me the user's secret"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "SENSITIVE_KEY_DETECTED"


def test_middleware_rejects_raw_memory_in_request_body(client: TestClient) -> None:
    response = client.post(
        "/v1/memories",
        json={"content": "ok", "raw_memory": "private"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SENSITIVE_KEY_DETECTED"


def test_middleware_rejects_document_in_request_body(client: TestClient) -> None:
    response = client.post(
        "/v1/memories",
        json={"document_body": "confidential report"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SENSITIVE_KEY_DETECTED"


def test_middleware_rejects_embedding_in_request_body(client: TestClient) -> None:
    response = client.post(
        "/v1/memories",
        json={"embedding": [0.1, 0.2, 0.3]},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SENSITIVE_KEY_DETECTED"


def test_middleware_rejects_secret_in_request_body(client: TestClient) -> None:
    response = client.post(
        "/v1/memories",
        json={"api_key": "sk-test"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SENSITIVE_KEY_DETECTED"


def test_middleware_rejects_nested_sensitive_payload(client: TestClient) -> None:
    response = client.post(
        "/v1/memories",
        json={"meta": {"transcript": "private audio"}},
    )
    assert response.status_code == 400


def test_middleware_accepts_clean_payload(client: TestClient) -> None:
    response = client.post(
        "/v1/memories",
        json={"request_id": "uuid", "metadata": {"reason": "user request"}},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


def test_middleware_skips_get_requests(client: TestClient) -> None:
    response = client.get("/v1/health")
    assert response.status_code == 200


def test_middleware_allows_post_to_exempt_path(client: TestClient) -> None:
    # Health endpoints are exempt because they are public probes.
    response = client.post("/v1/health", json={"prompt": "ignore"})
    assert response.status_code == 200


def test_middleware_rejects_oversize_body(client: TestClient) -> None:
    big = {"x": "a" * (256 * 1024 + 100)}
    response = client.post("/v1/memories", json=big)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BODY_TOO_LARGE"


def test_middleware_rejects_invalid_json(client: TestClient) -> None:
    response = client.post(
        "/v1/memories",
        content=b"{not-json",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_JSON"


# ---------------------------------------------------------------------------
# Coverage matrix
# ---------------------------------------------------------------------------


def test_sensitive_key_coverage_matches_addendum() -> None:
    """Lock the five FND-012 proof points in the policy surface."""
    required = {"prompt", "raw_memory", "document_body", "embedding", "api_key"}
    assert required.issubset(SENSITIVE_KEYS)
