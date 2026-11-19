# Reviewer instructions — developerz-ai/ai-gaming-agent-mcp

> Read by the developerz.ai reviewer at EVERY review of this repository, at the reviewed
> commit, as this repo's own layer of the reviewer's prompt. It refines the platform rules
> (a finding is cited or withheld) and never overrides them. `CLAUDE.md` is the source of
> truth; this file is its review-time distillation. Keep it under 12,000 characters — past
> that it is cut.

## Stack

Python 3.12 + uv (Hatchling build), MCP server (`mcp>=2.3.0,<3`) over stdio and FastAPI
HTTP/SSE, PyAutoGUI + Pillow for GUI automation, Pydantic settings, optional Ollama VLM,
Ruff + pytest. The app is its own uv project in `apps/ai-gaming-agent-mcp/`; the root
`pyproject.toml` only registers it as a workspace member.

The gate is `bin/check`: `uv sync --extra dev`, then `uv run ruff check src tests` and
`uv run pytest tests/ --ignore=tests/integration -v` inside the app directory. Exit 0 = the
change passes, 75 = the environment was unreachable and the change was never graded (blame
the environment, never the change), 1 = the change is red. CI (`.github/workflows/ci.yml`,
job `test`) runs the same two commands as separate steps, without `bin/check`.

## What to reject

**Security surface (`docs/security.txt`, `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/http_server.py`)**
- Any `/mcp` route or message path that skips Bearer authentication, or that runs the
  Host/Origin allow-list check before the token check. Order is fixed: bad token 401, empty
  configured password 403, disallowed Host 421, disallowed Origin 403.
- Widening the defaults of `server.allowed_hosts` / `server.allowed_origins` beyond loopback
  in `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/config.py`, or a wildcard that matches more
  than `host:port` forms.
- Adding authentication or Host validation requirements to `GET /health`, or putting anything
  but status and version in its body.
- A file tool in `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/tools/files.py` that reads or writes without `_is_path_allowed`, or a
  command path in `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/tools/system.py` that skips `_is_command_blocked` or the
  `security.max_command_timeout` bound.
- A feature-toggle bypass: a tool that runs while its `features.*` flag is off.
- The configured password, a Bearer token or clipboard content logged, echoed in an error
  message or returned in a tool result.

**Public tree (`apps/ai-gaming-agent-mcp/tests/test_public_tree.py`)**
- This repository is public. Reject internal hostnames, internal run/task identifiers, or
  internal tooling names in any tracked file outside `.dz/`, and any new MCP server entry in
  `.mcp.json` other than the public ones the guard allows.

**Tool contract (`.claude/agents/mcp-tools.md`)**
- A new or renamed tool that is not in all four places: the `TOOL_DEFINITIONS` entry plus
  `TOOL_HANDLERS` mapping in `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/server.py`, the lazy export in `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/tools/__init__.py`,
  `_get_tool_handler()` in `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/tools/workflow.py`, and `docs/tools.txt`.
- A tool registered with an `@server.list_tools()` / `@server.call_tool()` decorator: mcp 2
  has none; handlers go through the `Server(...)` constructor (`on_list_tools`,
  `on_call_tool`).
- A tool result that is not a dict with consistent `success` and `error` keys; workflow
  dispatch reads them.
- A top-level `import pyautogui`, `PIL` or another display-bound module in a module the unit
  suite imports. GUI imports stay lazy so CI needs no display.
- `docs/tools.txt` advertising MCP resource URIs while `create_server` registers no resource
  handler (`apps/ai-gaming-agent-mcp/tests/test_client_docs.py` pins this), or a `claude_desktop_config.json` example
  using `"transport": "sse"`.

**Layout and scripts**
- Moving `uv.lock` to the repository root or deleting the `[tool.uv.workspace]` table of
  either `pyproject.toml` (`apps/ai-gaming-agent-mcp/tests/test_layout.py`).
- A change to `bin/setup` or `bin/check` that lets a missing or unusable toolchain exit
  anything but 75, or that drifts from the commands CI runs (`apps/ai-gaming-agent-mcp/tests/test_bin_scripts.py`,
  `apps/ai-gaming-agent-mcp/tests/test_toolchain.py`). If CI's commands change, `bin/check` and those tests change in
  the same PR.

**Code standards (`CLAUDE.md` § Code Standards)**
- A function without type hints.
- A new source file over 500 lines, or a change that grows `apps/ai-gaming-agent-mcp/src/ai_gaming_agent/tools/workflow.py` (already at
  the limit) further instead of splitting it.

**Tests (`CLAUDE.md` § Non-negotiable rules, `docs/testing.md`)**
- A bug fix without a test that fails before it; a new tool or changed interface without a
  case in `apps/ai-gaming-agent-mcp/tests/test_tools.py` (and `apps/ai-gaming-agent-mcp/tests/test_workflow.py` for dispatch behaviour).
- A GUI-dependent feature without an integration test under `apps/ai-gaming-agent-mcp/tests/integration/`.
- A deleted, skipped or weakened test, or a silenced Ruff rule, added to get green.
- A unit test that needs a real display, a real Ollama endpoint or the network.

## Gates that matter

- CI job `test` in `.github/workflows/ci.yml`: Ruff, then the unit suite (integration
  excluded). Green on the head commit is what proves a PR; `bin/check` is the local mirror and
  `.githooks/pre-commit` runs it.
- Integration tests (`apps/ai-gaming-agent-mcp/tests/integration/`) are local only and skip under `CI=true`; a PR
  touching real-display GUI or OCR behaviour should say how it was exercised
  (`.claude/skills/integration-gui/SKILL.md`). Their absence from CI is not a finding.

## Never flag

- `apps/ai-gaming-agent-mcp/uv.lock`: generated by uv.
- Import order and whitespace: Ruff owns them (`E,F,I,W`, line length 120, `E501` ignored).
- `security.allowed_paths` defaulting to `[]` (unrestricted) and the substring command
  blocklist: documented behaviour in `CLAUDE.md` § Configuration defaults; a change to them is
  a design change, not a bug in an unrelated PR.
- HTTP (not HTTPS) in the server itself: TLS is terminated by a reverse proxy
  (`docs/security.txt`).
- Plain-text `.txt` docs under `docs/`: chosen on purpose.
- The `.dz/` directory's own layout: the platform owns it.
