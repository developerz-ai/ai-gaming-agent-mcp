"""Tests for configuration module."""

import json
import os
import stat
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


def test_server_transport_allow_list_defaults():
    """Test that the transport allow-list defaults to loopback only."""
    server = ServerConfig()

    assert server.allowed_hosts == ["localhost:*", "127.0.0.1:*", "[::1]:*"]
    assert server.allowed_origins == ["http://localhost:*", "http://127.0.0.1:*", "http://[::1]:*"]

    # No default entry may name every host or every origin.
    assert [entry.removesuffix(":*") for entry in server.allowed_hosts] == ["localhost", "127.0.0.1", "[::1]"]
    assert [entry.removesuffix(":*") for entry in server.allowed_origins] == [
        "http://localhost",
        "http://127.0.0.1",
        "http://[::1]",
    ]


def test_allowed_hosts_and_origins_env_overrides(monkeypatch):
    """Test that the allow-list can be widened through the environment."""
    monkeypatch.setenv(
        "GAMING_AGENT_SERVER__ALLOWED_HOSTS",
        '["localhost:*", "192.168.1.100:8765"]',
    )
    monkeypatch.setenv(
        "GAMING_AGENT_SERVER__ALLOWED_ORIGINS",
        '["http://localhost:*", "http://192.168.1.100:8765"]',
    )

    config = Config()

    assert config.server.allowed_hosts == ["localhost:*", "192.168.1.100:8765"]
    assert config.server.allowed_origins == ["http://localhost:*", "http://192.168.1.100:8765"]


def test_allow_list_is_saved_to_config_file(monkeypatch):
    """Test that the allow-list lands in the saved configuration file."""
    monkeypatch.delenv("GAMING_AGENT_SERVER__ALLOWED_HOSTS", raising=False)
    monkeypatch.delenv("GAMING_AGENT_SERVER__ALLOWED_ORIGINS", raising=False)

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        Config().save(config_path)
        data = json.loads(config_path.read_text())

    assert data["server"]["allowed_hosts"] == ["localhost:*", "127.0.0.1:*", "[::1]:*"]
    assert data["server"]["allowed_origins"] == ["http://localhost:*", "http://127.0.0.1:*", "http://[::1]:*"]


def test_config_file_allow_list_wins_over_environment(monkeypatch):
    """Test that a saved config file's allow-list wins over the environment."""
    monkeypatch.setenv("GAMING_AGENT_SERVER__ALLOWED_HOSTS", '["env-host:*"]')
    monkeypatch.setenv("GAMING_AGENT_SERVER__ALLOWED_ORIGINS", '["http://env-host:*"]')

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"

        config = Config()
        config.server.allowed_hosts = ["file-host:*"]
        config.server.allowed_origins = ["http://file-host:*"]
        config.save(config_path)

        loaded = Config.load(config_path)

    assert loaded.server.allowed_hosts == ["file-host:*"]
    assert loaded.server.allowed_origins == ["http://file-host:*"]


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


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits are not Windows ACLs")
@pytest.mark.parametrize("use_default_path", [True, False], ids=["default", "custom"])
def test_config_save_creates_private_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, use_default_path: bool):
    """New config directories and files are private before any JSON is written."""
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    config_path = (
        tmp_path / ".gaming-agent" / "config.json"
        if use_default_path
        else tmp_path / "custom" / "nested" / "config.json"
    )
    config = Config(server=ServerConfig(password="test-password", port=9999))
    original_dump = json.dump

    def checked_dump(data: dict, stream, **kwargs) -> None:
        assert stat.S_IMODE(config_path.parent.stat().st_mode) == 0o700
        assert stat.S_IMODE(config_path.stat().st_mode) == 0o600
        original_dump(data, stream, **kwargs)

    monkeypatch.setattr(json, "dump", checked_dump)
    previous_umask = os.umask(0)
    try:
        config.save(None if use_default_path else config_path)
    finally:
        os.umask(previous_umask)

    assert stat.S_IMODE(config_path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(config_path.stat().st_mode) == 0o600
    if not use_default_path:
        assert stat.S_IMODE((tmp_path / "custom").stat().st_mode) == 0o700
    assert json.loads(config_path.read_text()) == config.model_dump()
    assert Config.load(None if use_default_path else config_path).server.password == "test-password"


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits are not Windows ACLs")
@pytest.mark.parametrize("use_default_path", [True, False], ids=["default", "custom"])
def test_config_save_tightens_existing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, use_default_path: bool):
    """Tighten loose files before writing, without chmod of unrelated existing parents."""
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    config_dir = tmp_path / (".gaming-agent" if use_default_path else "custom")
    config_dir.mkdir()
    config_dir.chmod(0o755)
    config_path = config_dir / "config.json"
    config_path.write_text("old contents that must be fully replaced" * 100)
    config_path.chmod(0o644)
    config = Config(server=ServerConfig(password="replacement-password", port=9999))
    original_dump = json.dump

    def checked_dump(data: dict, stream, **kwargs) -> None:
        assert stat.S_IMODE(config_path.stat().st_mode) == 0o600
        original_dump(data, stream, **kwargs)

    monkeypatch.setattr(json, "dump", checked_dump)
    previous_umask = os.umask(0)
    try:
        config.save(None if use_default_path else config_path)
    finally:
        os.umask(previous_umask)

    assert stat.S_IMODE(config_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(config_dir.stat().st_mode) == (0o700 if use_default_path else 0o755)
    assert json.loads(config_path.read_text()) == config.model_dump()
    loaded = Config.load(None if use_default_path else config_path)
    assert loaded.server.password == "replacement-password"
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
