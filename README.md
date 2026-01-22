# AI Gaming Agent MCP Server

MCP (Model Context Protocol) server that enables AI agents like Claude to remotely control gaming PCs for automated gameplay.

```
Master Claude (Orchestrator)
    |
    | MCP Protocol (JSON-RPC over HTTP/SSE)
    |
    +---> PC #1 (MCP Server :8765) --> PyAutoGUI + Optional VLM
    +---> PC #2 (MCP Server :8765) --> PyAutoGUI + Optional VLM
    +---> PC #N (MCP Server :8765) --> PyAutoGUI + Optional VLM
```

## Features

- **21 MCP Tools**: Screen capture, mouse/keyboard control, file operations, system commands
- **Multi-Monitor Support**: Target specific monitors for screenshots and actions
- **Optional Local VLM**: Use Ollama for fast local screen analysis
- **Security-First**: Password auth, path restrictions, command blocklist, audit logging
- **Cross-Platform**: Windows, Linux, macOS

## Quick Start

### Installation

```bash
pip install ai-gaming-agent
```

Or install from source:

```bash
git clone https://github.com/developerz-ai/ai-gaming-agent-mcp.git
cd ai-gaming-agent-mcp
pip install -e .
```

### Start the Server

```bash
gaming-agent serve --port 8765 --password your-secret-password
```

### Connect from Claude Desktop

Add to your Claude Desktop config (`~/.config/claude/claude_desktop_config.json` on Linux):

```json
{
  "mcpServers": {
    "gaming-pc": {
      "transport": "sse",
      "url": "http://YOUR-PC-IP:8765/mcp",
      "headers": {
        "Authorization": "Bearer your-secret-password"
      }
    }
  }
}
```

## Available Tools

### Screen Tools
| Tool | Description |
|------|-------------|
| `screenshot` | Capture current screen (returns base64 PNG) |
| `get_screen_size` | Get screen dimensions |
| `analyze_screen` | Use local VLM to analyze screen content |

### Mouse Tools
| Tool | Description |
|------|-------------|
| `click` | Click at coordinates |
| `double_click` | Double-click at coordinates |
| `move_to` | Move mouse cursor |
| `drag_to` | Drag from current position |
| `scroll` | Scroll mouse wheel |
| `get_mouse_position` | Get current cursor location |

### Keyboard Tools
| Tool | Description |
|------|-------------|
| `type_text` | Type a string of text |
| `press_key` | Press a single key |
| `hotkey` | Press key combination |

### File Tools
| Tool | Description |
|------|-------------|
| `read_file` | Read file contents |
| `write_file` | Write content to file |
| `list_files` | List directory contents |
| `upload_file` | Upload file to PC |
| `download_file` | Download file from PC |

### System Tools
| Tool | Description |
|------|-------------|
| `execute_command` | Run shell command |
| `get_system_info` | Get CPU/RAM/GPU usage |
| `list_windows` | List open windows |
| `focus_window` | Bring window to foreground |

## Configuration

Create `~/.gaming-agent/config.json`:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8765,
    "password": "your-secure-password"
  },
  "vlm": {
    "enabled": false,
    "provider": "ollama",
    "model": "qwen2.5-vl:3b"
  },
  "security": {
    "allowed_paths": ["/home/user/games", "C:\\Games"],
    "blocked_commands": ["rm -rf", "format", "del /f"],
    "max_command_timeout": 30
  }
}
```

## Deployment Options

### Option A: Claude Does All Vision (Simplest)
- Claude analyzes all screenshots
- Gaming PCs are simple executors
- No GPU needed on gaming PCs

### Option B: Hybrid with Local VLM (Recommended)
- Claude for high-level decisions
- Local VLM (Qwen, Moondream) for fast visual processing
- Best balance of speed and intelligence

### Option C: Full Local (Privacy)
- Local orchestrator (e.g., Qwen3-72B)
- No cloud APIs
- Requires powerful hardware

## Security

- Always use strong, unique passwords
- Limit file access to game directories only
- Use a VPN if accessing over internet
- Enable TLS/HTTPS for production
- Regularly rotate passwords

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src tests
```

## License

MIT
