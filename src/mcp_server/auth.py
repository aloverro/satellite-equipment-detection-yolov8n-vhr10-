"""API Key authentication utilities for the MCP server."""

from __future__ import annotations

import os
import secrets
import logging
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request as StarletteRequest
from starlette.applications import Starlette
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Only protect paths that start with this prefix
PROTECTED_PREFIX = "/mcp"


class AuthConfig:
    """Holds authentication configuration for the process lifetime."""

    def __init__(self) -> None:
        self.env = os.getenv("ENV", "local").lower()
        raw_key = os.getenv("MCP_API_KEY")
        self.dev_generated: bool = False

        if not raw_key:
            if self.env in ("local", "development"):
                raw_key = secrets.token_urlsafe(32)
                # Optionally export so other modules (and subprocesses) can read it
                os.environ["MCP_API_KEY"] = raw_key
                self.dev_generated = True
                logger.warning(
                    "[DEV ONLY] Generated temporary MCP_API_KEY: %s",
                    raw_key,
                )
                logger.warning("Set MCP_API_KEY env var to persist the key across restarts.")
            else:
                # Fail fast; we don't want runtime 500s later.
                raise RuntimeError(
                    f"MCP_API_KEY must be set for {self.env} environment"
                )

        self.api_key: str = raw_key
        logger.info(
            "API key authentication enabled (env=%s, generated_dev=%s)",
            self.env,
            self.dev_generated,
        )

auth_config = AuthConfig()


def _extract_token_from_headers(request: Request) -> Optional[str]:
    """Extract the API key from supported headers.

    Priority order:
      1. Authorization: Bearer <token>
      2. X-API-Key: <token>
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip() or None
    x_api_key = request.headers.get("X-API-Key")
    if x_api_key:
        return x_api_key.strip() or None
    return None


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Starlette/ASGI middleware enforcing API key authentication for /mcp paths.

    Anything whose path starts with the PROTECTED_PREFIX requires a valid API key.
    Other paths (health, docs, root, etc.) are left open implicitly.
    """

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: StarletteRequest, call_next):
        if request.url.path.startswith(PROTECTED_PREFIX):
            token = _extract_token_from_headers(request)
            if not token:
                return JSONResponse({"detail": "Authorization or X-API-Key header required"}, status_code=401, headers={"WWW-Authenticate": "Bearer"})
            if not secrets.compare_digest(token, auth_config.api_key):
                return JSONResponse({"detail": "Invalid API key"}, status_code=401, headers={"WWW-Authenticate": "Bearer"})
        return await call_next(request)


class APIKeyFastMCP(FastMCP):
    """FastMCP subclass that injects API key middleware for /mcp endpoints.

    We override streamable_http_app to wrap the Starlette instance with the
    middleware.
    """

    def streamable_http_app(self) -> Starlette:
        app = super().streamable_http_app()
        # Insert middleware (adds to the stack; order matters, keep auth early)
        app.add_middleware(APIKeyAuthMiddleware)
        return app

__all__ = ["APIKeyFastMCP"]
