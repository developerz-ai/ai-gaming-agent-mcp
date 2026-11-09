"""HTTP/SSE server for AI Gaming Agent MCP.

This module provides a FastAPI-based HTTP server with Server-Sent Events (SSE)
transport for the MCP protocol. It enables remote control of gaming PCs over HTTP
with Bearer token authentication.

Endpoints:
    GET /health - Health check endpoint
    GET /mcp - SSE connection endpoint (requires Bearer token)
    POST /mcp/messages - Message posting endpoint (requires Bearer token)
"""

from __future__ import annotations

import hashlib
import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from mcp.server.sse import SseServerTransport

from ai_gaming_agent import __version__
from ai_gaming_agent.config import Config
from ai_gaming_agent.server import create_server

if TYPE_CHECKING:
    from mcp.server import Server

logger = logging.getLogger(__name__)

# Global state for the server
_mcp_server: Server | None = None
_sse_transport: SseServerTransport | None = None
_config: Config | None = None

# Security scheme for Bearer token auth
security = HTTPBearer()


def get_config() -> Config:
    """Get the current configuration."""
    if _config is None:
        return Config.load()
    return _config


def validate_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Validate Bearer token against configured password.

    Args:
        credentials: HTTP Bearer credentials from the request.

    Returns:
        The validated token.

    Raises:
        HTTPException: If authentication fails.
    """
    config = get_config()

    # If no password is set, reject all requests for security
    if not config.server.password:
        logger.warning("Authentication failed: No password configured")
        raise HTTPException(
            status_code=403,
            detail="Server not configured with password. Set server.password in config.",
        )

    if credentials.credentials != config.server.password:
        logger.warning("Authentication failed: Invalid token")
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    return credentials.credentials


def _principal_for(token: str) -> AuthenticatedUser:
    """Build the MCP principal that `token` authenticates as.

    This server has one shared password, so every authenticated request is the
    same principal, named here by a digest of that credential: the digest keeps
    the password itself out of the ASGI scope while staying stable, so the SSE
    endpoint and the POST endpoint derive the same identity from the same token.
    ``AccessToken.token`` therefore holds a fingerprint, never the credential.

    Args:
        token: A bearer token that already passed `validate_token`.

    Returns:
        The principal to record in ``scope["user"]``.
    """
    fingerprint = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return AuthenticatedUser(AccessToken(token=fingerprint, client_id=fingerprint, scopes=["mcp"]))


async def require_authenticated_principal(
    request: Request,
    token: str = Depends(validate_token),
) -> None:
    """Authenticate the request and record its principal in the ASGI scope.

    The mcp SSE transport binds each session to the principal that opened it
    and re-checks that principal on every posted message, but it only records
    an owner for an `AuthenticatedUser` in ``scope["user"]``. Without this both
    sides are ``None`` and the comparison is vacuous; with it, GET /mcp and
    POST /mcp/messages record the same principal derived from the bearer token,
    so the transport compares real principals and a session cannot be opened
    without one being recorded for it.

    This is not per-client isolation. One shared password yields one principal
    for every client, so any holder of that password still matches every
    session; separating clients requires per-client credentials.

    Args:
        request: The incoming HTTP request whose scope is annotated.
        token: Validated Bearer token (dependency).
    """
    request.scope["user"] = _principal_for(token)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    global _mcp_server, _sse_transport

    logger.info(f"Starting AI Gaming Agent HTTP Server v{__version__}")

    # Create MCP server
    _mcp_server = create_server(_config)

    # Create SSE transport - messages will be posted to /mcp/messages
    _sse_transport = SseServerTransport("/mcp/messages")

    logger.info("MCP server initialized with SSE transport")

    yield

    logger.info("Shutting down AI Gaming Agent HTTP Server")


def create_app(config: Config | None = None) -> FastAPI:
    """Create the FastAPI application.

    Args:
        config: Configuration object. If None, loads from default location.

    Returns:
        Configured FastAPI application.
    """
    global _config
    _config = config or Config.load()

    app = FastAPI(
        title="AI Gaming Agent",
        description="MCP server for remote PC automation",
        version=__version__,
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        """Health check endpoint.

        Returns:
            Health status including version information.
        """
        return {
            "status": "ok",
            "version": __version__,
        }

    @app.get("/mcp")
    async def handle_sse(
        request: Request,
        _principal: None = Depends(require_authenticated_principal),
    ) -> Response:
        """Handle SSE connections for MCP.

        This endpoint establishes a Server-Sent Events connection for bidirectional
        MCP communication. The client receives messages through the SSE stream and
        posts messages to /mcp/messages endpoint.

        Args:
            request: The incoming HTTP request.
            _principal: Authenticated principal (dependency); recorded in the
                scope so the transport can bind the session to it.

        Returns:
            Empty response after SSE connection ends.
        """
        if _sse_transport is None or _mcp_server is None:
            raise HTTPException(status_code=503, detail="Server not initialized")

        logger.info(f"New MCP SSE connection from {request.client}")

        async with _sse_transport.connect_sse(request.scope, request.receive, request._send) as streams:
            await _mcp_server.run(
                streams[0],
                streams[1],
                _mcp_server.create_initialization_options(),
            )

        logger.info(f"MCP SSE connection closed from {request.client}")

        # Return empty response to avoid NoneType error when client disconnects
        return Response()

    # Create ASGI wrapper for POST message handler with authentication
    async def mcp_post_handler(scope: dict, receive: Any, send: Any) -> None:
        """Handle POST requests for MCP messages with authentication.

        This is an ASGI wrapper that validates authentication before
        passing requests to the SSE transport's message handler.
        """
        if _sse_transport is None:
            response = Response("Server not initialized", status_code=503)
            await response(scope, receive, send)
            return

        # Create a Request object to extract the Authorization header
        request = Request(scope, receive)

        # Check for Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            response = Response("Missing or invalid authorization header", status_code=401)
            await response(scope, receive, send)
            return

        token = auth_header[7:]  # Strip "Bearer " prefix
        config = get_config()

        if not config.server.password:
            response = Response("Server not configured with password", status_code=403)
            await response(scope, receive, send)
            return

        if token != config.server.password:
            response = Response("Invalid authentication token", status_code=401)
            await response(scope, receive, send)
            return

        # Record the same principal the SSE endpoint derives from this token so
        # the transport can match this message to the session it opened.
        scope["user"] = _principal_for(token)

        # Authentication passed, forward to SSE transport
        await _sse_transport.handle_post_message(scope, receive, send)

    # Mount the POST handler at /mcp/messages
    app.mount("/mcp/messages", app=mcp_post_handler)

    return app


async def run_http_server(config: Config | None = None) -> None:
    """Run the HTTP/SSE MCP server.

    Args:
        config: Configuration object. If None, loads from default location.
    """
    import uvicorn

    config = config or Config.load()
    app = create_app(config)

    logger.info(f"Starting HTTP server on {config.server.host}:{config.server.port}")

    server_config = uvicorn.Config(
        app,
        host=config.server.host,
        port=config.server.port,
        log_level="info",
    )
    server = uvicorn.Server(server_config)
    await server.serve()
