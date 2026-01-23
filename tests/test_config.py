"""Tests for configuration module."""

import tempfile
from pathlib import Path

import pytest

from ai_gaming_agent.config import Config, SecurityConfig, ServerConfig, VLMConfig


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


class TestVLMConfig:
    """Tests for VLM configuration validation."""

    def test_vlm_disabled_no_validation(self):
        """Test that VLM validation is skipped when disabled."""
        # This should not raise even with invalid values
        vlm = VLMConfig(
            enabled=False,
            provider="invalid_provider",
            model="",
            endpoint="not_a_url",
        )
        assert vlm.enabled is False

    def test_vlm_enabled_valid_config(self):
        """Test that valid VLM config is accepted."""
        vlm = VLMConfig(
            enabled=True,
            provider="ollama",
            model="qwen2.5-vl:3b",
            endpoint="http://localhost:11434",
        )
        assert vlm.enabled is True
        assert vlm.provider == "ollama"
        assert vlm.model == "qwen2.5-vl:3b"

    def test_vlm_enabled_https_endpoint(self):
        """Test that https endpoints are accepted."""
        vlm = VLMConfig(
            enabled=True,
            provider="ollama",
            model="qwen2.5-vl:3b",
            endpoint="https://remote-ollama.example.com:11434",
        )
        assert vlm.endpoint == "https://remote-ollama.example.com:11434"

    def test_vlm_enabled_unsupported_provider(self):
        """Test that unsupported provider raises error when VLM is enabled."""
        with pytest.raises(ValueError, match="Unsupported VLM provider"):
            VLMConfig(
                enabled=True,
                provider="unsupported_provider",
                model="qwen2.5-vl:3b",
                endpoint="http://localhost:11434",
            )

    def test_vlm_enabled_empty_model(self):
        """Test that empty model name raises error when VLM is enabled."""
        with pytest.raises(ValueError, match="model name cannot be empty"):
            VLMConfig(
                enabled=True,
                provider="ollama",
                model="",
                endpoint="http://localhost:11434",
            )

    def test_vlm_enabled_empty_endpoint(self):
        """Test that empty endpoint raises error when VLM is enabled."""
        with pytest.raises(ValueError, match="endpoint URL cannot be empty"):
            VLMConfig(
                enabled=True,
                provider="ollama",
                model="qwen2.5-vl:3b",
                endpoint="",
            )

    def test_vlm_enabled_invalid_endpoint_format(self):
        """Test that endpoint without http(s) prefix raises error."""
        with pytest.raises(ValueError, match="must start with http"):
            VLMConfig(
                enabled=True,
                provider="ollama",
                model="qwen2.5-vl:3b",
                endpoint="localhost:11434",
            )

    def test_vlm_enabled_ftp_endpoint_rejected(self):
        """Test that non-http(s) protocols are rejected."""
        with pytest.raises(ValueError, match="must start with http"):
            VLMConfig(
                enabled=True,
                provider="ollama",
                model="qwen2.5-vl:3b",
                endpoint="ftp://localhost:11434",
            )

    def test_vlm_default_config(self):
        """Test VLM default configuration."""
        vlm = VLMConfig()
        assert vlm.enabled is False
        assert vlm.provider == "ollama"
        assert vlm.model == "qwen2.5-vl:3b"
        assert vlm.endpoint == "http://localhost:11434"

    def test_config_with_enabled_vlm(self):
        """Test full Config object with enabled VLM."""
        config = Config(
            vlm=VLMConfig(
                enabled=True,
                provider="ollama",
                model="qwen2.5-vl:3b",
                endpoint="http://localhost:11434",
            )
        )
        assert config.vlm.enabled is True

    def test_config_vlm_validation_in_full_config(self):
        """Test that VLM validation works within full Config object."""
        with pytest.raises(ValueError, match="Unsupported VLM provider"):
            Config(
                vlm=VLMConfig(
                    enabled=True,
                    provider="invalid",
                    model="test",
                    endpoint="http://localhost:11434",
                )
            )
