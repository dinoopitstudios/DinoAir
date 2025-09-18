from __future__ import annotations

import os
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.app import app, create_app  # noqa: E402
from api.metrics_state import snapshot as metrics_snapshot  # noqa: E402
from api.services import router_client  # noqa: E402
from core_router.errors import (
    AdapterError,
    NoHealthyService,
    ServiceNotFound,
)
from core_router.errors import ValidationError as CoreValidationError  # noqa: E402

# Ensure dev/docs and auth are consistently set for this test module
os.environ.setdefault("DINOAIR_ENV", "dev")
os.environ.setdefault("DINOAIR_EXPOSE_OPENAPI_IN_DEV", "true")
os.environ.setdefault("DINOAIR_AUTH_TOKEN", "test-token")


client = TestClient(app)

GOOD_AUTH = {"X-DinoAir-Auth": "test-token"}
BAD_AUTH = {"X-DinoAir-Auth": "bad"}


# -------------------------
# Router endpoints
# -------------------------


def test_router_execute_happy(monkeypatch: pytest.MonkeyPatch):
    class FakeRouter:
        def execute(self, service_name: str, payload: dict[str, Any]):
            assert service_name == "search.local.default"
            return {"hits": []}

    monkeypatch.setattr(router_client, "get_router", FakeRouter)

    r = client.post(
        "/router/execute",
        json={"serviceName": "search.local.default", "payload": {}},
        headers=GOOD_AUTH,
    )
    assert r.status_code == 200
    assert r.json() == {"hits": []}


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (ServiceNotFound("x"), 404),
        (NoHealthyService("x"), 503),
        (CoreValidationError("bad"), 422),
        (AdapterError("upstream"), 502),
    ],
)
def test_router_execute_errors(monkeypatch: pytest.MonkeyPatch, exc: Exception, expected: int):
    class FakeRouter:
        def execute(self, service_name: str, payload: dict[str, Any]):
            raise exc

    monkeypatch.setattr(router_client, "get_router", FakeRouter)

    r = client.post(
        "/router/execute", json={"serviceName": "svc", "payload": {}}, headers=GOOD_AUTH
    )
    assert r.status_code == expected


def test_router_execute_by_happy(monkeypatch: pytest.MonkeyPatch):
    class FakeRouter:
        def execute_by(self, tag: str, payload: dict[str, Any], policy: str):
            assert tag == "chat"
            return {
                "choices": [{"message": {"content": "hello"}}],
                "model": "test",
                "usage": {"total_tokens": 2},
            }

    monkeypatch.setattr(router_client, "get_router", FakeRouter)

    r = client.post(
        "/router/executeBy",
        json={"tag": "chat", "payload": {}, "policy": "first_healthy"},
        headers=GOOD_AUTH,
    )
    assert r.status_code == 200
    body = r.json()
    assert "choices" in body


def test_router_metrics_endpoint_smoke():
    r = client.get("/router/metrics", headers=GOOD_AUTH)
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


# -------------------------
# System endpoints (health, metrics, config)
# -------------------------


def test_health_endpoint_public():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    assert "status" in body


def test_metrics_endpoint_smoke():
    r = client.get("/metrics", headers=GOOD_AUTH)
    assert r.status_code == 200
    assert "uptimeSeconds" in r.json()


def test_config_dirs_happy(monkeypatch: pytest.MonkeyPatch):
    # Patch facade to return deterministic directory metadata including totals

    # Patch the already-imported alias in the route module so our lambda is used
    import api.routes.config as routes_config

    monkeypatch.setattr(
        routes_config,
        "svc_directory_settings",
        lambda: {
            "allowed_directories": ["/a", "/b"],
            "excluded_directories": ["/x"],
            "total_allowed": 2,
            "total_excluded": 1,
        },
    )

    r = client.get("/config/dirs", headers=GOOD_AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["total_allowed"] == 2
    assert body["total_excluded"] == 1


# -------------------------
# Search endpoints (keyword, vector, hybrid)
# -------------------------


def test_search_keyword_happy():
    r = client.post("/file-search/keyword", json={"query": "foo", "top_k": 5}, headers=GOOD_AUTH)
    assert r.status_code == 200
    body = r.json()
    assert "hits" in body
    assert isinstance(body["hits"], list)


def test_search_vector_happy():
    # Vector path consults ServiceRouter in this API layer (which is stubbed)
    r = client.post("/file-search/vector", json={"query": "foo", "top_k": 5}, headers=GOOD_AUTH)
    assert r.status_code == 200
    assert "hits" in r.json()


def test_search_hybrid_happy():
    r = client.post(
        "/file-search/hybrid",
        json={"query": "foo", "top_k": 5, "vector_weight": 0.6, "keyword_weight": 0.4},
        headers=GOOD_AUTH,
    )
    assert r.status_code == 200
    assert "hits" in r.json()


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (ServiceNotFound("x"), 404),
        (NoHealthyService("x"), 503),
        (CoreValidationError("bad"), 422),
        (AdapterError("upstream"), 502),
    ],
)
def test_search_keyword_error_mapping(
    monkeypatch: pytest.MonkeyPatch, exc: Exception, expected: int
):
    class FakeRouter:
        def execute(self, service_name: str, payload: dict[str, Any]):
            raise exc

    # For search routes, the router accessor is imported directly in the module.
    import api.routes.search as search_routes

    monkeypatch.setattr(search_routes, "get_router", FakeRouter)

    r = client.post("/file-search/keyword", json={"query": "foo", "top_k": 5}, headers=GOOD_AUTH)
    assert r.status_code == expected


# -------------------------
# AI chat endpoint
# -------------------------


def test_ai_chat_happy(monkeypatch: pytest.MonkeyPatch):
    class FakeRouter:
        def execute_by(self, tag: str, payload: dict[str, Any], policy: str):
            return {
                "choices": [{"message": {"content": "hello"}}],
                "model": "test",
                "usage": {"total_tokens": 2},
            }

    # Patch the router accessor as imported inside the ai route module
    import api.routes.ai as ai_routes

    monkeypatch.setattr(ai_routes.router_client, "get_router", FakeRouter)

    payload = {
        "messages": [{"role": "user", "content": "hi"}],
        "extra_params": {"router_tag": "chat"},
    }
    r = client.post("/ai/chat", json=payload, headers=GOOD_AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") in (
        True,
        False,
    )  # success is True when non-empty text is extracted
    assert "content" in body


def test_ai_chat_validation_error_422():
    payload = {"messages": []}  # invalid: empty list
    r = client.post("/ai/chat", json=payload, headers=GOOD_AUTH)
    assert r.status_code == 422


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (ServiceNotFound("x"), 404),
        (NoHealthyService("x"), 503),
        (CoreValidationError("bad"), 422),
        (AdapterError("upstream"), 502),
    ],
)
def test_ai_chat_error_mapping(monkeypatch: pytest.MonkeyPatch, exc: Exception, expected: int):
    class FakeRouter:
        def execute_by(self, tag: str, payload: dict[str, Any], policy: str):
            raise exc

    # Patch the accessor inside the ai route module to ensure our FakeRouter is used
    import api.routes.ai as ai_routes

    monkeypatch.setattr(ai_routes.router_client, "get_router", FakeRouter)

    payload = {
        "messages": [{"role": "user", "content": "hi"}],
        "extra_params": {"router_tag": "chat"},
    }
    r = client.post("/ai/chat", json=payload, headers=GOOD_AUTH)
    assert r.status_code == expected


# -------------------------
# Middleware behavior
# -------------------------


def test_content_type_middleware_415():
    # Wrong content-type must be rejected before body parsing; include valid auth to reach content-type middleware
    r = client.post(
        "/translate",
        data="text body",
        headers={"Content-Type": "text/plain", **GOOD_AUTH},
    )
    assert r.status_code == 415


def test_body_limit_middleware_413(monkeypatch: pytest.MonkeyPatch):
    # Create a fresh app with a tiny max body size to trigger 413
    monkeypatch.setenv("DINOAIR_MAX_REQUEST_BODY_BYTES", "10")
    app_small = create_app()
    small_client = TestClient(app_small)

    payload = {"pseudocode": "X" * 100}  # JSON well over 10 bytes
    r = small_client.post("/translate", json=payload, headers=GOOD_AUTH)
    assert r.status_code == 413


def test_request_id_header_present():
    r = client.get("/health")
    assert r.status_code == 200
    # Case-insensitive header mapping
    assert "x-trace-id" in {k.lower(): v for k, v in r.headers.items()}


def test_auth_middleware_401_and_bypass():
    # Protected endpoint without/invalid auth => 401
    r1 = client.post("/translate", json={"pseudocode": "print 1"})
    assert r1.status_code == 401

    r2 = client.post("/translate", json={"pseudocode": "print 1"}, headers=BAD_AUTH)
    assert r2.status_code == 401

    # /health is public even when auth is required
    rh = client.get("/health")
    assert rh.status_code == 200

    # Docs may be exposed in dev
    ro = client.get("/openapi.json")
    assert ro.status_code in (200, 404)


# -------------------------
# Error handler shape and metrics counters
# -------------------------


def test_error_handler_404_shape_and_metric_delta():
    before = metrics_snapshot()
    r = client.get("/does-not-exist", headers=GOOD_AUTH)
    after = metrics_snapshot()
    assert r.status_code == 404
    body = r.json()
    assert isinstance(body, dict)
    assert body.get("code") == "ERR_NOT_FOUND"
    assert body.get("error") == "Not Found"
    # Verify counters moved forward by at least one
    assert after.get("requests_total", 0) >= before.get("requests_total", 0) + 1
    assert after.get("status_4xx", 0) >= before.get("status_4xx", 0) + 1


def test_error_handler_422_shape_and_metric_delta():
    before = metrics_snapshot()
    # Missing required field 'pseudocode' triggers FastAPI RequestValidationError
    r = client.post("/translate", json={}, headers=GOOD_AUTH)
    after = metrics_snapshot()
    assert r.status_code == 422
    body = r.json()
    assert body.get("code") == "ERR_VALIDATION"
    assert body.get("error") == "Validation Error"
    assert after.get("requests_total", 0) >= before.get("requests_total", 0) + 1
    assert after.get("status_4xx", 0) >= before.get("status_4xx", 0) + 1
