# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Repository brain for AI Gaming Agent: an MCP server for remote PC automation. Package version: **0.2.0**.

## Non-negotiable rules

| Rule | Requirement |
|------|-------------|
| Gate | `bin/check` is the gate. Red is not a pull request; fix the cause. |
| Verify | Run the narrowest relevant check first; the harness runs the full gate after all editors finish. |
| Tests | Reproduce a bug with a failing test before fixing it. Never delete or weaken a test to get green. |
| Guards | Never silence a lint, type, test, or security guard. A machine-enforced rule wins. |
| Disclosure | Agents are bots; disclose that in usernames and every comment. Never impersonate a human. |
| Merge gates | CI, review verdict, and branch protection decide merges. Never merge around red or missing gates; never self-approve. |
| Bot etiquette | Never argue with or reply to another bot. Act on dependency-bot PRs like any other PR. |
| Checkout | One checkout and branch. Never create a worktree; the harness owns commits, pushes, and PRs. |
| File ownership | Edit only your assigned paths; report other required paths instead of touching them. |
| Credentials | Resolve secrets from the vault at point of use. Never expose them in context, logs, comments, or commits. |
| Scope | Do one task. Report unrelated defects separately; do not bundle them. |
| Change discipline | Read before editing; make the smallest correct change; keep files under 500 LOC. |
| Tool changes | Follow `.claude/agents/mcp-tools.md`: registry, export, workflow dispatch, tests, and docs stay aligned. |
| GUI imports | Keep PyAutoGUI/Pillow-heavy imports lazy so CI needs no display. |
| Tool results | Return dictionaries with consistent `success` and `error` keys. |

## Project Overview

AI Gaming Agent is a distributed automation system where a Master Claude instance controls multiple remote gaming PCs through MCP (Model Context Protocol) servers. The primary use case is autonomous game account leveling across multiple machines simultaneously.

**Current State:** Core implementation complete with MCP server, HTTP/SSE transport, CLI, and 23 tools including workflow automation.

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

## Stack

| Area | Declared stack |
|------|----------------|
| Language | Python >=3.12 |
| Package/build | uv, Hatchling |
| MCP | `mcp>=1.30.0,<2` |
| HTTP | FastAPI >=0.115, `uvicorn[standard]` >=0.32 |
| Automation | PyAutoGUI >=0.9.54, Pillow >=10, pyperclip >=1.8 |
| Configuration | Pydantic >=2, pydantic-settings >=2 |
| System | screeninfo >=0.8.1, psutil >=6 |
| VLM (optional) | Ollama >=0.4 via the `vlm` extra |
| Quality | Ruff >=0.8; pytest >=8 and pytest-asyncio >=0.24 via the `dev` extra |
| Integration extra | pytest and pytesseract >=0.3.10 |

Ruff targets Python 3.12, line length 120, and selects `E,F,I,W` (ignoring `E501`). Pytest uses `asyncio_mode = "auto"`, `testpaths = ["tests"]`, and the `integration` marker.

## Project Structure

The application lives in `apps/ai-gaming-agent-mcp/` - its own uv project with its own
`pyproject.toml`, `uv.lock`, `src/` and `tests/`. Every uv/pytest/ruff command below runs
from that directory (`(cd apps/ai-gaming-agent-mcp && <command>)`); the repository root only
registers the app as a uv workspace member.

```
apps/ai-gaming-agent-mcp/
├── src/ai_gaming_agent/
│   ├── __init__.py              # Package version
│   ├── cli.py                   # CLI commands (serve, init, config)
│   ├── config.py                # Configuration management (JSON file)
│   ├── server.py                # MCP server implementation (stdio transport)
│   ├── http_server.py           # FastAPI + SSE HTTP server with Bearer token auth
│   └── tools/                   # 23 MCP tools
│       ├── screen.py            # screenshot, get_screen_size
│       ├── mouse.py             # click, move_to, drag_to, scroll
│       ├── keyboard.py          # type_text, press_key, hotkey
│       ├── files.py             # read/write/list/upload/download
│       ├── system.py            # execute_command, focus_window
│       ├── workflow.py          # run_workflow, demo_terminal_workflow
│       └── vlm.py               # analyze_screen (optional Ollama integration)
│
├── tests/
│   ├── test_config.py           # Unit tests for config
│   ├── test_tools.py            # Unit tests for tools
│   ├── test_http_server.py      # Unit tests for HTTP/SSE server
│   ├── test_workflow.py         # Unit tests for workflow tools
│   ├── test_vlm.py              # Unit tests for VLM tool
│   ├── test_cli.py              # Unit tests for CLI
│   ├── test_layout.py           # Layout pins (uv workspace, documented commands)
│   └── integration/             # Integration tests (LOCAL ONLY)
│       ├── test_gui_automation.py
│       ├── test_demo_workflow.py
│       └── test_full_workflow.py
```

### Repository structure

| Path | Responsibility |
|------|----------------|
| `pyproject.toml` | Repository root workspace manifest; registers the app as a member and is not a buildable project. |
| `bin/` | `setup`, `dev`, `check`, and `stop` helpers; each runs uv inside the app directory. |
| `docs/` | Documentation; see the Documentation index below. |
| `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/__init__.py` | Package version. |
| `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/cli.py` | CLI commands and transport selection. |
| `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/config.py` | Pydantic configuration and JSON persistence. |
| `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/server.py` | Stdio MCP server and tool registry. |
| `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/http_server.py` | FastAPI/SSE HTTP transport and authentication. |
| `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/tools/screen.py` | Screen capture and dimensions. |
| `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/tools/mouse.py` | Pointer control. |
| `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/tools/keyboard.py` | Text and key input. |
| `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/tools/files.py` | File operations and path validation. |
| `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/tools/system.py` | Commands, processes, windows, and system information. |
| `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/tools/workflow.py` | Workflow execution and tool dispatch. |
| `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/tools/vlm.py` | Optional Ollama screen analysis. |
| `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/tools/__init__.py` | Lazy public exports for MCP tools. |
| `apps/ai-gaming-agent-mcp/tests/test_*.py` | Unit tests: CLI, config, HTTP server, tools, VLM, and workflows. |
| `apps/ai-gaming-agent-mcp/tests/integration/` | Display-dependent GUI and OCR integration tests; local only. |

## Commands

| Command | Purpose |
|---------|---------|
| `bin/setup` | Install system prerequisites (`xvfb`, `scrot`, `python3-tk`, `python3-dev`, `tesseract-ocr`) and run `uv sync --extra dev`. |
| `bin/dev` | Run the HTTP server under `xvfb-run` on `127.0.0.1:8765` with the development password. |
| `bin/check` | **The gate:** `uv run ruff check src tests && uv run pytest tests/ --ignore=tests/integration -v`. |
| `bin/stop` | Stop the development stack; currently a no-op. |

CLI entry point: `gaming-agent`. Common subcommands are `gaming-agent init --password secret`, `gaming-agent serve` (HTTP by default), `gaming-agent serve --transport stdio`, and `gaming-agent config`.

### Key Commands

```bash
# Development (run from the repository root; the app lives in apps/ai-gaming-agent-mcp)
(cd apps/ai-gaming-agent-mcp && uv sync --extra dev)    # Install dependencies
(cd apps/ai-gaming-agent-mcp && uv run ruff check src tests)    # Lint
(cd apps/ai-gaming-agent-mcp && uv run pytest tests/ --ignore=tests/integration -v)  # Unit tests (CI)
(cd apps/ai-gaming-agent-mcp && uv run pytest tests/integration -v)     # Integration tests (local only)
(cd apps/ai-gaming-agent-mcp && uv run pytest tests/integration/test_full_workflow.py -v)  # Test complete workflow

# Running the server
gaming-agent init --password secret              # Create config
gaming-agent serve                               # Start HTTP/SSE server
gaming-agent serve --transport stdio             # Start stdio server (for parent MCP)
gaming-agent config                              # Show config

# Quick workflow test
python apps/ai-gaming-agent-mcp/examples/terminal_demo.py                 # Run demo terminal workflow
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
```

### Configuration defaults

Configuration is stored at `~/.gaming-agent/config.json`. Environment overrides use the `GAMING_AGENT_` prefix and `__` for nested fields, such as `GAMING_AGENT_SERVER__PORT`.

| Setting | Default | Note |
|---------|---------|------|
| `server.host` | `0.0.0.0` | Bind address. |
| `server.port` | `8765` | HTTP port. |
| `server.password` | empty string | Empty password causes HTTP authentication requests to be rejected with 403. |
| `vlm.enabled` | `false` | VLM is optional. |
| `vlm.provider` | `ollama` | Supported provider when enabled. |
| `vlm.model` | `qwen2.5-vl:3b` | Model name. |
| `vlm.endpoint` | `http://localhost:11434` | Ollama endpoint. |
| `security.allowed_paths` | `[]` | Empty means unrestricted file paths. |
| `security.blocked_commands` | `["rm -rf", "format", "del /f", "mkfs"]` | Command blocklist. |
| `security.max_command_timeout` | `30` | Seconds. |
| `features.screenshot` | `true` | Feature toggle. |
| `features.file_access` | `true` | Feature toggle. |
| `features.command_execution` | `true` | Feature toggle. |
| `features.mouse_control` | `true` | Feature toggle. |
| `features.keyboard_control` | `true` | Feature toggle. |

## MCP tools (23)

| Category | Tools |
|----------|-------|
| Screen | `screenshot`, `get_screen_size` |
| Mouse | `click`, `double_click`, `move_to`, `drag_to`, `scroll`, `get_mouse_position` |
| Keyboard | `type_text` (with `use_paste` for fast input), `press_key`, `hotkey` |
| File | `read_file`, `write_file`, `list_files`, `upload_file`, `download_file` |
| System | `execute_command`, `get_system_info`, `list_windows`, `focus_window` |
| Workflow | `run_workflow`, `demo_terminal_workflow` |
| VLM | `analyze_screen` (optional Ollama integration) |

The registry in `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/server.py` and exports in `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/tools/__init__.py` must remain aligned. Workflow details and `type_text(..., use_paste=True)` guidance live in `docs/workflow.md`; the API reference lives in `docs/tools.txt`.

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
# Returns: {"status": "ok", "version": "0.2.0"}
```

### Security
- Password stored in `~/.gaming-agent/config.json`
- All HTTP requests require Bearer token authentication
- Health endpoint requires no authentication
- Enforce HTTPS in production

### Transports

| Transport | Interface | Authentication |
|-----------|-----------|----------------|
| HTTP/SSE (CLI default) | `GET /mcp` for SSE; `POST /mcp/messages` for messages | Bearer token required. Empty configured password rejects requests with 403; wrong token returns 401. |
| Health | `GET /health` | None; returns the status and current package version. |
| stdio | Standard input/output MCP transport | Managed by the parent MCP client. |

Use HTTPS in production. The HTTP server exposes GUI automation on the configured bind address and port.

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

## Testing

| Suite | Command | Environment |
|-------|---------|-------------|
| Unit/CI | `uv run pytest tests/ --ignore=tests/integration -v` | No display required. |
| Integration | `uv run pytest tests/integration -v` | Real or isolated display; OCR cases require Tesseract. |
| Gate | `bin/check` | Ruff plus the unit suite. |

Integration tests are local-only and skip in CI. Before real-display GUI or OCR work, read `.claude/skills/integration-gui/SKILL.md`.

### Unit Tests (CI)
- Run in GitHub Actions on every push/PR
- Test config, file operations, tool interfaces
- No display required
- Command: `(cd apps/ai-gaming-agent-mcp && uv run pytest tests/ --ignore=tests/integration -v)`

### Integration Tests (Local Only)
- Require real display (X11/Windows/macOS)
- Perform actual GUI automation
- OCR verification with tesseract
- Auto-skip in CI (detected via `CI=true` env var)
- Command: `(cd apps/ai-gaming-agent-mcp && uv run pytest tests/integration -v)`

## Specialist instructions

| Source | Use it for |
|--------|------------|
| `.claude/agents/mcp-tools.md` | MCP tool registry, handlers, workflow dispatch, tests, and tool documentation. |
| `.claude/skills/verify-change/SKILL.md` | The repository gate and its required install/run/check/stop workflow. |
| `.claude/skills/integration-gui/SKILL.md` | Real-display GUI and OCR integration tests. |

These files are authoritative for their areas; do not duplicate their detailed rules here.

## Documentation

| Path | Contents |
|------|----------|
| `README.md` | Project overview and quick start. |
| `docs/workflow.md` | Workflow concepts, `run_workflow`, terminal demo, and fast paste input. |
| `docs/tools.txt` | MCP tool API reference. |
| `docs/configuration.md` | Configuration and VLM setup. |
| `docs/testing.md` | Unit, integration, and CI testing guide. |
| `docs/integration-testing.md` | GUI and OCR integration testing. |
| `docs/architecture.txt` | System design. |
| `docs/security.txt` | Security practices. |
| `docs/README.md` | Documentation index. |
| `apps/ai-gaming-agent-mcp/examples/terminal_demo.py` | Standalone Python script for terminal workflow demo. |
| `apps/ai-gaming-agent-mcp/idea.md` | Full architecture specification. |

## Development Workflow

When working on this project, follow this pattern:

### 1. Understanding a New Feature
- Read the relevant tool file in `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/tools/`
- Check the corresponding test file in `apps/ai-gaming-agent-mcp/tests/`
- Review the documentation in `docs/`

### 2. Making Changes
- Edit tool implementation (e.g., `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/tools/workflow.py`)
- Update tool registry in `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/server.py`
- Update tool exports in `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/tools/__init__.py`
- Add unit tests in `apps/ai-gaming-agent-mcp/tests/test_*.py`
- Add integration tests if GUI interaction needed in `apps/ai-gaming-agent-mcp/tests/integration/`

### 3. Validating Changes
```bash
# Unit tests (no display required - runs in CI)
(cd apps/ai-gaming-agent-mcp && uv run pytest tests/ --ignore=tests/integration -v)

# Integration tests (requires display - local only)
(cd apps/ai-gaming-agent-mcp && uv run pytest tests/integration -v)

# Linting and type checking
(cd apps/ai-gaming-agent-mcp && uv run ruff check src tests)
```

### 4. Important Notes
- **HTTP Server:** Default transport is HTTP/SSE (set in `cli.py` `cmd_serve()`)
- **Lazy Imports:** GUI modules (pyautogui, PIL) use lazy imports to avoid breaking CI
- **VLM Optional:** `analyze_screen` returns error if Ollama not configured
- **Workflow Engine:** All tools must be callable from `_get_tool_handler()` in `workflow.py`
- **Fast Text Input:** Use `type_text(..., use_paste=True)` for clipboard-based fast input when typing long strings or commands

## Code Standards

- Python 3.12+
- Type hints on all functions
- ruff for linting
- Lazy imports for GUI modules (avoid breaking CI)
- Files under 500 LOC
- Security: path validation, command blocklist
- All new tools must be documented in `docs/tools.txt`
- All new features must have unit tests + integration tests (if GUI-related)
