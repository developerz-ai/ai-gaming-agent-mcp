"""Tests for configuration module."""

import tempfile
from pathlib import Path

from ai_gaming_agent.config import Config, SecurityConfig, ServerConfig


def test_default_config():
    """Test default configuration values."""
    config = Config()
    assert config.server.host == "0.0.0.0"
    assert config.server.port == 8765
    assert config.server.password == ""
    assert config.vlm.enabled is False
    assert config.features.screenshot is True


def test_server_config():
    """Test server configuration."""
    server = ServerConfig(host="127.0.0.1", port=9000, password="secret")
    assert server.host == "127.0.0.1"
    assert server.port == 9000
    assert server.password == "secret"


def test_security_config_defaults():
    """Test security configuration defaults."""
    security = SecurityConfig()
    assert "rm -rf" in security.blocked_commands
    assert "format" in security.blocked_commands
    assert security.max_command_timeout == 30


def test_config_save_and_load():
    """Test saving and loading configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"

        # Create and save config
        config = Config()
        config.server.password = "test-password"
        config.server.port = 9999
        config.save(config_path)

        # Load and verify
        loaded = Config.load(config_path)
        assert loaded.server.password == "test-password"
        assert loaded.server.port == 9999


def test_config_load_nonexistent():
    """Test loading config when file doesn't exist."""
    config = Config.load(Path("/nonexistent/path/config.json"))
    # Should return defaults
    assert config.server.port == 8765
