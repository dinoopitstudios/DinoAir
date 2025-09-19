from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging

from anyio import move_on_after
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from starlette.middleware.gzip import GZipMiddleware
from starlette.types import Receive, Scope, Send

from .errors import register_exception_handlers
from .logging_config import RequestResponseLoggerMiddleware, setup_logging
from .middleware.auth import AuthMiddleware
from .middleware.body_limit import BodySizeLimitMiddleware
from .middleware.content_type import ContentTypeJSONMiddleware
from .middleware.request_id import RequestIDMiddleware
from .settings import Settings


# Define locally to avoid linter/editor issues with starlette.types.ASGIApp
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

log = logging.getLogger("api.app")


class TimeoutMiddleware:
    """
    Cancels requests exceeding settings.request_timeout_seconds, returning 504.
    """

    def __init__(self, asgi_app: ASGIApp, timeout_seconds: int):
        self.app = asgi_app
        self.timeout_seconds = max(1, timeout_seconds)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)

        # Use move_on_after to avoid version-specific TimeoutError imports and exceptions
        with move_on_after(self.timeout_seconds) as cancel_scope:
            await self.app(scope, receive, send)
        if getattr(cancel_scope, "cancel_called", False) or getattr(
            cancel_scope, "cancelled_caught", False
        ):
            # Request exceeded the timeout window
            return await self._send_timeout(scope, receive, send)
        return None

    async def _send_timeout(self, scope: Scope, receive: Receive, send: Send):
        from starlette import status

        from core_router.errors import error_response as core_error_response

        trace_id = scope.get("trace_id", "")
        method = scope.get("method", "GET")
        path = scope.get("path", "")
        endpoint = f"{method} {path}"

        response = core_error_response(
            status=status.HTTP_504_GATEWAY_TIMEOUT,
            code="ERR_TIMEOUT",
            message="The request took too long to complete.",
            error="Timeout",
            details=None,
            endpoint=endpoint,
            operationId=None,
            requestId=str(trace_id) if isinstance(trace_id, str) and trace_id else None,
        )
        if trace_id:
            from contextlib import suppress

            with suppress(Exception):
                response.headers["X-Trace-Id"] = trace_id
        await response(scope, receive, send)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application with:
    - Strict CORS
    - Security middleware (Request ID, Body size limit, Auth)
    - Structured logging and request/response logging
    - Unified error handlers
    - Conditional OpenAPI/docs exposure in dev
    """
    settings = Settings()  # reads env with DINOAIR_ prefix

    # Initialize logging once per process
    setup_logging(settings)
    log.info(
        "Starting DinoAir API",
        extra={"env": settings.environment, "port": settings.port},
    )

    # Control OpenAPI/docs exposure
    openapi_url: str | None = (
        "/openapi.json" if (settings.is_dev and settings.expose_openapi_in_dev) else None
    )
    docs_url: str | None = "/docs" if (settings.is_dev and settings.expose_openapi_in_dev) else None
    redoc_url: str | None = (
        "/redoc" if (settings.is_dev and settings.expose_openapi_in_dev) else None
    )

    fastapi_app = FastAPI(
        title="DinoAir Local API",
        version="0.1.0",
        openapi_url=openapi_url,
        docs_url=docs_url,
        redoc_url=redoc_url,
        default_response_class=ORJSONResponse,
    )

    # Register exception handlers (canonical ErrorResponse responses)
    register_exception_handlers(fastapi_app)

    # CORS - strict, no wildcards
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "OPTIONS", "PUT", "PATCH"],
        allow_headers=["Content-Type", "X-DinoAir-Auth", "X-Request-ID", "X-Trace-Id"],
        expose_headers=["X-Trace-Id"],
        allow_credentials=False,
        max_age=600,
    )

    # Request pipeline middlewares (order matters):
    # Add short-circuiting middlewares first, then logging, and finally
    # RequestID as OUTERMOST so it can stamp trace_id on all responses.
    # Enforce JSON content-type for POSTs before any parsing/validation
    fastapi_app.add_middleware(ContentTypeJSONMiddleware)
    fastapi_app.add_middleware(BodySizeLimitMiddleware, settings=settings)
    fastapi_app.add_middleware(AuthMiddleware, settings=settings)
    fastapi_app.add_middleware(TimeoutMiddleware, timeout_seconds=settings.request_timeout_seconds)
    fastapi_app.add_middleware(RequestResponseLoggerMiddleware)
    fastapi_app.add_middleware(GZipMiddleware, minimum_size=1024)
    # Must be last-added to be outermost
    fastapi_app.add_middleware(RequestIDMiddleware)

    # Routers: import lazily to reduce import-time coupling and allow testing with stubs
    try:
        from .routes.health import router as health_router

        fastapi_app.include_router(health_router)
    except Exception:  # pragma: no cover
        log.exception("Failed to include health router")

    try:
        from .routes.translate import router as translate_router

        fastapi_app.include_router(translate_router)
    except Exception:  # pragma: no cover
        log.exception("Failed to include translate router")

    return fastapi_app

    try:
        from .routes.search import router as search_router

        app.include_router(search_router)
    except Exception:  # pragma: no cover
        log.exception("Failed to include search router")

    try:
        from .routes.config import router as config_router

        app.include_router(config_router)
    except Exception:  # pragma: no cover
        log.exception("Failed to include config router")

    # RAG router (new)
    try:
        from .routes.rag import router as rag_router

        app.include_router(rag_router)
    except Exception:  # pragma: no cover
        log.exception("Failed to include rag router")

    try:
        from .routes.metrics import router as metrics_router

        app.include_router(metrics_router)
    except Exception:  # pragma: no cover
        log.exception("Failed to include metrics router")

    try:
        from .routes.ai import router as ai_router

        app.include_router(ai_router)
    except Exception:  # pragma: no cover
        log.exception("Failed to include ai router")

    try:
        from .routes.router import router as router_router

        app.include_router(router_router)
    except Exception:  # pragma: no cover
        log.exception("Failed to include core router endpoints")

    # Add a root endpoint
    @app.get("/")
    async def root():
        """Root endpoint providing API information."""
        return {
            "message": "Welcome to DinoAir API",
            "version": "0.1.0",
            "status": "running",
            "endpoints": {
                "health": "/health",
                "docs": "/docs" if app.docs_url else "disabled",
                "openapi": "/openapi.json" if app.openapi_url else "disabled",
            },
        }

    return app


# Expose an ASGI application instance for servers (e.g., `uvicorn api.app:app`)
app: FastAPI = create_app()


# Also expose a factory for `--factory` usage:
#   uvicorn api.app:app_factory --factory
#   uvicorn api.app:create_app --factory
def app_factory() -> FastAPI:
    return create_app()
