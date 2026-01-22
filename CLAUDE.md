# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Gaming Agent is a distributed automation system where a Master Claude instance controls multiple remote gaming PCs through MCP (Model Context Protocol) servers. The primary use case is autonomous game account leveling across multiple machines simultaneously.

**Current State:** Architecture specification and documentation. Implementation files (server.py, installers) are not yet in this repository.

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

## Key Design Decisions

- **MCP Protocol:** Standardized tool interface - Claude automatically discovers available tools
- **PyAutoGUI:** Cross-platform mouse/keyboard automation with multi-monitor support
- **Security-First:** Password auth, path restrictions, command blocklist, audit logging
- **Parallel Execution:** Screenshots and actions execute in parallel across all PCs

## MCP Tools (21 total)

The MCP server exposes tools in these categories:
- **Screen:** `screenshot`, `get_screen_size`, `analyze_screen` (local VLM)
- **Mouse:** `click`, `double_click`, `move_to`, `drag_to`, `scroll`, `get_mouse_position`
- **Keyboard:** `type_text`, `press_key`, `hotkey`
- **File:** `read_file`, `write_file`, `list_files`, `upload_file`, `download_file`
- **System:** `execute_command`, `get_system_info`, `list_windows`, `focus_window`

## Configuration Locations

- **Server config:** `~/.gaming-agent/config.json`
- **Claude Desktop MCP config:**
  - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
  - Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
  - Linux: `~/.config/claude/claude_desktop_config.json`

## Target Dependencies (when implementing)

```
pyautogui    # Mouse/keyboard automation
mcp          # MCP protocol implementation
pillow       # Screenshot handling
fastapi      # HTTP server
uvicorn      # ASGI server
screeninfo   # Multi-monitor support
psutil       # System info
ollama       # Optional: local VLM serving
```

Platform-specific: `pywin32` (Windows), `python3-xlib` (Linux), `pyobjc` (Mac)

## Documentation Structure

All detailed documentation lives in `/docs/`:
- `overview.txt` - Capabilities and components
- `architecture.txt` - System design and communication flow
- `configuration.txt` - Config file guide and Claude Desktop setup
- `installation.txt` - Setup instructions
- `tools.txt` - Complete MCP tools reference
- `workflow.txt` - Master Claude workflow and example sessions
- `security.txt` - Security layers and best practices
- `troubleshooting.txt` - Common issues and solutions

`idea.md` contains the full architecture specification (~30KB).

## Code Standards (for implementation)

- Files under 500 LOC, following SOLID/SRP principles
- Fully typed Python with no type errors
- All code tested and linted
- Security: path validation, command blocklist, rate limiting on all tools
