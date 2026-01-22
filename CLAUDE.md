# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Gaming Agent is a distributed automation system where a Master Claude instance controls multiple remote gaming PCs through MCP (Model Context Protocol) servers. The primary use case is autonomous game account leveling across multiple machines simultaneously.

**Current State:** Core implementation complete with MCP server, CLI, and 21 tools.

## Architecture

```
Master Claude (Orchestrator)
    ↓ MCP Protocol (JSON-RPC over HTTP/SSE)
    ├─→ PC #1 (MCP Server :8765) ─→ PyAutoGUI + Optional Local VLM
    ├─→ PC #2 (MCP Server :8765) ─→ PyAutoGUI + Optional Local VLM
    └─→ PC #N (MCP Server :8765) ─→ PyAutoGUI + Optional Local VLM
```

**Three Deployment Options:**
- **Option A (Simplest):** Claude analyzes all screenshots, gaming PCs are simple executors
- **Option B (Recommended):** Hybrid - Claude for high-level decisions, local VLM for fast visual processing
- **Option C (Privacy):** Fully local orchestrator (e.g., Qwen3-72B), no cloud APIs

## Project Structure

```
src/ai_gaming_agent/
├── __init__.py          # Package version
├── cli.py               # CLI commands (serve, init, config)
├── config.py            # Configuration management (JSON file)
├── server.py            # MCP server implementation
└── tools/               # 21 MCP tools
    ├── screen.py        # screenshot, get_screen_size
    ├── mouse.py         # click, move_to, drag_to, scroll
    ├── keyboard.py      # type_text, press_key, hotkey
    ├── files.py         # read/write/list/upload/download
    └── system.py        # execute_command, focus_window

tests/
├── test_config.py       # Unit tests for config
├── test_tools.py        # Unit tests for tools
└── integration/         # Integration tests (LOCAL ONLY)
    └── test_gui_automation.py
```

## Key Commands

```bash
# Development
uv sync --extra dev            # Install dependencies
uv run ruff check src tests    # Lint
uv run pytest tests/ --ignore=tests/integration -v  # Unit tests
uv run pytest tests/integration -v  # Integration tests (local only)

# Running the server
gaming-agent init --password secret  # Create config
gaming-agent serve                   # Start MCP server
gaming-agent config                  # Show config
```

## Configuration

Server configuration lives at `~/.gaming-agent/config.json`:

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
    "model": "qwen2.5-vl:3b",
    "endpoint": "http://localhost:11434"
  },
  "security": {
    "allowed_paths": ["/home/user/games"],
    "blocked_commands": ["rm -rf", "format"],
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
```

## MCP Tools (21 total)

| Category | Tools |
|----------|-------|
| **Screen** | `screenshot`, `get_screen_size`, `analyze_screen` |
| **Mouse** | `click`, `double_click`, `move_to`, `drag_to`, `scroll`, `get_mouse_position` |
| **Keyboard** | `type_text`, `press_key`, `hotkey` |
| **File** | `read_file`, `write_file`, `list_files`, `upload_file`, `download_file` |
| **System** | `execute_command`, `get_system_info`, `list_windows`, `focus_window` |

## Testing Strategy

### Unit Tests (CI)
- Run in GitHub Actions on every push/PR
- Test config, file operations, tool interfaces
- No display required
- Command: `uv run pytest tests/ --ignore=tests/integration -v`

### Integration Tests (Local Only)
- Require real display (X11/Windows/macOS)
- Perform actual GUI automation
- OCR verification with tesseract
- Auto-skip in CI (detected via `CI=true` env var)
- Command: `uv run pytest tests/integration -v`

## Documentation

| File | Content |
|------|---------|
| `docs/testing.md` | Complete testing guide |
| `docs/configuration.md` | Config file reference |
| `docs/tools.txt` | MCP tools API reference |
| `docs/architecture.txt` | System design |
| `docs/security.txt` | Security best practices |
| `idea.md` | Full architecture specification |

## Code Standards

- Python 3.12+
- Type hints on all functions
- ruff for linting
- Lazy imports for GUI modules (avoid breaking CI)
- Files under 500 LOC
- Security: path validation, command blocklist
