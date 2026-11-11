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

### File Permissions

The password is stored as plaintext in the JSON file, not encrypted. On POSIX
systems (Linux/macOS), saving configuration creates new config directories with
mode `0700` (owner-only access) and the config file with mode `0600` (owner-only
read/write), even with a permissive umask. Saving also tightens an existing
config file to `0600` before writing and the app-owned default `~/.gaming-agent`
directory to `0700`. Existing custom parent directories are left unchanged;
secure those directories yourself.

These mode-bit guarantees do not enforce equivalent Windows ACL protection.
On Windows, restrict access to the configuration directory and file using
Windows security settings.

### Manual Creation

On POSIX systems, create the file with restrictive permissions before writing
the password. This also tightens an existing directory and file. The subshell
keeps the restrictive umask local, and `set -e` stops before writing if a
permission-setting command fails:

```bash
(
set -e
umask 077
mkdir -p ~/.gaming-agent
chmod 700 ~/.gaming-agent
touch ~/.gaming-agent/config.json
chmod 600 ~/.gaming-agent/config.json
cat > ~/.gaming-agent/config.json << 'EOF'
{
  "server": {
    "host": "0.0.0.0",
    "port": 8765,
    "password": "your-secure-password-here",
    "allowed_hosts": ["localhost:*", "127.0.0.1:*", "[::1]:*"],
    "allowed_origins": ["http://localhost:*", "http://127.0.0.1:*", "http://[::1]:*"]
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
)
```

## Configuration Sections

### Server Configuration

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8765,
    "password": "your-secure-password-here",
    "allowed_hosts": ["localhost:*", "127.0.0.1:*", "[::1]:*"],
    "allowed_origins": ["http://localhost:*", "http://127.0.0.1:*", "http://[::1]:*"]
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `host` | string | `"0.0.0.0"` | IP address to bind to. Use `0.0.0.0` for all interfaces |
| `port` | int | `8765` | Port number for MCP server |
| `password` | string | `""` | Authentication password (required for remote access) |
| `allowed_hosts` | list[str] | `["localhost:*", "127.0.0.1:*", "[::1]:*"]` | `Host` headers accepted by the MCP endpoints. Loopback only by default |
| `allowed_origins` | list[str] | `["http://localhost:*", "http://127.0.0.1:*", "http://[::1]:*"]` | `Origin` headers accepted by the MCP endpoints. Loopback only by default |

**Host and Origin rules**

- A request whose `Host` header is not in `allowed_hosts` is refused with `421`
  ("Invalid Host header") and never reaches the SSE transport.
- A request whose `Origin` header is present and not in `allowed_origins` is
  refused with `403` ("Invalid Origin header"). A request without an `Origin`
  header is allowed.
- An entry matches either exactly (`192.168.1.100:8765`) or, when it ends in
  `:*`, any `host:port` form of that host (`192.168.1.100:*` matches
  `192.168.1.100:8765`).
- The wildcard covers `host:port` forms only: a value without a port
  (`192.168.1.100`) is refused with `421` even when `192.168.1.100:*` is
  listed, so a bare host needs its own exact entry.
- The bearer token is checked first: a missing or wrong token is refused with
  `401` (`403` when no password is configured) before any Host or Origin check.
- `GET /health` is neither authenticated nor Host-validated.
- A remote PC must therefore list its own address in `allowed_hosts`, for
  example `"192.168.1.100:8765"`. Without it every `/mcp` request from that
  client is refused with `421`.

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

# Host/Origin allow-lists (JSON array values)
export GAMING_AGENT_SERVER__ALLOWED_HOSTS='["localhost:*","192.168.1.100:8765"]'
export GAMING_AGENT_SERVER__ALLOWED_ORIGINS='["http://localhost:*","http://192.168.1.100:8765"]'

# VLM settings
export GAMING_AGENT_VLM__ENABLED=true
export GAMING_AGENT_VLM__MODEL=qwen2.5-vl:7b
```

Note: Use double underscore `__` for nested keys. `allowed_hosts` and
`allowed_origins` take a JSON array as their value - a bare comma-separated
string is rejected.

Note: a value written in `~/.gaming-agent/config.json` wins over the
environment for that setting, and the environment supplies every setting the
config file does not define. A config file's `server.allowed_hosts` /
`server.allowed_origins` win and are not merged with the environment; the
environment overrides fill in the allow-lists only while the config file does
not set them.

## CLI Override

Command-line arguments override both config file and environment variables:

```bash
gaming-agent serve --host 127.0.0.1 --port 9000 --password override-password
```

## Viewing Current Config

```bash
gaming-agent config
```

This outputs valid JSON with every nonempty `server.password` replaced by the
fixed marker `[REDACTED]`, including one-character passwords. An empty password
remains `""`, and other settings are unchanged. Displaying configuration does
not change the loaded settings or rewrite the saved file; masking is only for
display and does not change the authentication password.

To explicitly reveal the original password in a private terminal:

```bash
gaming-agent config --show-password
```

**Warning:** `--show-password` exposes the plaintext password in terminal
output, scrollback, and any captured logs. Do not use it in shared terminals,
CI logs, screen recordings, or output you intend to share. Masked output is
for inspection, not a replacement configuration file.

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
    "password": "strong-random-password-here",
    "allowed_hosts": ["localhost:*", "127.0.0.1:*", "[::1]:*", "192.168.1.100:8765"],
    "allowed_origins": ["http://localhost:*", "http://127.0.0.1:*", "http://[::1]:*"]
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
    "password": "viewer-password",
    "allowed_hosts": ["localhost:*", "127.0.0.1:*", "[::1]:*", "192.168.1.100:8765"],
    "allowed_origins": ["http://localhost:*", "http://127.0.0.1:*", "http://[::1]:*"]
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

`claude_desktop_config.json` only holds local stdio servers (`command` /
`args` / `env`). It does not accept `"transport": "sse"` / `url` / `headers`
entries, and the server here speaks plain-HTTP SSE with a static Bearer token.
To reach it from Claude Desktop, run the
[`mcp-remote`](https://github.com/punkpeye/mcp-remote) bridge as a stdio
server (needs Node.js 18+). Edit:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "gaming-pc-1": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://YOUR-PC-IP:8765/mcp",
        "--transport",
        "sse-only",
        "--allow-http",
        "--header",
        "Authorization:${AUTH_HEADER}"
      ],
      "env": {
        "AUTH_HEADER": "Bearer your-secret-password"
      }
    },
    "gaming-pc-2": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://YOUR-OTHER-PC-IP:8765/mcp",
        "--transport",
        "sse-only",
        "--allow-http",
        "--header",
        "Authorization:${AUTH_HEADER}"
      ],
      "env": {
        "AUTH_HEADER": "Bearer your-other-secret-password"
      }
    }
  }
}
```

- `--transport sse-only` selects the legacy HTTP+SSE protocol this server
  speaks.
- `--allow-http` is required because the server is plain HTTP; use it only on
  a trusted private network or VPN.
- The header value goes through `env` (`Authorization:${AUTH_HEADER}`, no
  space after the colon) to avoid a known argument-splitting bug with spaces
  in `args` on Windows.

This bridge config follows the mcp-remote and Claude documentation; it has not
been exercised against a live Claude client, so no client versions are claimed.

Claude Desktop's **Settings > Connectors > Add custom connector** is not an
alternative here: connectors need a public HTTPS URL with OAuth (or no auth),
not a LAN `http://` address with a static Bearer header.

## Claude Code

Claude Code connects to the `/mcp` SSE endpoint directly. `--transport` must
come before the server name:

```bash
claude mcp add --transport sse gaming-pc-1 http://YOUR-PC-IP:8765/mcp --header "Authorization: Bearer your-secret-password"
claude mcp list
```

SSE is flagged as deprecated in the Claude Code docs but is still supported.

Each PC must list its own address in its own `server.allowed_hosts` (and in
`server.allowed_origins` if the client sends an `Origin` header). A remote PC
that does not list itself refuses every `/mcp` request with `421 Invalid Host
header` - the request never reaches the SSE transport, even with a valid
bearer token. The matching config for `192.168.1.100` looks like this:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8765,
    "password": "your-secure-password-here",
    "allowed_hosts": ["localhost:*", "127.0.0.1:*", "[::1]:*", "192.168.1.100:8765"],
    "allowed_origins": ["http://localhost:*", "http://127.0.0.1:*", "http://[::1]:*"]
  }
}
```
