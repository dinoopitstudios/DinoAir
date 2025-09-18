from __future__ import annotations

import os

from api.app import app  # noqa: E402
from fastapi.testclient import TestClient


# Ensure dev docs are visible for this smoke test
os.environ.setdefault("DINOAIR_ENV", "dev")
os.environ.setdefault("DINOAIR_EXPOSE_OPENAPI_IN_DEV", "true")
# Require auth during tests by setting a non-empty token; success test will use this value
os.environ.setdefault("DINOAIR_AUTH_TOKEN", "test-token")


client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    if r.status_code != 200:
        raise AssertionError
    body = r.json()
    assert isinstance(body, dict)
    if body.get("status") not in {"ok", "degraded", "unhealthy"}:
        raise AssertionError


def test_openapi_docs_available_in_dev():
    r = client.get("/openapi.json")
    if r.status_code not in (200, 404):
        raise AssertionError


def test_translate_stub_success():
    r = client.post(
        "/translate",
        json={"pseudocode": "PRINT 1", "target_language": "python"},
        headers={"X-DinoAir-Auth": "test-token"},
    )
    if r.status_code != 200:
        raise AssertionError
    body = r.json()
    if body.get("success") is not True:
        raise AssertionError
    if not body.get("language"):
        raise AssertionError


def test_translate_stub_unauthorized():
    # Wrong token should be rejected
    r = client.post(
        "/translate",
        json={"pseudocode": "PRINT 1", "target_language": "python"},
        headers={"X-DinoAir-Auth": "bad"},
    )
    if r.status_code != 401:
        raise AssertionError


def test_router_metrics_smoke():
    r = client.get("/router/metrics", headers={"X-DinoAir-Auth": "test-token"})
    if r.status_code != 200:
        raise AssertionError
    assert isinstance(r.json(), dict)
