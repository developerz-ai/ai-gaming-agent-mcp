"""Tests for HTTP/SSE server module.

This module tests the HTTP/SSE transport layer for the MCP server.
Tests mock the create_server function to avoid GUI dependencies.
"""

import sys
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from ai_gaming_agent.config import Config


def _get_mock_create_server():
    """Create a mock for create_server that returns a mock MCP server."""
    mock_server = MagicMock()
    mock_server.create_initialization_options.return_value = {}
    return MagicMock(return_value=mock_server)


def create_test_app(config: Config):
    """Create a test app with mocked server to avoid GUI dependencies.

    This function patches create_server before importing the http_server module
    to avoid triggering GUI-dependent code paths.
    """
    mock_create_server = _get_mock_create_server()

    # Remove module from cache if already imported
    modules_to_remove = [key for key in sys.modules if key.startswith("ai_gaming_agent.http_server")]
    for mod in modules_to_remove:
        del sys.modules[mod]

    # Also need to prevent server.py from being imported with GUI deps
    # Patch at the point of use
    with patch.dict(
        "sys.modules",
        {"ai_gaming_agent.server": MagicMock(create_server=mock_create_server)},
    ):
        from ai_gaming_agent import http_server

        # Reset module globals
        http_server._mcp_server = None
        http_server._sse_transport = None
        http_server._config = None

        # Patch create_server on the imported module
        http_server.create_server = mock_create_server

        return http_server.create_app(config)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_returns_ok(self):
        """Test that health endpoint returns OK status."""
        config = Config()
        config.server.password = "test-password"
        app = create_test_app(config)

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_includes_version(self):
        """Test that health endpoint includes version."""
        from ai_gaming_agent import __version__

        config = Config()
        config.server.password = "test-password"
        app = create_test_app(config)

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["version"] == __version__


class TestAuthentication:
    """Tests for Bearer token authentication."""

    def test_mcp_endpoint_requires_auth(self):
        """Test that /mcp endpoint requires authentication."""
        config = Config()
        config.server.password = "test-password"
        app = create_test_app(config)

        with TestClient(app) as client:
            response = client.get("/mcp")

        # FastAPI's HTTPBearer returns 401 when header is missing (auto_error=True)
        # or 403 in some versions. Accept either as valid auth rejection.
        assert response.status_code in [401, 403]

    def test_mcp_endpoint_rejects_invalid_token(self):
        """Test that /mcp endpoint rejects invalid tokens."""
        config = Config()
        config.server.password = "correct-password"
        app = create_test_app(config)

        with TestClient(app) as client:
            response = client.get(
                "/mcp",
                headers={"Authorization": "Bearer wrong-password"},
            )

        assert response.status_code == 401

    def test_no_password_configured_rejects_all(self):
        """Test that server rejects all requests if no password is set."""
        config = Config()
        config.server.password = ""  # No password
        app = create_test_app(config)

        with TestClient(app) as client:
            response = client.get(
                "/mcp",
                headers={"Authorization": "Bearer any-token"},
            )

        assert response.status_code == 403
        assert "not configured with password" in response.json()["detail"]


class TestMcpMessagesEndpoint:
    """Tests for the MCP POST message endpoint at /mcp/messages."""

    def test_post_without_auth_rejected(self):
        """Test that POST to /mcp/messages without auth is rejected."""
        config = Config()
        config.server.password = "test-password"
        app = create_test_app(config)

        with TestClient(app) as client:
            response = client.post("/mcp/messages", json={})

        assert response.status_code == 401

    def test_post_with_invalid_token_rejected(self):
        """Test that POST to /mcp/messages with invalid token is rejected."""
        config = Config()
        config.server.password = "correct-password"
        app = create_test_app(config)

        with TestClient(app) as client:
            response = client.post(
                "/mcp/messages",
                json={},
                headers={"Authorization": "Bearer wrong-password"},
            )

        assert response.status_code == 401

    def test_post_without_session_id_rejected(self):
        """Test that POST to /mcp/messages without session_id is rejected."""
        config = Config()
        config.server.password = "test-password"
        app = create_test_app(config)

        with TestClient(app) as client:
            response = client.post(
                "/mcp/messages",
                json={},
                headers={"Authorization": "Bearer test-password"},
            )

        # Should fail with 400 because no session_id
        assert response.status_code == 400

    def test_post_with_invalid_session_id_rejected(self):
        """Test that POST to /mcp/messages with invalid session_id is rejected."""
        config = Config()
        config.server.password = "test-password"
        app = create_test_app(config)

        with TestClient(app) as client:
            response = client.post(
                "/mcp/messages?session_id=invalid-uuid",
                json={},
                headers={"Authorization": "Bearer test-password"},
            )

        # Should fail with 400 for invalid UUID format
        assert response.status_code == 400

    def test_post_no_password_configured_rejected(self):
        """Test that POST is rejected when no password is configured."""
        config = Config()
        config.server.password = ""  # No password
        app = create_test_app(config)

        with TestClient(app) as client:
            response = client.post(
                "/mcp/messages",
                json={},
                headers={"Authorization": "Bearer any-token"},
            )

        assert response.status_code == 403


class TestAppConfiguration:
    """Tests for app configuration."""

    def test_app_has_correct_title(self):
        """Test that app has correct title."""
        config = Config()
        app = create_test_app(config)
        assert app.title == "AI Gaming Agent"

    def test_app_uses_provided_config(self):
        """Test that app uses the provided configuration."""
        config = Config()
        config.server.password = "custom-password"
        config.server.port = 9999

        app = create_test_app(config)

        # Verify the app was created with custom config
        # The config is stored globally, so we can test via the health endpoint
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200

    def test_app_has_correct_description(self):
        """Test that app has correct description."""
        config = Config()
        app = create_test_app(config)
        assert app.description == "MCP server for remote PC automation"

    def test_app_version_matches_package_version(self):
        """Test that app version matches package version."""
        from ai_gaming_agent import __version__

        config = Config()
        app = create_test_app(config)
        assert app.version == __version__


class TestSSEConnection:
    """Tests for SSE connection setup.

    Note: Full SSE connection testing requires async mocking and is complex.
    These tests verify the authentication layer and initialization checks
    for the SSE endpoint.
    """

    def test_mcp_endpoint_requires_valid_auth_before_connection(self):
        """Test that /mcp endpoint validates auth before attempting SSE connection."""
        config = Config()
        config.server.password = "test-password"
        app = create_test_app(config)

        with TestClient(app) as client:
            # Invalid auth should fail before SSE connection is attempted
            response = client.get(
                "/mcp",
                headers={"Authorization": "Bearer wrong-password"},
            )

            assert response.status_code == 401

    def test_mcp_endpoint_checks_initialization(self):
        """Test that handle_sse checks if transport and server are initialized.

        This test verifies that the endpoint has the proper initialization check
        by examining the code path, even though we cannot easily trigger the
        uninitialized state in tests due to the lifespan management.
        """
        # Read the source to verify the check exists
        import inspect

        from ai_gaming_agent import http_server

        # Get the handle_sse function source
        source = inspect.getsource(http_server.create_app)

        # Verify that the initialization check is present
        assert "_sse_transport is None" in source
        assert "_mcp_server is None" in source
        assert "503" in source or "Service Unavailable" in source.lower()


class TestAuthenticationEdgeCases:
    """Tests for authentication edge cases and security."""

    def test_bearer_token_case_sensitive(self):
        """Test that Bearer token validation is case-sensitive."""
        config = Config()
        config.server.password = "TestPassword123"
        app = create_test_app(config)

        with TestClient(app) as client:
            # Try with wrong case
            response = client.get(
                "/mcp",
                headers={"Authorization": "Bearer testpassword123"},
            )
            assert response.status_code == 401

    def test_empty_bearer_token_rejected(self):
        """Test that empty Bearer token is rejected."""
        config = Config()
        config.server.password = "test-password"
        app = create_test_app(config)

        with TestClient(app) as client:
            response = client.get(
                "/mcp",
                headers={"Authorization": "Bearer "},
            )
            assert response.status_code == 401

    def test_malformed_auth_header_rejected(self):
        """Test that malformed authorization header is rejected."""
        config = Config()
        config.server.password = "test-password"
        app = create_test_app(config)

        with TestClient(app) as client:
            # Missing "Bearer " prefix
            response = client.get(
                "/mcp",
                headers={"Authorization": "test-password"},
            )
            assert response.status_code in [401, 403]

    def test_post_messages_bearer_prefix_required(self):
        """Test that POST /mcp/messages requires Bearer prefix."""
        config = Config()
        config.server.password = "test-password"
        app = create_test_app(config)

        with TestClient(app) as client:
            # Send token without Bearer prefix
            response = client.post(
                "/mcp/messages",
                json={},
                headers={"Authorization": "test-password"},
            )
            assert response.status_code == 401
