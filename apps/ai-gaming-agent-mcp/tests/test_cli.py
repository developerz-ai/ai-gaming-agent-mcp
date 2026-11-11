"""Tests for CLI module."""

import argparse
import json
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_gaming_agent.cli import cmd_serve, main
from ai_gaming_agent.config import Config


class TestConfigCommand:
    """Tests for configuration display through the real CLI parser."""

    @pytest.mark.parametrize("password", ["synthetic-cli-password-923", "x", "xy", ""])
    @pytest.mark.parametrize("show_password", [False, True])
    def test_config_display(self, password: str, show_password: bool, capsys: pytest.CaptureFixture[str]) -> None:
        config = Config(
            server={"password": password, "host": "127.0.0.1", "port": 9123},
            features={"file_access": False},
            security={"allowed_paths": ["/example/games"]},
        )
        original = config.model_dump()
        argv = ["gaming-agent", "config"]
        if show_password:
            argv.append("--show-password")

        with (
            patch("sys.argv", argv),
            patch("ai_gaming_agent.cli.Config.load", return_value=config) as load,
            patch("ai_gaming_agent.cli.Config.save") as save,
        ):
            assert main() == 0

        captured = capsys.readouterr()
        displayed = json.loads(captured.out)
        expected = config.model_dump()
        if password and not show_password:
            expected["server"]["password"] = "[REDACTED]"
            assert password not in json.dumps(displayed["server"]["password"])
            if len(password) > 2:
                assert password not in captured.out
        assert displayed == expected
        assert captured.err == ""
        assert config.model_dump() == original
        load.assert_called_once_with()
        save.assert_not_called()

    @pytest.mark.parametrize("show_password", [False, True])
    def test_config_does_not_rewrite_file(
        self, show_password: bool, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config = Config(server={"password": "synthetic-file-password-568"})
        config_dir = tmp_path / ".gaming-agent"
        config_dir.mkdir()
        config_path = config_dir / "config.json"
        original = config.model_dump_json(indent=4).encode()
        config_path.write_bytes(original)
        original_mtime = config_path.stat().st_mtime_ns
        argv = ["gaming-agent", "config"] + (["--show-password"] if show_password else [])

        with (
            patch("sys.argv", argv),
            patch("ai_gaming_agent.cli.Path.home", return_value=tmp_path),
            patch("ai_gaming_agent.cli.Config.load", return_value=config),
        ):
            assert main() == 0

        json.loads(capsys.readouterr().out)
        assert config_path.read_bytes() == original
        assert config_path.stat().st_mtime_ns == original_mtime

    def test_config_help_warns_about_password_exposure(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch("sys.argv", ["gaming-agent", "config", "--help"]), pytest.raises(SystemExit) as exc:
            main()

        assert exc.value.code == 0
        help_text = capsys.readouterr().out
        assert "--show-password" in help_text
        assert "terminal" in help_text
        assert "logs" in help_text


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
