# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Gaming Agent is a distributed automation system where a Master Claude instance controls multiple remote gaming PCs through MCP (Model Context Protocol) servers. The primary use case is autonomous game account leveling across multiple machines simultaneously.

**Current State:** Core implementation complete with MCP server, HTTP/SSE transport, CLI, and 24 tools including workflow automation.

## Architecture

```
Master Claude (Orchestrator)
    ↓ MCP Protocol (JSON-RPC over HTTP/SSE + Bearer Token Auth)
    ├─→ PC #1 (HTTP Server :8765) ─→ PyAutoGUI + Optional Local VLM + Workflow Engine
    ├─→ PC #2 (HTTP Server :8765) ─→ PyAutoGUI + Optional Local VLM + Workflow Engine
    └─→ PC #N (HTTP Server :8765) ─→ PyAutoGUI + Optional Local VLM + Workflow Engine
```

**Three Deployment Options:**
- **Option A (Simplest):** Claude analyzes all screenshots, gaming PCs are simple executors
- **Option B (Recommended):** Hybrid - Claude for high-level decisions, local VLM for fast visual processing
- **Option C (Privacy):** Fully local orchestrator (e.g., Qwen3-72B), no cloud APIs

## Project Structure

```
src/ai_gaming_agent/
├── __init__.py              # Package version
├── cli.py                   # CLI commands (serve, init, config)
├── config.py                # Configuration management (JSON file)
├── server.py                # MCP server implementation (stdio transport)
├── http_server.py           # FastAPI + SSE HTTP server with Bearer token auth
└── tools/                   # 24 MCP tools
    ├── screen.py            # screenshot, get_screen_size
    ├── mouse.py             # click, move_to, drag_to, scroll
    ├── keyboard.py          # type_text, press_key, hotkey
    ├── files.py             # read/write/list/upload/download
    ├── system.py            # execute_command, focus_window
    ├── workflow.py          # run_workflow, demo_terminal_workflow
    └── vlm.py               # analyze_screen (optional Ollama integration)

tests/
├── test_config.py           # Unit tests for config
├── test_tools.py            # Unit tests for tools
├── test_http_server.py      # Unit tests for HTTP/SSE server
├── test_workflow.py         # Unit tests for workflow tools
├── test_vlm.py              # Unit tests for VLM tool
├── test_cli.py              # Unit tests for CLI
└── integration/             # Integration tests (LOCAL ONLY)
    ├── test_gui_automation.py
    ├── test_demo_workflow.py
    └── test_full_workflow.py
```

## Key Commands

```bash
# Development
uv sync --extra dev                    # Install dependencies
uv run ruff check src tests            # Lint
uv run pytest tests/ --ignore=tests/integration -v  # Unit tests (CI)
uv run pytest tests/integration -v     # Integration tests (local only)
uv run pytest tests/integration/test_full_workflow.py -v  # Test complete workflow

# Running the server
gaming-agent init --password secret              # Create config
gaming-agent serve                               # Start HTTP/SSE server
gaming-agent serve --transport stdio             # Start stdio server (for parent MCP)
gaming-agent config                              # Show config

# Quick workflow test
python examples/terminal_demo.py                 # Run demo terminal workflow
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

## MCP Tools (24 total)

| Category | Tools |
|----------|-------|
| **Screen** | `screenshot`, `get_screen_size`, `analyze_screen` |
| **Mouse** | `click`, `double_click`, `move_to`, `drag_to`, `scroll`, `get_mouse_position` |
| **Keyboard** | `type_text` (with `use_paste` for fast input), `press_key`, `hotkey` |
| **File** | `read_file`, `write_file`, `list_files`, `upload_file`, `download_file` |
| **System** | `execute_command`, `get_system_info`, `list_windows`, `focus_window` |
| **Workflow** | `run_workflow`, `demo_terminal_workflow` |
| **VLM** | `analyze_screen` (optional Ollama integration) |

## HTTP/SSE Transport (Remote Control)

The server supports both **stdio** (for parent MCP) and **HTTP/SSE** (for remote clients) transports:

### HTTP Endpoint
- **URL:** `http://PC_IP:8765/mcp`
- **Auth:** Bearer token (configured password in config.json)
- **Protocol:** Server-Sent Events (SSE) for incoming messages + POST for outgoing messages
- **Health Check:** `GET http://PC_IP:8765/health` (no auth required)

### Starting HTTP Server
```bash
gaming-agent serve --transport http
# or use default (which is http)
gaming-agent serve
```

### Remote Connection Example
```bash
curl -H "Authorization: Bearer your-password" http://localhost:8765/health
# Returns: {"status": "ok", "version": "0.1.0"}
```

### Security
- Password stored in `~/.gaming-agent/config.json`
- All HTTP requests require Bearer token authentication
- Health endpoint requires no authentication
- Enforce HTTPS in production

---

## Workflow Automation

The platform includes two new workflow tools for executing sequences of actions:

### `demo_terminal_workflow(text: str)`
A ready-made workflow that:
1. Detects platform and terminal
2. Opens a new terminal window
3. Types the provided text (uses fast paste input by default for speed)
4. Presses Enter to execute
5. Captures screenshot
6. Closes the terminal

**Perfect for:** Testing, demos, and simple terminal commands.

**Example:**
```json
{
  "tool": "demo_terminal_workflow",
  "args": { "text": "echo hello world" }
}
```

### `run_workflow(steps: list[dict])`
A generic workflow executor that chains multiple actions:
1. Accepts array of steps
2. Executes each step sequentially
3. Supports delays between steps (`wait_ms`)
4. Returns success/failure for each step
5. Optional error handling strategies

**Perfect for:** Complex automation sequences, batch operations.

**Example with character-by-character typing:**
```json
{
  "tool": "run_workflow",
  "args": {
    "steps": [
      {
        "tool": "execute_command",
        "args": { "command": "gnome-terminal" },
        "wait_ms": 1500
      },
      {
        "tool": "type_text",
        "args": { "text": "python script.py" },
        "wait_ms": 200
      },
      {
        "tool": "press_key",
        "args": { "key": "enter" }
      },
      {
        "tool": "screenshot",
        "args": {}
      }
    ]
  }
}
```

**Example with fast paste input (recommended for long text):**
```json
{
  "tool": "run_workflow",
  "args": {
    "steps": [
      {
        "tool": "execute_command",
        "args": { "command": "gnome-terminal" },
        "wait_ms": 1500
      },
      {
        "tool": "type_text",
        "args": { "text": "echo 'Long text here' && python script.py", "use_paste": true },
        "wait_ms": 200
      },
      {
        "tool": "press_key",
        "args": { "key": "enter" }
      },
      {
        "tool": "screenshot",
        "args": {}
      }
    ]
  }
}
```

---

## Fast Text Input with `use_paste` Parameter

The `type_text` tool now supports a `use_paste` parameter for significantly faster text input, especially useful for long strings or commands:

### How It Works
- **`use_paste=True`:** Copies text to clipboard and pastes using Ctrl+V (Linux/Windows) or Cmd+V (macOS)
  - ⚡ **Much faster** for long text (especially important for automation)
  - ✓ **Platform-aware** (automatically uses correct hotkey)
  - ✓ **Clipboard-safe** (saves and restores original clipboard content)

- **`use_paste=False` (default):** Character-by-character typing via pyautogui
  - ✓ Works in all applications (including games)
  - Can be slow for long text strings
  - Controllable via `interval` parameter for game input

### Use Cases
- **Terminal commands:** Use `use_paste=True` for faster script input
- **Form filling:** Use `use_paste=True` for long text entries
- **Game input:** Use `use_paste=False` (default) for realistic character-by-character input
- **Credentials:** Consider security implications when pasting sensitive data

### Example: Fast Terminal Input
```python
# Slow (character-by-character)
type_text("python train_model.py --epochs 100 --lr 0.001")

# Fast (clipboard paste)
type_text("python train_model.py --epochs 100 --lr 0.001", use_paste=True)
```

### In Workflows
```json
{
  "tool": "type_text",
  "args": {
    "text": "long command here",
    "use_paste": true
  }
}
```

---

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
| `docs/testing.md` | Complete testing guide (unit, integration, CI) |
| `docs/configuration.md` | Config file reference with VLM setup |
| `docs/integration-testing.md` | Integration testing with OCR and screenshots |
| `docs/workflow.md` | **NEW:** Complete workflow automation guide with examples |
| `docs/tools.txt` | MCP tools API reference (updated with new tools) |
| `docs/architecture.txt` | System design |
| `docs/security.txt` | Security best practices |
| `README.md` | **UPDATED:** Includes workflow section and quick test |
| `examples/terminal_demo.py` | **NEW:** Standalone Python script for terminal workflow demo |
| `idea.md` | Full architecture specification |

## Development Workflow

When working on this project, follow this pattern:

### 1. Understanding a New Feature
- Read the relevant tool file in `src/ai_gaming_agent/tools/`
- Check the corresponding test file in `tests/`
- Review the documentation in `docs/`

### 2. Making Changes
- Edit tool implementation (e.g., `src/ai_gaming_agent/tools/workflow.py`)
- Update tool registry in `src/ai_gaming_agent/server.py`
- Update tool exports in `src/ai_gaming_agent/tools/__init__.py`
- Add unit tests in `tests/test_*.py`
- Add integration tests if GUI interaction needed in `tests/integration/`

### 3. Validating Changes
```bash
# Unit tests (no display required - runs in CI)
uv run pytest tests/ --ignore=tests/integration -v

# Integration tests (requires display - local only)
uv run pytest tests/integration -v

# Linting and type checking
uv run ruff check src tests
```

### 4. Important Notes
- **HTTP Server:** Default transport is HTTP/SSE (set in `cli.py` `cmd_serve()`)
- **Lazy Imports:** GUI modules (pyautogui, PIL) use lazy imports to avoid breaking CI
- **VLM Optional:** `analyze_screen` returns error if Ollama not configured
- **Workflow Engine:** All tools must be callable from `_get_tool_handler()` in `workflow.py`
- **Fast Text Input:** Use `type_text(..., use_paste=True)` for clipboard-based fast input when typing long strings or commands

---

## Code Standards

- Python 3.12+
- Type hints on all functions
- ruff for linting
- Lazy imports for GUI modules (avoid breaking CI)
- Files under 500 LOC
- Security: path validation, command blocklist
- All new tools must be documented in `docs/tools.txt`
- All new features must have unit tests + integration tests (if GUI-related)
