# Multi-PC Gaming Agent Architecture

## Master Claude + MCP Server Fleet for Automated Game Leveling

---

## Executive Summary

This document describes a distributed architecture where a **Master Claude** (smart orchestrator) controls multiple **remote PCs** through **MCP (Model Context Protocol) servers**. Each PC runs a local vision model + PyAutoGUI to execute game actions. The Master Claude can simultaneously level up multiple game accounts across different machines.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MASTER CLAUDE                                      │
│                    (Claude Desktop / Claude.ai / API)                        │
│                                                                              │
│   • High-level strategy & planning                                           │
│   • Decides WHAT to do for each account                                      │
│   • Monitors progress across all PCs                                         │
│   • Handles complex decision making                                          │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │
                              │ MCP Protocol (JSON-RPC over HTTP/SSE)
                              │
        ┌─────────────────────┼─────────────────────┬─────────────────────┐
        │                     │                     │                     │
        ▼                     ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   PC #1       │     │   PC #2       │     │   PC #3       │     │   PC #N       │
│   (Gaming)    │     │   (Gaming)    │     │   (Gaming)    │     │   (Gaming)    │
│               │     │               │     │               │     │               │
│ MCP Server    │     │ MCP Server    │     │ MCP Server    │     │ MCP Server    │
│ :8765         │     │ :8765         │     │ :8765         │     │ :8765         │
│               │     │               │     │               │     │               │
│ ┌───────────┐ │     │ ┌───────────┐ │     │ ┌───────────┐ │     │ ┌───────────┐ │
│ │Local VLM  │ │     │ │Local VLM  │ │     │ │Local VLM  │ │     │ │Local VLM  │ │
│ │(Optional) │ │     │ │(Optional) │ │     │ │(Optional) │ │     │ │(Optional) │ │
│ └───────────┘ │     │ └───────────┘ │     │ └───────────┘ │     │ └───────────┘ │
│               │     │               │     │               │     │               │
│ ┌───────────┐ │     │ ┌───────────┐ │     │ ┌───────────┐ │     │ ┌───────────┐ │
│ │ PyAutoGUI │ │     │ │ PyAutoGUI │ │     │ │ PyAutoGUI │ │     │ │ PyAutoGUI │ │
│ └───────────┘ │     │ └───────────┘ │     │ └───────────┘ │     │ └───────────┘ │
│               │     │               │     │               │     │               │
│   [Game 1]    │     │   [Game 2]    │     │   [Game 3]    │     │   [Game N]    │
│   Account A   │     │   Account B   │     │   Account C   │     │   Account N   │
└───────────────┘     └───────────────┘     └───────────────┘     └───────────────┘
```

---

## MCP (Model Context Protocol) Explained

### What is MCP?

MCP is an **open protocol by Anthropic** (now under Linux Foundation) that standardizes how AI applications connect to external tools and data sources. Think of it as **"USB-C for AI"** — a universal interface.

### Key Concepts

| Component | Description |
|-----------|-------------|
| **Host** | The AI application (Claude Desktop, your app) that coordinates everything |
| **Client** | Lives inside the Host, manages connection to one MCP Server |
| **Server** | Exposes tools, resources, and prompts to the AI |
| **Transport** | How messages travel: `stdio` (local) or `HTTP/SSE` (remote) |

### MCP Message Flow

```
┌──────────────────┐                              ┌──────────────────┐
│   MCP Client     │                              │   MCP Server     │
│   (in Claude)    │                              │   (on Remote PC) │
└────────┬─────────┘                              └────────┬─────────┘
         │                                                  │
         │  1. initialize (capabilities exchange)           │
         │ ─────────────────────────────────────────────▶  │
         │                                                  │
         │  2. initialized (server capabilities)            │
         │ ◀─────────────────────────────────────────────  │
         │                                                  │
         │  3. tools/list (what can you do?)                │
         │ ─────────────────────────────────────────────▶  │
         │                                                  │
         │  4. tools list response                          │
         │ ◀─────────────────────────────────────────────  │
         │                                                  │
         │  5. tools/call { name: "screenshot" }            │
         │ ─────────────────────────────────────────────▶  │
         │                                                  │
         │  6. result { image: base64... }                  │
         │ ◀─────────────────────────────────────────────  │
         │                                                  │
```

### Why MCP for This Project?

1. **Standardized Interface** — Same protocol for all PCs
2. **Claude Native Support** — Claude Desktop can connect to MCP servers directly
3. **Tool Discovery** — Claude automatically learns available tools
4. **Bidirectional** — Server can request info from Claude (sampling, elicitation)
5. **Security** — Built-in auth patterns (OAuth, API keys)

---

## MCP Server Design for Gaming PC

Each gaming PC runs an MCP server that exposes these tools:

### Tools Exposed

| Tool Name | Description | Parameters | Returns |
|-----------|-------------|------------|---------|
| `screenshot` | Capture current screen | `monitor?: int` | Base64 PNG image |
| `click` | Click at coordinates | `x: int, y: int, button?: str` | Success/failure |
| `double_click` | Double click | `x: int, y: int` | Success/failure |
| `move_to` | Move mouse | `x: int, y: int, duration?: float` | Success/failure |
| `drag_to` | Drag from current to target | `x: int, y: int, duration?: float` | Success/failure |
| `type_text` | Type text | `text: str, interval?: float` | Success/failure |
| `press_key` | Press keyboard key | `key: str, modifiers?: list` | Success/failure |
| `hotkey` | Press key combination | `keys: list` | Success/failure |
| `scroll` | Scroll wheel | `clicks: int, x?: int, y?: int` | Success/failure |
| `execute_command` | Run terminal/shell command | `command: str, timeout?: int` | stdout, stderr, exit_code |
| `read_file` | Read file contents | `path: str` | File contents (text or base64) |
| `write_file` | Write file | `path: str, content: str, binary?: bool` | Success/failure |
| `list_files` | List directory | `path: str` | List of files |
| `upload_file` | Upload file to PC | `path: str, content: str, binary?: bool` | Success/failure |
| `download_file` | Download file from PC | `path: str` | Base64 content |
| `get_screen_size` | Get screen dimensions | None | `{width, height}` |
| `get_mouse_position` | Current mouse location | None | `{x, y}` |
| `analyze_screen` | Use local VLM to analyze | `prompt: str` | VLM response |
| `get_system_info` | CPU, RAM, GPU usage | None | System stats |
| `list_windows` | List open windows | None | Window titles and handles |
| `focus_window` | Bring window to front | `title: str` or `handle: int` | Success/failure |

### Resources Exposed

| Resource URI | Description |
|--------------|-------------|
| `screen://current` | Live screenshot (refreshes each access) |
| `file:///{path}` | File system access |
| `system://info` | System information |
| `game://status` | Current game state (custom) |

---

## Installation & Setup Flow

### One-Line Install (Goal)

**Windows (PowerShell):**
```powershell
irm https://your-domain.com/install.ps1 | iex
```

**Linux/Mac:**
```bash
curl -fsSL https://your-domain.com/install.sh | bash
```

### What the Installer Does

```
┌─────────────────────────────────────────────────────────────────┐
│                     INSTALLATION FLOW                            │
└─────────────────────────────────────────────────────────────────┘

1. Check Python 3.10+ installed
   └── If not: download and install Python

2. Create virtual environment
   └── ~/.gaming-agent/venv/

3. Install dependencies
   └── pip install: pyautogui, mcp, pillow, fastapi, uvicorn, 
                    screeninfo, psutil, ollama (optional)

4. Download MCP server script
   └── ~/.gaming-agent/server.py

5. Prompt for configuration
   ├── Password/API Key: ________
   ├── Port (default 8765): ________
   ├── Enable local VLM? [y/N]: ________
   └── VLM model (if yes): qwen2.5-vl:3b

6. Create system service
   ├── Windows: Creates scheduled task (runs at startup)
   └── Linux: Creates systemd service

7. Configure firewall
   └── Opens port 8765 (or custom)

8. Generate connection config
   └── Outputs MCP config JSON for Claude Desktop

9. Start the server
   └── Server running at http://0.0.0.0:8765
```

### Configuration File

After install, config lives at `~/.gaming-agent/config.json`:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8765,
    "password": "your-secure-password-here"
  },
  "vlm": {
    "enabled": true,
    "provider": "ollama",
    "model": "qwen2.5-vl:3b",
    "endpoint": "http://localhost:11434"
  },
  "security": {
    "allowed_paths": ["/home/user/games", "C:\\Games"],
    "blocked_commands": ["rm -rf", "format", "del /f"],
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

---

## Authentication & Security

### Password-Based Auth Flow

```
┌──────────────┐                              ┌──────────────┐
│    Claude    │                              │  MCP Server  │
└──────┬───────┘                              └──────┬───────┘
       │                                              │
       │  1. HTTP Request with Authorization header   │
       │     Authorization: Bearer <password>         │
       │ ─────────────────────────────────────────▶  │
       │                                              │
       │  2. Server validates password                │
       │     ✓ Match: proceed                         │
       │     ✗ No match: 401 Unauthorized             │
       │                                              │
       │  3. If valid, establish SSE connection       │
       │ ◀─────────────────────────────────────────  │
       │                                              │
```

### Security Layers

1. **Password/Token** — Required for all connections
2. **Path Restrictions** — Limit file access to specific directories
3. **Command Blocklist** — Prevent dangerous shell commands
4. **Rate Limiting** — Max requests per minute
5. **Audit Logging** — Log all actions with timestamps
6. **TLS/HTTPS** — Encrypt all traffic (optional but recommended)

---

## Workflow: Leveling Multiple Accounts

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MASTER CLAUDE WORKFLOW                                │
└─────────────────────────────────────────────────────────────────────────────┘

STEP 1: Initialize All Connections
────────────────────────────────────
Master Claude connects to all MCP servers:
  • PC1 (192.168.1.10:8765) — Account: PlayerOne
  • PC2 (192.168.1.11:8765) — Account: PlayerTwo  
  • PC3 (192.168.1.12:8765) — Account: PlayerThree

STEP 2: Check Current State (Parallel)
────────────────────────────────────────
For each PC, Claude calls:
  screenshot() → Gets current game screen
  analyze_screen("What level is the character? What's the current task?")
  
Results:
  • PC1: Level 15, doing quest "Dragon Slayer"
  • PC2: Level 8, idle in town
  • PC3: Level 22, in combat

STEP 3: Generate Instructions (Smart Model)
────────────────────────────────────────────
Claude analyzes all states and decides:
  • PC1: "Continue quest, next objective is at coordinates..."
  • PC2: "Accept quest from NPC, navigate to quest giver..."
  • PC3: "Use skill rotation: Q, W, E, wait, repeat..."

STEP 4: Execute Actions (Batch)
───────────────────────────────
Claude sends tool calls to each PC:

PC1: click(500, 300) → move_to(800, 600) → click(800, 600)
PC2: click(100, 200) → type_text("Accept") → press_key("enter")
PC3: hotkey(["q"]) → wait(0.5) → hotkey(["w"]) → hotkey(["e"])

STEP 5: Verify & Loop
─────────────────────
After actions complete:
  screenshot() → Check if action succeeded
  If failed: retry with different approach
  If succeeded: continue to next action

STEP 6: Report Progress
───────────────────────
Every N minutes, Claude generates report:
  "PC1: Gained 2 levels (15→17), completed 3 quests"
  "PC2: Gained 5 levels (8→13), completed tutorial"
  "PC3: Gained 1 level (22→23), farmed 500 gold"
```

### Detailed Action Sequence

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SINGLE PC ACTION SEQUENCE                                │
└─────────────────────────────────────────────────────────────────────────────┘

USER → MASTER CLAUDE: "Level up the account on PC1"

MASTER CLAUDE:
│
├─► [TOOL CALL] screenshot @ PC1
│   └─► Returns: base64 image of game screen
│
├─► [ANALYZE] Claude looks at screenshot
│   └─► Identifies: Menu open, "Play" button at (640, 400)
│
├─► [TOOL CALL] click(640, 400) @ PC1
│   └─► Returns: { success: true }
│
├─► [WAIT] 2 seconds for game to load
│
├─► [TOOL CALL] screenshot @ PC1
│   └─► Returns: base64 image (now in game)
│
├─► [ANALYZE] Claude identifies game state
│   └─► Character at level 15, HP: 80%, in forest area
│   └─► Enemy visible at approximately (300, 250)
│
├─► [DECISION] Attack enemy to gain XP
│
├─► [TOOL CALL] click(300, 250) @ PC1  (target enemy)
│   └─► Returns: { success: true }
│
├─► [TOOL CALL] press_key("1") @ PC1  (use attack skill)
│   └─► Returns: { success: true }
│
├─► [LOOP] Continue until level up detected
│
└─► [REPORT] "Gained 1 level on PC1, now level 16"
```

---

## Architecture Options

### Option A: Claude Does All Vision (Simplest)

```
┌─────────────────────┐
│    Master Claude    │ ◄── Does ALL the thinking
│   (Vision Model)    │     Screenshots sent to Claude
└──────────┬──────────┘     Claude decides actions
           │
           │ MCP
           ▼
┌─────────────────────┐
│   Gaming PC         │
│   MCP Server Only   │ ◄── Dumb executor
│   (No local VLM)    │     Just runs PyAutoGUI commands
└─────────────────────┘

Pros:
  ✓ Simplest setup
  ✓ Best intelligence (Claude is smarter)
  ✓ No GPU needed on gaming PCs

Cons:
  ✗ Higher latency (image upload)
  ✗ More API costs (vision tokens)
  ✗ Requires good internet
```

### Option B: Hybrid (Local VLM for Speed)

```
┌─────────────────────┐
│    Master Claude    │ ◄── High-level decisions
│   (Orchestrator)    │     "Go to quest area and farm"
└──────────┬──────────┘
           │
           │ MCP (instructions)
           ▼
┌─────────────────────┐
│   Gaming PC         │
│   ┌───────────────┐ │
│   │  Local VLM    │ │ ◄── Fast visual processing
│   │  Qwen3-VL-2B  │ │     "Click on enemy at (x,y)"
│   └───────────────┘ │
│   ┌───────────────┐ │
│   │  PyAutoGUI    │ │ ◄── Action execution
│   └───────────────┘ │
└─────────────────────┘

Pros:
  ✓ Much faster (local inference)
  ✓ Lower API costs
  ✓ Works with poor internet

Cons:
  ✗ Needs GPU on gaming PCs
  ✗ More complex setup
  ✗ Local VLM less smart than Claude
```

### Option C: Full Local (Privacy Maximum)

```
┌─────────────────────┐
│   Local Orchestrator│ ◄── Could be Qwen3-72B or similar
│   (Your Server)     │     Running on powerful local machine
└──────────┬──────────┘
           │
           │ MCP
           ▼
┌─────────────────────┐
│   Gaming PCs        │
│   (Local VLMs)      │
└─────────────────────┘

Pros:
  ✓ Complete privacy
  ✓ No API costs
  ✓ No internet required

Cons:
  ✗ Need powerful hardware
  ✗ More maintenance
  ✗ Less capable than Claude
```

---

## Claude Desktop MCP Configuration

To connect Master Claude to your gaming PCs, add this to Claude Desktop's config:

**Location:**
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "gaming-pc-1": {
      "transport": "sse",
      "url": "http://192.168.1.10:8765/mcp",
      "headers": {
        "Authorization": "Bearer your-password-here"
      }
    },
    "gaming-pc-2": {
      "transport": "sse", 
      "url": "http://192.168.1.11:8765/mcp",
      "headers": {
        "Authorization": "Bearer your-password-here"
      }
    },
    "gaming-pc-3": {
      "transport": "sse",
      "url": "http://192.168.1.12:8765/mcp",
      "headers": {
        "Authorization": "Bearer your-password-here"
      }
    }
  }
}
```

---

## Example Conversation with Master Claude

```
USER: 
I have 3 gaming PCs set up. PC1 and PC2 are running Game X, PC3 is running 
Game Y. Level up all accounts to level 20.

MASTER CLAUDE:
I'll check the current status of all three PCs.

[Calling screenshot on gaming-pc-1]
[Calling screenshot on gaming-pc-2]  
[Calling screenshot on gaming-pc-3]

Here's what I see:
• PC1 (Game X): Level 12, currently in the starter zone
• PC2 (Game X): Level 7, at the login screen - needs to log in
• PC3 (Game Y): Level 18, in a dungeon

I'll start the leveling process:

**PC2** needs to log in first. Let me handle that...
[Calling click(640, 300) on gaming-pc-2] - Clicking username field
[Calling type_text("account_name") on gaming-pc-2]
[Calling click(640, 350) on gaming-pc-2] - Clicking password field
[Calling type_text("password123") on gaming-pc-2]
[Calling click(640, 400) on gaming-pc-2] - Clicking Login

**PC1** - I'll move to the next quest zone for better XP...
[Calling click(minimap_coords) on gaming-pc-1]
[Calling analyze_screen("Where is the quest NPC?") on gaming-pc-1]

**PC3** - Almost there! Let me help finish this dungeon...
[Calling hotkey(["1"]) on gaming-pc-3] - Using main attack
[Calling click(enemy_coords) on gaming-pc-3]

I'll continue monitoring and report progress every 10 minutes.

---

[10 minutes later]

Progress Update:
• PC1: Level 12 → 14 (+2 levels) - Completed 2 quests
• PC2: Level 7 → 11 (+4 levels) - Finished tutorial zone  
• PC3: Level 18 → 20 ✓ GOAL REACHED

PC3 has reached level 20! Continuing on PC1 and PC2...
```

---

## File Structure on Gaming PC

```
~/.gaming-agent/
├── config.json              # Server configuration
├── server.py                # Main MCP server
├── requirements.txt         # Python dependencies
├── venv/                    # Virtual environment
├── logs/
│   ├── server.log           # Server logs
│   ├── actions.log          # All actions taken
│   └── errors.log           # Error logs
├── screenshots/
│   └── (temporary screenshots)
└── scripts/
    ├── install.py           # Installation script
    ├── uninstall.py         # Cleanup script
    └── update.py            # Update script
```

---

## Dependencies

### Required (All Platforms)

| Package | Purpose |
|---------|---------|
| `mcp` | MCP protocol implementation |
| `pyautogui` | Mouse/keyboard control |
| `pillow` | Screenshot handling |
| `fastapi` | HTTP server |
| `uvicorn` | ASGI server |
| `screeninfo` | Multi-monitor support |
| `psutil` | System info |

### Optional (For Local VLM)

| Package | Purpose |
|---------|---------|
| `ollama` | Local model serving |
| `torch` | ML framework |
| `transformers` | Model loading |

### Platform-Specific

| Platform | Additional |
|----------|------------|
| Windows | `pywin32` (window management) |
| Linux | `python3-xlib` (X11 support) |
| Mac | `pyobjc` (Cocoa bindings) |

---

## Recommended Local VLM Models

| Model | Size | VRAM | Speed | Quality | Best For |
|-------|------|------|-------|---------|----------|
| Moondream 2B | 2B | 4GB | ⚡⚡⚡⚡ | ★★★☆☆ | Fastest, basic UI |
| Qwen2.5-VL-3B | 3B | 6GB | ⚡⚡⚡ | ★★★★☆ | Best balance |
| Qwen3-VL-2B | 2B | 5GB | ⚡⚡⚡⚡ | ★★★★☆ | Latest, GUI-trained |
| Qwen3-VL-4B | 4B | 8GB | ⚡⚡⚡ | ★★★★★ | High quality |
| Gemma 3 4B | 4B | 8GB | ⚡⚡⚡ | ★★★★☆ | Good multilingual |

---

## Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| "Connection refused" | Check firewall, ensure server is running |
| "Unauthorized" | Verify password matches config |
| Screenshots are black | Run with admin/root privileges |
| Mouse not moving | Disable game's mouse lock, check permissions |
| Slow response | Reduce screenshot quality, use local VLM |
| "Port already in use" | Change port in config or kill existing process |

### Testing Connection

```bash
# Test if server is reachable
curl http://192.168.1.10:8765/health

# Test with auth
curl -H "Authorization: Bearer your-password" http://192.168.1.10:8765/mcp
```

---

## Security Considerations

### DO
- Use strong, unique passwords for each PC
- Limit file access to game directories only
- Use a VPN if accessing over internet
- Enable TLS/HTTPS for production
- Regularly rotate passwords

### DON'T
- Expose port directly to internet without VPN
- Use simple passwords like "123456"
- Allow unrestricted command execution
- Give access to system directories
- Run server as root/admin (unless necessary)

---

## Future Enhancements

1. **Web Dashboard** — Monitor all PCs from a browser
2. **Mobile App** — Check progress from phone
3. **Auto-Scaling** — Spin up cloud VMs for more accounts
4. **Recording** — Record sessions for debugging
5. **Macros** — Save and replay action sequences
6. **Game Plugins** — Game-specific optimizations
7. **Anti-Detection** — Human-like mouse movements

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│                    QUICK REFERENCE                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INSTALL:                                                        │
│    Windows: irm https://domain.com/install.ps1 | iex            │
│    Linux:   curl -fsSL https://domain.com/install.sh | bash     │
│                                                                  │
│  CONFIG FILE:  ~/.gaming-agent/config.json                      │
│                                                                  │
│  START SERVER:                                                   │
│    Windows: gaming-agent start                                   │
│    Linux:   systemctl start gaming-agent                        │
│                                                                  │
│  STOP SERVER:                                                    │
│    Windows: gaming-agent stop                                    │
│    Linux:   systemctl stop gaming-agent                         │
│                                                                  │
│  VIEW LOGS:    ~/.gaming-agent/logs/server.log                  │
│                                                                  │
│  DEFAULT PORT: 8765                                              │
│                                                                  │
│  MCP TOOLS:                                                      │
│    screenshot, click, type_text, press_key, hotkey,             │
│    execute_command, read_file, write_file, analyze_screen       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Appendix: MCP Protocol Details

### JSON-RPC Message Format

```json
// Request
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "screenshot",
    "arguments": {}
  }
}

// Response
{
  "jsonrpc": "2.0", 
  "id": 1,
  "result": {
    "content": [
      {
        "type": "image",
        "data": "base64-encoded-png...",
        "mimeType": "image/png"
      }
    ]
  }
}
```

### Tool Definition Schema

```json
{
  "name": "click",
  "description": "Click at screen coordinates",
  "inputSchema": {
    "type": "object",
    "properties": {
      "x": { "type": "integer", "description": "X coordinate" },
      "y": { "type": "integer", "description": "Y coordinate" },
      "button": { 
        "type": "string", 
        "enum": ["left", "right", "middle"],
        "default": "left"
      }
    },
    "required": ["x", "y"]
  }
}
```

---

*Document Version: 1.0*  
*Last Updated: January 2026*