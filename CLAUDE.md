# CLAUDE.md

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

## Stack

| Area | Declared stack |
|------|----------------|
| Language | Python >=3.12 |
| Package/build | uv, Hatchling |
| MCP | `mcp>=1.0.0` |
| HTTP | FastAPI >=0.115, `uvicorn[standard]` >=0.32 |
| Automation | PyAutoGUI >=0.9.54, Pillow >=10, pyperclip >=1.8 |
| Configuration | Pydantic >=2, pydantic-settings >=2 |
| System | screeninfo >=0.8.1, psutil >=6 |
| VLM (optional) | Ollama >=0.4 via the `vlm` extra |
| Quality | Ruff >=0.8; pytest >=8 and pytest-asyncio >=0.24 via the `dev` extra |
| Integration extra | pytest and pytesseract >=0.3.10 |

Ruff targets Python 3.12, line length 120, and selects `E,F,I,W` (ignoring `E501`). Pytest uses `asyncio_mode = "auto"`, `testpaths = ["tests"]`, and the `integration` marker.

## Commands

| Command | Purpose |
|---------|---------|
| `bin/setup` | Install system prerequisites (`xvfb`, `scrot`, `python3-tk`, `python3-dev`, `tesseract-ocr`) and run `uv sync --extra dev`. |
| `bin/dev` | Run the HTTP server under `xvfb-run` on `127.0.0.1:8765` with the development password. |
| `bin/check` | **The gate:** `uv run ruff check src tests && uv run pytest tests/ --ignore=tests/integration -v`. |
| `bin/stop` | Stop the development stack; currently a no-op. |

CLI entry point: `gaming-agent`. Common subcommands are `gaming-agent init --password secret`, `gaming-agent serve` (HTTP by default), `gaming-agent serve --transport stdio`, and `gaming-agent config`.

## Repository structure

| Path | Responsibility |
|------|----------------|
| `src/ai_gaming_agent/__init__.py` | Package version. |
| `src/ai_gaming_agent/cli.py` | CLI commands and transport selection. |
| `src/ai_gaming_agent/config.py` | Pydantic configuration and JSON persistence. |
| `src/ai_gaming_agent/server.py` | Stdio MCP server and tool registry. |
| `src/ai_gaming_agent/http_server.py` | FastAPI/SSE HTTP transport and authentication. |
| `src/ai_gaming_agent/tools/screen.py` | Screen capture and dimensions. |
| `src/ai_gaming_agent/tools/mouse.py` | Pointer control. |
| `src/ai_gaming_agent/tools/keyboard.py` | Text and key input. |
| `src/ai_gaming_agent/tools/files.py` | File operations and path validation. |
| `src/ai_gaming_agent/tools/system.py` | Commands, processes, windows, and system information. |
| `src/ai_gaming_agent/tools/workflow.py` | Workflow execution and tool dispatch. |
| `src/ai_gaming_agent/tools/vlm.py` | Optional Ollama screen analysis. |
| `src/ai_gaming_agent/tools/__init__.py` | Lazy public exports for MCP tools. |
| `tests/test_*.py` | Unit tests: CLI, config, HTTP server, tools, VLM, and workflows. |
| `tests/integration/` | Display-dependent GUI and OCR integration tests; local only. |

## MCP tools (23)

| Category | Tools |
|----------|-------|
| Screen | `screenshot`, `get_screen_size` |
| Mouse | `click`, `double_click`, `move_to`, `drag_to`, `scroll`, `get_mouse_position` |
| Keyboard | `type_text`, `press_key`, `hotkey` |
| File | `read_file`, `write_file`, `list_files`, `upload_file`, `download_file` |
| System | `execute_command`, `get_system_info`, `list_windows`, `focus_window` |
| Workflow | `run_workflow`, `demo_terminal_workflow` |
| VLM | `analyze_screen` |

The registry in `src/ai_gaming_agent/server.py` and exports in `src/ai_gaming_agent/tools/__init__.py` must remain aligned. Workflow details and `type_text(..., use_paste=True)` guidance live in `docs/workflow.md`; the API reference lives in `docs/tools.txt`.

## Configuration defaults

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

## Transports

| Transport | Interface | Authentication |
|-----------|-----------|----------------|
| HTTP/SSE (CLI default) | `GET /mcp` for SSE; `POST /mcp/messages` for messages | Bearer token required. Empty configured password rejects requests with 403; wrong token returns 401. |
| Health | `GET /health` | None; returns the status and current package version. |
| stdio | Standard input/output MCP transport | Managed by the parent MCP client. |

Use HTTPS in production. The HTTP server exposes GUI automation on the configured bind address and port.

## Testing

| Suite | Command | Environment |
|-------|---------|-------------|
| Unit/CI | `uv run pytest tests/ --ignore=tests/integration -v` | No display required. |
| Integration | `uv run pytest tests/integration -v` | Real or isolated display; OCR cases require Tesseract. |
| Gate | `bin/check` | Ruff plus the unit suite. |

Integration tests are local-only and skip in CI. Before real-display GUI or OCR work, read `.claude/skills/integration-gui/SKILL.md`.

## Specialist instructions

| Source | Use it for |
|--------|------------|
| `.claude/agents/mcp-tools.md` | MCP tool registry, handlers, workflow dispatch, tests, and tool documentation. |
| `.claude/skills/verify-change/SKILL.md` | The repository gate and its required install/run/check/stop workflow. |
| `.claude/skills/integration-gui/SKILL.md` | Real-display GUI and OCR integration tests. |

These files are authoritative for their areas; do not duplicate their detailed rules here.

## Documentation index

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
