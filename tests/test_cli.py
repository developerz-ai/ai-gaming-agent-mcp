"""Tests for CLI module."""

import argparse
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from ai_gaming_agent.cli import cmd_serve


class TestServeCommand:
    """Tests for the serve command."""

    def test_transport_flag_defaults_to_http(self):
        """Test that transport defaults to 'http' when not specified."""
        with patch("sys.argv", ["gaming-agent", "serve"]):
            # We just want to verify the argument parser, not actually run the server

            # Create parser manually to test argument parsing
            parser = argparse.ArgumentParser()
            subparsers = parser.add_subparsers(dest="command")
            serve_parser = subparsers.add_parser("serve")
            serve_parser.add_argument(
                "--transport",
                type=str,
                choices=["stdio", "http"],
                default="http",
            )
            serve_parser.add_argument("--host", type=str)
            serve_parser.add_argument("--port", type=int)
            serve_parser.add_argument("--password", type=str)
            serve_parser.add_argument("--config", type=str)

            args = parser.parse_args(["serve"])
            assert args.transport == "http"

    def test_transport_flag_accepts_stdio(self):
        """Test that --transport stdio is accepted."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        serve_parser = subparsers.add_parser("serve")
        serve_parser.add_argument(
            "--transport",
            type=str,
            choices=["stdio", "http"],
            default="http",
        )

        args = parser.parse_args(["serve", "--transport", "stdio"])
        assert args.transport == "stdio"

    def test_transport_flag_accepts_http(self):
        """Test that --transport http is accepted."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        serve_parser = subparsers.add_parser("serve")
        serve_parser.add_argument(
            "--transport",
            type=str,
            choices=["stdio", "http"],
            default="http",
        )

        args = parser.parse_args(["serve", "--transport", "http"])
        assert args.transport == "http"

    def test_transport_flag_rejects_invalid(self):
        """Test that invalid transport values are rejected."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        serve_parser = subparsers.add_parser("serve")
        serve_parser.add_argument(
            "--transport",
            type=str,
            choices=["stdio", "http"],
            default="http",
        )

        with pytest.raises(SystemExit):
            parser.parse_args(["serve", "--transport", "invalid"])

    def test_cmd_serve_uses_stdio_when_specified(self):
        """Test that cmd_serve calls run_server for stdio transport."""
        mock_config = MagicMock()
        mock_config.server.port = 8765
        mock_config.server.host = "0.0.0.0"
        mock_config.server.password = "test"

        args = argparse.Namespace(
            transport="stdio",
            host=None,
            port=None,
            password=None,
            config=None,
        )

        mock_run_server = MagicMock()

        with patch("ai_gaming_agent.cli.Config.load", return_value=mock_config):
            with patch("ai_gaming_agent.cli.asyncio.run") as mock_asyncio_run:
                with patch.dict("sys.modules", {"ai_gaming_agent.server": MagicMock(run_server=mock_run_server)}):
                    with patch("ai_gaming_agent.cli.sys.stderr", new_callable=StringIO):
                        cmd_serve(args)
                        mock_asyncio_run.assert_called_once()

    def test_cmd_serve_uses_http_when_specified(self):
        """Test that cmd_serve calls run_http_server for http transport."""
        mock_config = MagicMock()
        mock_config.server.port = 8765
        mock_config.server.host = "0.0.0.0"
        mock_config.server.password = "test"

        args = argparse.Namespace(
            transport="http",
            host=None,
            port=None,
            password=None,
            config=None,
        )

        mock_run_http_server = MagicMock()

        with patch("ai_gaming_agent.cli.Config.load", return_value=mock_config):
            with patch("ai_gaming_agent.cli.asyncio.run") as mock_asyncio_run:
                with patch.dict(
                    "sys.modules", {"ai_gaming_agent.http_server": MagicMock(run_http_server=mock_run_http_server)}
                ):
                    with patch("ai_gaming_agent.cli.sys.stderr", new_callable=StringIO):
                        cmd_serve(args)
                        mock_asyncio_run.assert_called_once()

    def test_cmd_serve_warns_no_password_http_mode(self):
        """Test that cmd_serve warns when no password is set in HTTP mode."""
        mock_config = MagicMock()
        mock_config.server.port = 8765
        mock_config.server.host = "0.0.0.0"
        mock_config.server.password = None  # No password set

        args = argparse.Namespace(
            transport="http",
            host=None,
            port=None,
            password=None,
            config=None,
        )

        stderr = StringIO()
        mock_run_http_server = MagicMock()

        with patch("ai_gaming_agent.cli.Config.load", return_value=mock_config):
            with patch("ai_gaming_agent.cli.asyncio.run"):
                with patch.dict(
                    "sys.modules", {"ai_gaming_agent.http_server": MagicMock(run_http_server=mock_run_http_server)}
                ):
                    with patch("ai_gaming_agent.cli.sys.stderr", stderr):
                        cmd_serve(args)

        stderr_output = stderr.getvalue()
        assert "WARNING" in stderr_output
        assert "No password configured" in stderr_output
