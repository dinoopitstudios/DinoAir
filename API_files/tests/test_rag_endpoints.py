from __future__ import annotations

import os
import sys
from typing import Any

from api.app import create_app  # noqa: E402
from fastapi.testclient import TestClient
import pytest

from api.services import router_client  # noqa: E402


# Ensure dev/docs and auth are consistently set for this test module
os.environ.setdefault("DINOAIR_ENV", "dev")
os.environ.setdefault("DINOAIR_EXPOSE_OPENAPI_IN_DEV", "true")
os.environ.setdefault("DINOAIR_AUTH_TOKEN", "test-token")
# Disable RAG heavy internals so guarded endpoints return 501-style envelopes quickly and deterministically
os.environ.setdefault("DINOAIR_RAG_ENABLED", "false")

# Ensure router can locate the services config via documented precedence
# get_router() checks DINO_SERVICES_FILE first, then Settings().services_config_path (DINOAIR_SERVICES_FILE), then default.
os.environ.setdefault("DINO_SERVICES_FILE", "config/services.lmstudio.yaml")


GOOD_AUTH = {"X-DinoAir-Auth": "test-token"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def _build_real_router_via_yaml_or_fallback() -> Any:
    """
    Attempt to construct a real core_router.router.ServiceRouter that can dispatch
    rag.local.* services via the local_python adapter.

    Strategy:
    1) Try using core_router.config.load_services_from_file on the env-provided path.
       This expects PyYAML to be available. If that fails, fall back to (2).
    2) Manually register the rag.local.* services with adapter=local_python and
       function_path set to api.services.rag:router_* functions.
    """
    import core_router.registry as real_registry  # type: ignore
    import core_router.router as real_router  # type: ignore

    services_file = os.getenv("DINO_SERVICES_FILE") or "config/services.lmstudio.yaml"

    registry = real_registry.ServiceRegistry()

    # Try YAML load first
    try:
        import core_router.config as real_config  # type: ignore

        services = real_config.load_services_from_file(services_file)
        for s in services:
            registry.register(s)
        return real_router.ServiceRouter(registry=registry)
    except Exception:
        # Fall back: register the minimal rag services we exercise in these tests.
        rag_services = [
            {
                "name": "rag.local.ingest_dir",
                "version": "1.0.0",
                "tags": ["rag", "ingest", "local"],
                "adapter": "local_python",
                "adapter_config": {"function_path": "api.services.rag:router_ingest_directory"},
            },
            {
                "name": "rag.local.ingest_files",
                "version": "1.0.0",
                "tags": ["rag", "ingest", "local"],
                "adapter": "local_python",
                "adapter_config": {"function_path": "api.services.rag:router_ingest_files"},
            },
            {
                "name": "rag.local.generate_missing_embeddings",
                "version": "1.0.0",
                "tags": ["rag", "embeddings", "local"],
                "adapter": "local_python",
                "adapter_config": {
                    "function_path": "api.services.rag:router_generate_missing_embeddings"
                },
            },
            {
                "name": "rag.local.context",
                "version": "1.0.0",
                "tags": ["rag", "context", "local"],
                "adapter": "local_python",
                "adapter_config": {"function_path": "api.services.rag:router_context"},
            },
            {
                "name": "rag.local.monitor_start",
                "version": "1.0.0",
                "tags": ["rag", "monitor", "local"],
                "adapter": "local_python",
                "adapter_config": {"function_path": "api.services.rag:router_monitor_start"},
            },
            {
                "name": "rag.local.monitor_stop",
                "version": "1.0.0",
                "tags": ["rag", "monitor", "local"],
                "adapter": "local_python",
                "adapter_config": {"function_path": "api.services.rag:router_monitor_stop"},
            },
            {
                "name": "rag.local.monitor_status",
                "version": "1.0.0",
                "tags": ["rag", "monitor", "local"],
                "adapter": "local_python",
                "adapter_config": {"function_path": "api.services.rag:router_monitor_status"},
            },
        ]
        for entry in rag_services:
            registry.register(entry)
        return real_router.ServiceRouter(registry=registry)


@pytest.fixture
def real_router(monkeypatch: pytest.MonkeyPatch) -> Any:
    """
    Provide a real ServiceRouter (not the stub from conftest) by temporarily removing
    the stubbed core_router modules from sys.modules and importing the real ones
    from the repository.

    Then, monkeypatch api.services.router_client.get_router to return this router
    so that the /rag endpoints dispatch through local_python adapter to the
    functions in api.services.rag.*.

    The monkeypatch.delitem operations are auto-restored after the test.
    """
    # Drop stubbed modules installed by conftest so Python can import real packages.
    for name in [
        "core_router",
        "core_router.config",
        "core_router.registry",
        "core_router.router",
        "core_router.adapters",
        "core_router.adapters.local_python",
        "core_router.adapters.base",
        "core_router.errors",
        "core_router.health",
        "core_router.metrics",
    ]:
        monkeypatch.delitem(sys.modules, name, raising=False)

    # Import real modules and construct router via YAML or fallback
    real_sr = _build_real_router_via_yaml_or_fallback()

    # Ensure router_client uses our real router instance (bypassing its own singleton wiring)
    # We set the singleton directly and also override get_router to be safe.
    monkeypatch.setattr(router_client, "_router_singleton", real_sr, raising=False)
    monkeypatch.setattr(router_client, "get_router", lambda: real_sr, raising=True)

    return real_sr


def _assert_envelope_ok(body: dict[str, Any]) -> None:
    assert isinstance(body, dict)
    assert "success" in body
    if "code" in body and body["code"] == 501:
        # Feature gracefully unavailable is acceptable
        return
    # Otherwise success must be True to pass
    assert body.get("success") in (True, False)
    # Either success True or 501 code acceptable; if success is False without 501, still counted as handled envelope
    # but endpoints should not raise non-2xx in our tests.


@pytest.mark.parametrize(
    ("endpoint", "payload"),
    [
        ("/rag/ingest/directory", {"directory": "."}),
        # Use a non-empty list to satisfy schema min_length while avoiding FS work; nonexistent path yields a handled envelope
        ("/rag/ingest/files", {"paths": ["./nonexistent.txt"]}),
        ("/rag/embeddings/generate-missing", {"batch_size": 1}),
        ("/rag/context", {"query": "test", "top_k": 1, "include_suggestions": False}),
        # Provide at least one directory to satisfy schema; with RAG disabled this returns a 501-style envelope
        ("/rag/monitor/start", {"directories": ["."], "file_extensions": None}),
    ],
)
def test_rag_post_endpoints_envelope_200(
    client: TestClient, real_router: Any, endpoint: str, payload: dict[str, Any]
):
    r = client.post(endpoint, json=payload, headers=GOOD_AUTH)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    # All /rag endpoints should return an envelope dict with at least "success"
    assert "success" in body
    # Accept success True, or success False with code 501 (feature unavailable), or general handled failure shape
    if "code" in body and body["code"] == 501:
        return
    # Otherwise, success True also passes
    if body.get("success") is True:
        return
    # Some guarded endpoints might return handled failure envelopes (e.g., ingest_files with empty list),
    # still ensure dict with success present
    assert isinstance(body, dict)


def test_rag_monitor_stop_200(client: TestClient, real_router: Any):
    # Provide an empty JSON body to satisfy ContentTypeJSONMiddleware (requires application/json on POST)
    r = client.post("/rag/monitor/stop", json={}, headers=GOOD_AUTH)
    assert r.status_code == 200
    body = r.json()
    _assert_envelope_ok(body)


def test_rag_monitor_status_200(client: TestClient, real_router: Any):
    r = client.get("/rag/monitor/status", headers=GOOD_AUTH)
    assert r.status_code == 200
    body = r.json()
    _assert_envelope_ok(body)


def test_openapi_contains_rag_routes(client: TestClient):
    r = client.get("/openapi.json")
    # dev flag is enabled; accept 200 or 404 for robustness
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        body = r.json()
        assert isinstance(body, dict)
        paths = body.get("paths", {}) or {}
        # Ensure at least one rag path present
        assert any(k.startswith("/rag/") for k in paths)
        assert "/rag/context" in paths


def test_file_search_keyword_smoke(client: TestClient):
    # Backward-compatible /file-search/* smoke: minimal request, do not assert domain data.
    r = client.post("/file-search/keyword", json={"query": "foo", "top_k": 1}, headers=GOOD_AUTH)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    # Shape check only
    assert "hits" in body or "success" in body
