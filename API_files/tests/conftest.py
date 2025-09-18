from __future__ import annotations

from pathlib import Path

# Test bootstrap: provide lightweight stubs for external modules to allow app import
import sys
from types import ModuleType
from typing import Any


try:
    from typing import TypedDict
except ImportError:
    from typing import TypedDict

# Make the package importable as `api` when running tests from the package dir
ROOT = Path(__file__).resolve().parent.parent
PARENT = ROOT.parent
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))


def _ensure_module(name: str, mod: ModuleType | None = None) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    m = mod or ModuleType(name)
    sys.modules[name] = m
    return m


# Stub core_router package with minimal APIs used by the app
core_router = _ensure_module("core_router")

# core_router.errors.error_response -> returns a FastAPI-compatible ASGI response callable
errors = ModuleType("core_router.errors")


def error_response(
    status: int,
    code: str,
    message: str,
    error: str,
    details: Any,
    endpoint: str,
    operation_id: str | None = None,
    request_id: str | None = None,
    **legacy_names: Any,
):
    from fastapi.responses import JSONResponse

    # Accept legacy camelCase via **legacy_names without violating naming conventions
    op_id = operation_id if operation_id is not None else legacy_names.get("operationId")
    req_id = request_id if request_id is not None else legacy_names.get("requestId")
    body: dict[str, Any] = {
        "status": status,
        "code": code,
        "message": message,
        "error": error,
        "details": details,
        "endpoint": endpoint,
        "operationId": op_id,
        "requestId": req_id,
    }
    return JSONResponse(status_code=status, content=body)


# Define exceptions referenced
class AdapterError(Exception):
    pass


class NoHealthyService(Exception):
    pass


class ServiceNotFound(Exception):
    pass


class ValidationError(Exception):
    def errors(self) -> list[Any]:
        return []


errors.error_response = error_response
errors.AdapterError = AdapterError
errors.NoHealthyService = NoHealthyService
errors.ServiceNotFound = ServiceNotFound
errors.ValidationError = ValidationError

sys.modules["core_router.errors"] = errors

# core_router.metrics
metrics = ModuleType("core_router.metrics")
metrics.snapshot = lambda: {"uptimeSeconds": 0}


def minimal_snapshot() -> dict[str, Any]:
    return {
        "uptimeSeconds": 0,
        "requests": {"total": 0, "error": 0},
        "adapters": {},
    }


metrics.minimal_snapshot = minimal_snapshot
sys.modules["core_router.metrics"] = metrics

# core_router.health
health = ModuleType("core_router.health")


def _health_response() -> tuple[dict[str, Any], int]:
    checks: dict[str, Any] = {}
    return {"status": "ok", "checks": checks}, 200


health.health_response = _health_response
health.version_info = lambda: {"version": "test", "build": "dev", "commit": "deadbeef"}
sys.modules["core_router.health"] = health

# Registry/router minimal stubs used by router_client
config = ModuleType("core_router.config")


def load_services_from_file(path: str | Path) -> list[Any]:
    # Minimal stub returns empty service list; reference param to avoid unused-arg warnings
    _ = path
    return []


config.load_services_from_file = load_services_from_file
sys.modules["core_router.config"] = config

registry = ModuleType("core_router.registry")


class ServiceRegistry:
    def __init__(self):
        self._services: list[Any] = []

    def register(self, s: Any) -> None:
        self._services.append(s)


registry.ServiceRegistry = ServiceRegistry
sys.modules["core_router.registry"] = registry

router_mod = ModuleType("core_router.router")


class Message(TypedDict):
    content: str


class Choice(TypedDict):
    message: Message


class Usage(TypedDict):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ExecuteByResult(TypedDict):
    choices: list[Choice]
    model: str
    usage: Usage


class ServiceRouter:
    def __init__(
        self,
        registry: ServiceRegistry,
        adapter_factory: Any = None,
        *,
        logger: Any = None,
    ):
        # Minimal stub, matches real ServiceRouter signature
        self._registry = registry

    def execute(self, service_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        # Echo back for testing
        if service_name == "translator.local.default":
            language = payload.get("target_language") or "python"
            return {
                "success": True,
                "language": language,
                "code": "print(1)",
                "errors": [],
                "warnings": [],
                "metadata": {},
            }
        # Keyword path by default
        return {"hits": []} if service_name == "search.local.default" else {}

    def execute_by(self, tag: str, payload: dict[str, Any], policy: str) -> ExecuteByResult:
        # Reference parameters to avoid unused-argument warnings in this stub.
        _ = (tag, payload, policy)
        return {
            "choices": [{"message": {"content": "hello"}}],
            "model": "test",
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }


router_mod.ServiceRouter = ServiceRouter
sys.modules["core_router.router"] = router_mod

# Stub pseudocode_translator
pseudocode_translator = _ensure_module("pseudocode_translator")
integration = ModuleType("pseudocode_translator.integration")
api_mod = ModuleType("pseudocode_translator.integration.api")


class TranslatorResult(TypedDict):
    success: bool
    language: str
    code: str
    errors: list[Any]
    warnings: list[Any]
    metadata: dict[str, Any]


class TranslatorAPI:
    def __init__(self):
        # Minimal stub for tests
        pass

    def translate(
        self, text: str, *, language: str, use_streaming: bool = False
    ) -> TranslatorResult:
        # Reference arguments to avoid unused-argument warnings in stub
        _ = (text, use_streaming)
        return {
            "success": True,
            "language": language,
            "code": "print('ok')",
            "errors": [],
            "warnings": [],
            "metadata": {"inputPreview": text[:20]},
        }


api_mod.TranslatorAPI = TranslatorAPI
sys.modules["pseudocode_translator.integration.api"] = api_mod
sys.modules["pseudocode_translator.integration"] = integration

# Removed legacy src.* test stubs
