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

- **24 MCP Tools**: Screen capture, mouse/keyboard control, file operations, system commands, workflow automation
- **Workflow Automation**: Chain multiple actions into single commands with `run_workflow` and `demo_terminal_workflow`
- **Multi-Monitor Support**: Target specific monitors for screenshots and actions
- **Dual Transport Modes**: HTTP/SSE for remote control, stdio for local clients
- **Optional Local VLM**: Use Ollama (Qwen2.5-VL, Moondream) for fast local screen analysis
- **Security-First**: Bearer token auth, path restrictions, command blocklist, audit logging
- **Cross-Platform**: Windows, Linux, macOS with auto-detection

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

The server supports two transport modes:

**HTTP/SSE Transport (Recommended for Remote Control):**
```bash
gaming-agent serve --transport http --port 8765 --password your-secret-password
```

**Stdio Transport (For Local MCP Clients):**
```bash
gaming-agent serve --transport stdio
```

### Connect from Claude Desktop

**For HTTP/SSE Transport:**

Add to your Claude Desktop config (`~/.config/claude/claude_desktop_config.json` on Linux, `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

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

**For Stdio Transport:**

```json
{
  "mcpServers": {
    "gaming-pc": {
      "command": "gaming-agent",
      "args": ["serve", "--transport", "stdio"]
    }
  }
}
```

### Quick Test

Test the complete automation capability with a single command:

```bash
# Start the server
gaming-agent serve --transport http --password test123

# In Claude Desktop (after connecting), ask:
"Use the demo_terminal_workflow tool to open a terminal, type 'echo hello world', and close it"
```

This will:
1. ✓ Auto-detect your terminal (gnome-terminal, konsole, xterm, Terminal.app, cmd)
2. ✓ Open a new terminal window
3. ✓ Type "echo hello world"
4. ✓ Press Enter to execute
5. ✓ Capture a screenshot for verification
6. ✓ Close the terminal with the appropriate hotkey

## Available Tools

**Total: 24 MCP Tools**

### Workflow Tools (New!)
| Tool | Description |
|------|-------------|
| `run_workflow` | Execute a sequence of tool actions with optional delays |
| `demo_terminal_workflow` | Complete demo: open terminal, type command, execute, screenshot, close |

### Screen Tools
| Tool | Description |
|------|-------------|
| `screenshot` | Capture current screen (returns base64 PNG) |
| `get_screen_size` | Get screen dimensions |
| `analyze_screen` | Use local VLM to analyze screen content (requires Ollama) |

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

## Workflow Automation

### `run_workflow` - Composite Command Execution

Execute multiple tools in sequence with a single command. Perfect for complex automation tasks.

**Example: Open terminal and run command**
```json
{
  "steps": [
    {
      "tool": "execute_command",
      "args": {"command": "gnome-terminal"},
      "wait_ms": 1500,
      "description": "Open terminal"
    },
    {
      "tool": "type_text",
      "args": {"text": "ls -la"},
      "wait_ms": 200,
      "description": "Type command"
    },
    {
      "tool": "press_key",
      "args": {"key": "enter"},
      "wait_ms": 1000,
      "description": "Execute command"
    },
    {
      "tool": "screenshot",
      "args": {},
      "description": "Capture result"
    }
  ]
}
```

**Step Fields:**
- `tool` (required): Name of the tool to execute
- `args` (optional): Arguments to pass to the tool
- `wait_ms` (optional): Milliseconds to wait after this step
- `description` (optional): Human-readable step description
- `continue_on_error` (optional): Continue workflow if this step fails

**Returns:**
```json
{
  "success": true,
  "total_steps": 4,
  "completed_steps": 4,
  "failed_step": null,
  "results": [...],
  "total_time_ms": 3523,
  "error": null
}
```

### `demo_terminal_workflow` - Ready-Made Terminal Demo

A convenience tool that demonstrates the full automation capability in one call.

**Usage:**
```json
{
  "text": "echo hello world",
  "terminal_wait_ms": 2000,
  "post_type_wait_ms": 500,
  "post_enter_wait_ms": 1000,
  "capture_screenshot": true,
  "close_terminal": true
}
```

**What it does:**
1. Auto-detects platform terminal (gnome-terminal, konsole, xterm, Terminal.app, cmd)
2. Opens the terminal application
3. Waits for terminal to fully load
4. Types the provided command
5. Presses Enter to execute
6. Waits for command output
7. Captures screenshot for verification (optional)
8. Closes terminal with platform-appropriate hotkey (optional)

**Returns:**
```json
{
  "success": true,
  "terminal_command": "gnome-terminal",
  "platform": "Linux",
  "text_typed": "echo hello world",
  "screenshot": {"success": true, "image": "...", ...},
  "steps_completed": ["detect_terminal", "open_terminal", "wait_for_terminal",
                      "type_text", "press_enter", "capture_screenshot",
                      "close_terminal"],
  "total_time_ms": 4523,
  "error": null
}
```

**Platform Support:**
- **Linux**: gnome-terminal, konsole, xfce4-terminal, mate-terminal, tilix, terminator, xterm
- **macOS**: Terminal.app
- **Windows**: cmd.exe

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
    "model": "qwen2.5-vl:3b",
    "endpoint": "http://localhost:11434"
  },
  "security": {
    "allowed_paths": ["/home/user/games", "C:\\Games"],
    "blocked_commands": ["rm -rf", "format", "del /f"],
    "max_command_timeout": 30
  }
}
```

### Enabling VLM (Optional)

To use the `analyze_screen` tool with local vision models:

1. **Install Ollama** (if not already installed):
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. **Pull a vision model**:
   ```bash
   ollama pull qwen2.5-vl:3b  # Lightweight, fast
   # or
   ollama pull moondream      # Alternative
   ```

3. **Install VLM dependencies**:
   ```bash
   pip install ai-gaming-agent[vlm]
   ```

4. **Enable in config** (`~/.gaming-agent/config.json`):
   ```json
   {
     "vlm": {
       "enabled": true,
       "provider": "ollama",
       "model": "qwen2.5-vl:3b",
       "endpoint": "http://localhost:11434"
     }
   }
   ```

5. **Use in workflows**:
   ```json
   {
     "tool": "analyze_screen",
     "args": {
       "prompt": "What is the current health percentage?"
     }
   }
   ```

## Deployment Options

### Option A: Claude Does All Vision (Simplest)
- Claude analyzes all screenshots
- Gaming PCs are simple executors
- No GPU needed on gaming PCs
- Use HTTP/SSE transport with Bearer auth

### Option B: Hybrid with Local VLM (Recommended)
- Claude for high-level decisions and orchestration
- Local VLM (Qwen2.5-VL, Moondream) for fast visual processing
- Best balance of speed and intelligence
- Reduces API costs and latency

### Option C: Full Local (Privacy)
- Local orchestrator (e.g., Qwen3-72B via Ollama)
- No cloud APIs, complete privacy
- Requires powerful hardware (GPU recommended)
- Use stdio transport for local control

## Practical Examples

### Example 1: Terminal Automation
```python
# Ask Claude: "Run the demo_terminal_workflow with the command 'uname -a'"
# Result: Opens terminal, runs command, captures output, closes
```

### Example 2: Multi-Step Workflow
```python
# Ask Claude: "Create a workflow that:
# 1. Opens a file browser
# 2. Navigates to Downloads
# 3. Takes a screenshot
# 4. Closes the window"

# Claude will use run_workflow with execute_command, type_text, screenshot, hotkey
```

### Example 3: Game Automation with VLM
```python
# Ask Claude: "Use analyze_screen to check if the game menu is visible,
# then click the 'Start Game' button at coordinates you detect"

# Claude will:
# 1. Call analyze_screen with prompt "Is there a Start Game button? Where?"
# 2. Use VLM response to determine coordinates
# 3. Call click tool with detected coordinates
```

### Example 4: Batch File Operations
```python
# Ask Claude: "Create a workflow that backs up all .save files from
# C:\Games\MyGame to C:\Backups\saves-{date}"

# Claude will use run_workflow with list_files, read_file, write_file
```

## Security

- Always use strong, unique passwords (min 16 chars, random)
- Limit file access to game directories only in `allowed_paths`
- Use a VPN if accessing over internet (never expose to public)
- Enable TLS/HTTPS for production (use reverse proxy like nginx)
- Regularly rotate passwords (weekly for high-security environments)
- Monitor `~/.gaming-agent/audit.log` for suspicious activity
- Set appropriate `max_command_timeout` to prevent runaway processes

## Development

```bash
# Install with uv (recommended)
uv sync --extra dev

# Or with pip
pip install -e ".[dev]"

# Lint
uv run ruff check src tests

# Run unit tests
uv run pytest tests/ --ignore=tests/integration -v
```

## Testing

### Unit Tests (CI)

Unit tests run in CI on every push/PR. They test configuration, file operations, and tool interfaces without requiring a display.

```bash
# Run unit tests only
uv run pytest tests/ --ignore=tests/integration -v
```

### Integration Tests (Local Only)

Integration tests perform **real GUI automation** and require:
- A real display (X11, Wayland, Windows, macOS)
- `tesseract-ocr` for OCR verification
- pyautogui working with your display

**These tests CANNOT run in CI** because they need a real desktop environment.

```bash
# Install integration test dependencies
uv sync --extra integration

# Install tesseract (Linux)
sudo apt install tesseract-ocr

# Install tesseract (macOS)
brew install tesseract

# Run integration tests locally
uv run pytest tests/integration -v
```

#### What Integration Tests Do

| Test | Description |
|------|-------------|
| `test_screenshot_returns_image` | Captures real screen content |
| `test_ocr_screen_content` | Uses OCR to read text from screen |
| `test_mouse_move` | Moves mouse cursor to position |
| `test_mouse_click` | Performs real mouse click |
| `test_type_text` | Types actual text |
| `test_terminal_workflow` | Opens terminal, types command, closes |
| `test_terminal_with_ocr_verification` | Opens terminal, runs command, verifies output with OCR |
| `test_batch_gui_operations` | Runs 7 GUI operations in sequence |

#### Terminal Workflow Test

The most comprehensive test opens a terminal, types a command, and verifies the output:

```python
# What the test does:
1. Opens system terminal (gnome-terminal, konsole, xterm, etc.)
2. Types: echo "AGENT_TEST_abc12345"
3. Presses Enter
4. Takes screenshot
5. Runs OCR on screenshot
6. Verifies "AGENT_TEST_abc12345" appears in OCR output
7. Closes terminal with Alt+F4
```

### CI Configuration

CI runs on GitHub Actions with Python 3.12 only:

```yaml
# .github/workflows/ci.yml
- Checkout code
- Install uv
- Install Python 3.12
- Install system deps (xvfb, scrot, python3-tk)
- Run ruff lint
- Run unit tests (integration tests excluded)
```

Integration tests are auto-skipped in CI via the `CI=true` environment variable.

## License

MIT
