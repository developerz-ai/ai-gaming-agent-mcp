## Task List

Now I have a complete understanding of the project. Let me create the master plan:

---

# MASTER PLAN: AI Gaming Agent - One-Command Terminal Workflow

## Executive Summary

The goal is to implement and test a **complete end-to-end workflow** where a single MCP command can:
1. Open a new terminal
2. Focus it
3. Type "echo hello world"
4. Click to close it

**Current State:**
- MCP server exists with 21 tools (stdio transport)
- Tools work individually (mouse, keyboard, screen, system)
- Integration tests exist but don't have a single "composite" command
- Server runs on stdio but docs mention HTTP/SSE for remote access

**Gap Analysis:**
- Missing: `run_workflow` or composite command capability
- Missing: HTTP/SSE transport for remote control (server.py only has stdio)
- Missing: Test that validates the complete workflow as a single operation
- Missing: Documentation for the "one big command" pattern

---

## Architecture Decision

After analyzing the codebase, there are two implementation approaches:

### Approach A: Add `run_workflow` MCP Tool (Recommended)
Add a new tool that accepts a sequence of actions and executes them atomically. This keeps MCP architecture clean and allows Master Claude to send one call.

### Approach B: Add Higher-Level `demo_terminal_workflow` Tool
A specific tool that does exactly the requirement: open terminal, focus, type, close.

**Decision: Approach A (run_workflow)** - More flexible, reusable, and demonstrates the pattern for gaming automation.

---

### PR 1: Add HTTP/SSE Transport & Authentication (Foundation)

The current server only supports stdio. For remote MCP access, we need HTTP/SSE with auth.

- [x] `[coding]` Create `src/ai_gaming_agent/http_server.py` - FastAPI app with SSE transport for MCP, using `/mcp` endpoint with Bearer token auth from `server.password` config
- [x] `[coding]` Update `src/ai_gaming_agent/cli.py` - Add `--transport` flag to `cmd_serve()` supporting "stdio" and "http", default to "http" for remote use
- [x] `[coding]` Add health endpoint `GET /health` in `src/ai_gaming_agent/http_server.py` returning `{"status": "ok", "version": __version__}`
- [x] `[general]` Create `tests/test_http_server.py` - Unit tests for auth validation, health endpoint, and SSE connection setup

---

### PR 2: Add `run_workflow` Composite Tool

This is the core feature - a tool that executes a sequence of actions.

- [x] `[coding]` Create `src/ai_gaming_agent/tools/workflow.py` with `run_workflow(steps: list[dict]) -> dict` function that:
  - Accepts array of steps like `[{"tool": "execute_command", "args": {...}}, {"tool": "click", "args": {...}}]`
  - Executes each step sequentially with optional delay between steps
  - Returns success/failure for each step plus overall status
  - Supports `wait_ms` field for delays between actions
- [x] `[coding]` Update `src/ai_gaming_agent/tools/__init__.py` - Add `run_workflow` to `__all__` and `_MODULE_MAP`
- [x] `[coding]` Update `src/ai_gaming_agent/server.py`:
  - Add `run_workflow` to `TOOL_DEFINITIONS` with JSON schema for steps array
  - Add `run_workflow` to `TOOL_HANDLERS` mapping
- [x] `[general]` Create `tests/test_workflow.py` - Unit test for `run_workflow()` using mocked tool functions to verify step execution order

---

### PR 3: Add `demo_terminal_workflow` Convenience Tool

A ready-made command that does the exact "open terminal, focus, type, close" sequence.

- [x] `[coding]` Add `demo_terminal_workflow(text: str = "echo hello world") -> dict` to `src/ai_gaming_agent/tools/workflow.py`:
  - Detects platform and terminal command (gnome-terminal, konsole, xterm, cmd, Terminal.app)
  - Opens terminal via `execute_command()`
  - Waits for terminal to open (configurable delay)
  - Types the provided text using `type_text()`
  - Presses Enter using `press_key("enter")`
  - Waits for output
  - Takes screenshot for verification
  - Closes terminal with platform-appropriate hotkey (Alt+F4, Cmd+Q)
  - Returns detailed result with screenshot, timing, and success status
- [x] `[coding]` Update `src/ai_gaming_agent/server.py` - Add `demo_terminal_workflow` to tool definitions and handlers
- [x] `[general]` Create `tests/integration/test_demo_workflow.py` - Integration test that runs `demo_terminal_workflow()` and verifies with OCR

---

### PR 4: Add `analyze_screen` VLM Tool (Documented but Missing)

The docs mention `analyze_screen` but it's not implemented. Add it for completeness.

- [x] `[coding]` Create `src/ai_gaming_agent/tools/vlm.py` with:
  - `analyze_screen(prompt: str) -> dict` function
  - Uses Ollama client if VLM enabled in config
  - Takes screenshot, sends to VLM with prompt, returns response
  - Returns error if VLM not configured
- [x] `[coding]` Update `src/ai_gaming_agent/tools/__init__.py` - Add `analyze_screen` to exports
- [x] `[coding]` Update `src/ai_gaming_agent/server.py` - Add `analyze_screen` tool definition and handler
- [ ] `[quick]` Update `src/ai_gaming_agent/config.py` - Ensure VLM config validation works correctly
- [ ] `[general]` Create `tests/test_vlm.py` - Unit test with mocked Ollama client

---

### PR 5: Documentation & Production Readiness

- [ ] `[general]` Update `README.md`:
  - Add section for `run_workflow` tool with examples
  - Add section for `demo_terminal_workflow`
  - Document HTTP/SSE transport setup
  - Add "Quick Test" section showing the terminal workflow
- [ ] `[quick]` Create `docs/workflow.md` - Detailed guide for creating workflows
- [ ] `[quick]` Create `examples/terminal_demo.py` - Standalone Python script that connects to the MCP server and runs the terminal workflow
- [ ] `[general]` Update `docs/tools.txt` - Add new tool documentation for `run_workflow`, `demo_terminal_workflow`, and `analyze_screen`
- [ ] `[general]` Run full lint and test suite, fix any issues in `src/` and `tests/`

---

### PR 6: Final Integration Test & Validation

- [ ] `[coding]` Create `tests/integration/test_full_workflow.py`:
  - Test that starts HTTP server in background
  - Connects via MCP client
  - Calls `demo_terminal_workflow("echo hello world")`
  - Validates output with OCR
  - Cleans up resources
- [ ] `[general]` Run `uv run pytest tests/integration -v` locally to validate everything works
- [ ] `[quick]` Update `CLAUDE.md` - Document new tools and workflow patterns

---

## Success Criteria

1. **Single Command Works**: Calling `demo_terminal_workflow("echo hello world")` via MCP opens terminal, types command, and closes it
2. **Tests Pass**: `uv run pytest tests/ --ignore=tests/integration -v` passes (8+ unit tests)
3. **Lint Clean**: `uv run ruff check src tests` shows "All checks passed!"
4. **HTTP Transport Works**: Server starts with `gaming-agent serve --transport http` and responds to `/health`
5. **Integration Test Passes**: `test_demo_workflow.py` runs successfully on local machine with display
6. **Documentation Complete**: README and docs explain how to use the new workflow tools

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `src/ai_gaming_agent/http_server.py` | CREATE | FastAPI + SSE MCP transport |
| `src/ai_gaming_agent/tools/workflow.py` | CREATE | `run_workflow`, `demo_terminal_workflow` |
| `src/ai_gaming_agent/tools/vlm.py` | CREATE | `analyze_screen` with Ollama |
| `src/ai_gaming_agent/tools/__init__.py` | EDIT | Add new tool exports |
| `src/ai_gaming_agent/server.py` | EDIT | Add new tool definitions |
| `src/ai_gaming_agent/cli.py` | EDIT | Add --transport flag |
| `tests/test_http_server.py` | CREATE | HTTP transport tests |
| `tests/test_workflow.py` | CREATE | Workflow tool unit tests |
| `tests/test_vlm.py` | CREATE | VLM tool unit tests |
| `tests/integration/test_demo_workflow.py` | CREATE | Demo workflow integration test |
| `tests/integration/test_full_workflow.py` | CREATE | Full E2E integration test |
| `README.md` | EDIT | Add workflow documentation |
| `docs/workflow.md` | CREATE | Workflow guide |
| `docs/tools.txt` | EDIT | Add new tools |
| `examples/terminal_demo.py` | CREATE | Demo script |
| `CLAUDE.md` | EDIT | Update guidance |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| HTTP/SSE complexity | Use mcp library's built-in SSE support if available |
| Platform differences | Terminal detection already exists in integration tests |
| VLM dependency | Make VLM optional, tool returns clear error if not configured |
| Integration test flakiness | Add proper waits, retry logic, and cleanup |

---

PLANNING COMPLETE