# Configuration Guide

AI Gaming Agent uses a JSON configuration file for server settings.

## Config File Location

The configuration file is located at:
- **Linux/macOS:** `~/.gaming-agent/config.json`
- **Windows:** `%USERPROFILE%\.gaming-agent\config.json`

## Creating Configuration

### Using CLI

```bash
# Create default config
gaming-agent init

# Create with password
gaming-agent init --password your-secret-password

# Create with custom port
gaming-agent init --port 9000 --password secret

# Force overwrite existing
gaming-agent init --force --password new-password
```

### Manual Creation

Create the file manually:

```bash
mkdir -p ~/.gaming-agent
cat > ~/.gaming-agent/config.json << 'EOF'
{
  "server": {
    "host": "0.0.0.0",
    "port": 8765,
    "password": "your-secure-password-here"
  },
  "vlm": {
    "enabled": false,
    "provider": "ollama",
    "model": "qwen2.5-vl:3b",
    "endpoint": "http://localhost:11434"
  },
  "security": {
    "allowed_paths": [],
    "blocked_commands": ["rm -rf", "format", "del /f", "mkfs"],
    "max_command_timeout": 30
  },
  "features": {
    "screenshot": true,
    "file_access": true,
    "command_execution": true,
    "mouse_control": true,
    "keyboard_control": true
  }
}
EOF
```

## Configuration Sections

### Server Configuration

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8765,
    "password": "your-secure-password-here"
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `host` | string | `"0.0.0.0"` | IP address to bind to. Use `0.0.0.0` for all interfaces |
| `port` | int | `8765` | Port number for MCP server |
| `password` | string | `""` | Authentication password (required for remote access) |

### VLM Configuration (Optional)

```json
{
  "vlm": {
    "enabled": false,
    "provider": "ollama",
    "model": "qwen2.5-vl:3b",
    "endpoint": "http://localhost:11434"
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `false` | Enable local Vision Language Model |
| `provider` | string | `"ollama"` | VLM provider (`ollama`) |
| `model` | string | `"qwen2.5-vl:3b"` | Model name/tag |
| `endpoint` | string | `"http://localhost:11434"` | API endpoint |

**Recommended VLM Models:**

| Model | Size | VRAM | Speed | Quality |
|-------|------|------|-------|---------|
| `moondream2:latest` | 2B | 4GB | Fast | Good |
| `qwen2.5-vl:3b` | 3B | 6GB | Medium | Better |
| `qwen2.5-vl:7b` | 7B | 12GB | Slow | Best |

### Security Configuration

```json
{
  "security": {
    "allowed_paths": ["/home/user/games", "C:\\Games"],
    "blocked_commands": ["rm -rf", "format", "del /f", "mkfs"],
    "max_command_timeout": 30
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `allowed_paths` | list[str] | `[]` | Directories for file access. Empty = no restrictions |
| `blocked_commands` | list[str] | See below | Commands blocked from execution |
| `max_command_timeout` | int | `30` | Max seconds for command execution |

**Default Blocked Commands:**
- `rm -rf` - Recursive delete (Linux)
- `format` - Format disk (Windows)
- `del /f` - Force delete (Windows)
- `mkfs` - Make filesystem (Linux)

### Features Configuration

```json
{
  "features": {
    "screenshot": true,
    "file_access": true,
    "command_execution": true,
    "mouse_control": true,
    "keyboard_control": true
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `screenshot` | bool | `true` | Enable screen capture tools |
| `file_access` | bool | `true` | Enable file read/write tools |
| `command_execution` | bool | `true` | Enable shell command execution |
| `mouse_control` | bool | `true` | Enable mouse movement/clicks |
| `keyboard_control` | bool | `true` | Enable keyboard input |

## Environment Variables

Configuration can be overridden via environment variables:

```bash
# Server settings
export GAMING_AGENT_SERVER__HOST=127.0.0.1
export GAMING_AGENT_SERVER__PORT=9000
export GAMING_AGENT_SERVER__PASSWORD=secret

# VLM settings
export GAMING_AGENT_VLM__ENABLED=true
export GAMING_AGENT_VLM__MODEL=qwen2.5-vl:7b
```

Note: Use double underscore `__` for nested keys.

## CLI Override

Command-line arguments override both config file and environment variables:

```bash
gaming-agent serve --host 127.0.0.1 --port 9000 --password override-password
```

## Viewing Current Config

```bash
gaming-agent config
```

This outputs the current configuration as JSON.

## Example Configurations

### Development (Local Only)

```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8765,
    "password": ""
  },
  "security": {
    "allowed_paths": [],
    "blocked_commands": [],
    "max_command_timeout": 60
  },
  "features": {
    "screenshot": true,
    "file_access": true,
    "command_execution": true,
    "mouse_control": true,
    "keyboard_control": true
  }
}
```

### Production (Gaming PC)

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8765,
    "password": "strong-random-password-here"
  },
  "vlm": {
    "enabled": true,
    "provider": "ollama",
    "model": "qwen2.5-vl:3b",
    "endpoint": "http://localhost:11434"
  },
  "security": {
    "allowed_paths": [
      "C:\\Games",
      "C:\\Users\\Player\\Documents\\SaveGames"
    ],
    "blocked_commands": [
      "rm -rf", "format", "del /f", "mkfs",
      "shutdown", "reboot", "taskkill"
    ],
    "max_command_timeout": 30
  },
  "features": {
    "screenshot": true,
    "file_access": true,
    "command_execution": false,
    "mouse_control": true,
    "keyboard_control": true
  }
}
```

### Minimal (Screen Capture Only)

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8765,
    "password": "viewer-password"
  },
  "features": {
    "screenshot": true,
    "file_access": false,
    "command_execution": false,
    "mouse_control": false,
    "keyboard_control": false
  }
}
```

## Claude Desktop Configuration

To connect Claude Desktop to your gaming PC, add this to:
- **Linux:** `~/.config/claude/claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "gaming-pc-1": {
      "transport": "sse",
      "url": "http://192.168.1.100:8765/mcp",
      "headers": {
        "Authorization": "Bearer your-password-here"
      }
    },
    "gaming-pc-2": {
      "transport": "sse",
      "url": "http://192.168.1.101:8765/mcp",
      "headers": {
        "Authorization": "Bearer different-password"
      }
    }
  }
}
```
