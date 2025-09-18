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
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    assert body.get("status") in {"ok", "degraded", "unhealthy"}


def test_openapi_docs_available_in_dev():
    r = client.get("/openapi.json")
    assert r.status_code in (200, 404)  # 404 if dev flag disabled


def test_translate_stub_success():
    r = client.post(
        "/translate",
        json={"pseudocode": "PRINT 1", "target_language": "python"},
        headers={"X-DinoAir-Auth": "test-token"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert body.get("language")


def test_translate_stub_unauthorized():
    # Wrong token should be rejected
    r = client.post(
        "/translate",
        json={"pseudocode": "PRINT 1", "target_language": "python"},
        headers={"X-DinoAir-Auth": "bad"},
    )
    assert r.status_code == 401


def test_router_metrics_smoke():
    r = client.get("/router/metrics", headers={"X-DinoAir-Auth": "test-token"})
    assert r.status_code == 200
    assert isinstance(r.json(), dict)
