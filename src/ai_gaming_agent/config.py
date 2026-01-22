"""Configuration management for AI Gaming Agent."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = "0.0.0.0"
    port: int = 8765
    password: str = ""


class VLMConfig(BaseModel):
    """Vision Language Model configuration."""

    enabled: bool = False
    provider: str = "ollama"
    model: str = "qwen2.5-vl:3b"
    endpoint: str = "http://localhost:11434"


class SecurityConfig(BaseModel):
    """Security configuration."""

    allowed_paths: list[str] = Field(default_factory=list)
    blocked_commands: list[str] = Field(default_factory=lambda: ["rm -rf", "format", "del /f", "mkfs"])
    max_command_timeout: int = 30


class FeaturesConfig(BaseModel):
    """Feature toggles."""

    screenshot: bool = True
    file_access: bool = True
    command_execution: bool = True
    mouse_control: bool = True
    keyboard_control: bool = True


class Config(BaseSettings):
    """Main configuration class."""

    model_config = SettingsConfigDict(
        env_prefix="GAMING_AGENT_",
        env_nested_delimiter="__",
    )

    server: ServerConfig = Field(default_factory=ServerConfig)
    vlm: VLMConfig = Field(default_factory=VLMConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)

    @classmethod
    def load(cls, config_path: Path | None = None) -> Config:
        """Load configuration from file or defaults."""
        if config_path is None:
            config_path = Path.home() / ".gaming-agent" / "config.json"

        if config_path.exists():
            with open(config_path) as f:
                data = json.load(f)
            return cls.model_validate(data)

        return cls()

    def save(self, config_path: Path | None = None) -> None:
        """Save configuration to file."""
        if config_path is None:
            config_path = Path.home() / ".gaming-agent" / "config.json"

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(self.model_dump(), f, indent=2)


def get_config() -> Config:
    """Get the current configuration."""
    return Config.load()
