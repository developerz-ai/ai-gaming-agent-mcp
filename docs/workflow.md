# Workflow Guide

A comprehensive guide to creating and executing automation workflows with the AI Gaming Agent MCP Server.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Workflow Concepts](#workflow-concepts)
3. [run_workflow Tool](#run_workflow-tool)
4. [demo_terminal_workflow Tool](#demo_terminal_workflow-tool)
5. [Building Complex Workflows](#building-complex-workflows)
6. [Best Practices](#best-practices)
7. [Error Handling](#error-handling)
8. [Performance Optimization](#performance-optimization)
9. [Practical Examples](#practical-examples)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

### The Simplest Workflow: Terminal Demo

The easiest way to test workflows is with the built-in demo:

```json
{
  "tool": "demo_terminal_workflow",
  "args": {
    "text": "echo hello world"
  }
}
```

This single command:
1. ✓ Opens a terminal (auto-detects your OS)
2. ✓ Types your command
3. ✓ Executes it (presses Enter)
4. ✓ Captures screenshot
5. ✓ Closes the terminal

Perfect for testing and demonstration purposes.

### Multi-Step Workflow: Custom Sequence

For more complex tasks, chain multiple actions:

```json
{
  "tool": "run_workflow",
  "args": {
    "steps": [
      {
        "tool": "execute_command",
        "args": {"command": "gnome-terminal"},
        "wait_ms": 1500
      },
      {
        "tool": "type_text",
        "args": {"text": "python script.py"},
        "wait_ms": 200
      },
      {
        "tool": "press_key",
        "args": {"key": "enter"},
        "wait_ms": 2000
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

## Workflow Concepts

### What is a Workflow?

A workflow is a **sequence of automated actions** that execute in order to accomplish a task. Instead of sending one tool call at a time, you bundle multiple actions together and send them all at once.

### Why Use Workflows?

**Efficiency:**
- Reduces network roundtrips
- All steps execute with minimal delay
- Perfect for batch operations

**Reliability:**
- Waits between steps ensure UI elements load
- Optional continue-on-error for resilience
- Detailed logging of each step

**Automation:**
- Complex tasks from simple command
- Reproducible sequences
- Easy to share and modify

### Workflow Types

| Type | Use Case | Complexity |
|------|----------|-----------|
| **Built-in Demo** | Testing, proof-of-concept | Minimal |
| **Simple Sequence** | Open app, perform action, close | Low |
| **Conditional Loop** | Repeat until condition met | Medium |
| **Multi-App** | Chain operations across multiple apps | High |
| **Custom Script** | Full control, advanced logic | Very High |

---

## run_workflow Tool

The `run_workflow` tool is your primary tool for creating automation sequences.

### Basic Structure

```json
{
  "tool": "run_workflow",
  "args": {
    "steps": [
      { "tool": "...", "args": {...} },
      { "tool": "...", "args": {...} }
    ]
  }
}
```

### Step Definition

Each step in a workflow is defined as:

```json
{
  "tool": "screenshot",           // (required) Tool name to execute
  "args": {                        // (optional) Arguments to pass
    "key": "value"
  },
  "wait_ms": 500,                  // (optional) Milliseconds to wait after
  "description": "Take screenshot", // (optional) Human-readable description
  "continue_on_error": false       // (optional) Continue if this step fails
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tool` | string | Yes | Name of the MCP tool to execute (e.g., "click", "type_text") |
| `args` | object | No | Arguments specific to the tool (varies by tool) |
| `wait_ms` | number | No | Milliseconds to wait after step completes (default: 0) |
| `description` | string | No | Human-readable description for logging |
| `continue_on_error` | boolean | No | Continue executing next step even if this fails (default: false) |

### Return Format

When a workflow completes, you get a detailed response:

```json
{
  "success": true,
  "total_steps": 4,
  "completed_steps": 4,
  "failed_step": null,
  "total_time_ms": 3523,
  "error": null,
  "results": [
    {
      "step": 0,
      "tool": "execute_command",
      "success": true,
      "result": {...},
      "time_ms": 1500
    },
    // ... more steps ...
  ]
}
```

### Available Tools in Workflows

These are the tools you can use inside `run_workflow`:

#### Screen Tools
- `screenshot` - Capture screen
- `get_screen_size` - Get display dimensions
- `analyze_screen` - Use VLM to analyze content

#### Mouse Tools
- `click` - Click at coordinates
- `double_click` - Double-click at coordinates
- `move_to` - Move mouse cursor
- `drag_to` - Drag from current position
- `scroll` - Scroll mouse wheel
- `get_mouse_position` - Get cursor location

#### Keyboard Tools
- `type_text` - Type a string (supports fast paste mode via `use_paste` parameter)
- `press_key` - Press a key
- `hotkey` - Key combination (e.g., "ctrl+c")

#### File Tools
- `read_file` - Read file contents
- `write_file` - Write content to file
- `list_files` - List directory
- `upload_file` - Upload file to PC
- `download_file` - Download file from PC

#### System Tools
- `execute_command` - Run shell command
- `get_system_info` - Get system info
- `list_windows` - List open windows
- `focus_window` - Bring window to front

---

## demo_terminal_workflow Tool

A convenience tool that automates the complete terminal workflow in one call.

### Usage

```json
{
  "tool": "demo_terminal_workflow",
  "args": {
    "text": "echo hello world",
    "terminal_wait_ms": 2000,
    "post_type_wait_ms": 500,
    "post_enter_wait_ms": 1000,
    "capture_screenshot": true,
    "close_terminal": true
  }
}
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | string | "echo hello world" | Command to type and execute |
| `terminal_wait_ms` | number | 2000 | Wait time for terminal to open |
| `post_type_wait_ms` | number | 500 | Wait after typing command |
| `post_enter_wait_ms` | number | 1000 | Wait after pressing Enter |
| `capture_screenshot` | boolean | true | Capture screenshot after execution |
| `close_terminal` | boolean | true | Close terminal when done |

### Platform Support

Automatically detects and uses the appropriate terminal:

**Linux:**
- gnome-terminal (GNOME)
- konsole (KDE)
- xfce4-terminal (Xfce)
- mate-terminal (MATE)
- tilix (Tilix)
- terminator (Terminator)
- xterm (Fallback)

**macOS:**
- Terminal.app

**Windows:**
- cmd.exe

### Return Format

```json
{
  "success": true,
  "platform": "Linux",
  "terminal_command": "gnome-terminal",
  "text_typed": "echo hello world",
  "screenshot": {
    "success": true,
    "image": "base64_image_data...",
    "size": {"width": 1920, "height": 1080}
  },
  "steps_completed": [
    "detect_terminal",
    "open_terminal",
    "wait_for_terminal",
    "type_text",
    "press_enter",
    "capture_screenshot",
    "close_terminal"
  ],
  "total_time_ms": 4523,
  "error": null
}
```

---

## Building Complex Workflows

### Pattern 1: Open → Perform → Close

Execute an action on an application then close it:

```json
{
  "tool": "run_workflow",
  "args": {
    "steps": [
      {
        "tool": "execute_command",
        "args": {"command": "nautilus /home/user/Documents"},
        "wait_ms": 2000,
        "description": "Open file browser"
      },
      {
        "tool": "screenshot",
        "args": {},
        "wait_ms": 1000,
        "description": "Verify window opened"
      },
      {
        "tool": "hotkey",
        "args": {"keys": ["alt", "F4"]},
        "description": "Close window"
      }
    ]
  }
}
```

### Pattern 2: Click Sequence (Menu Navigation)

Navigate through menus with multiple clicks:

```json
{
  "tool": "run_workflow",
  "args": {
    "steps": [
      {
        "tool": "click",
        "args": {"x": 100, "y": 50},
        "wait_ms": 300,
        "description": "Click File menu"
      },
      {
        "tool": "click",
        "args": {"x": 120, "y": 100},
        "wait_ms": 300,
        "description": "Click Save option"
      },
      {
        "tool": "screenshot",
        "args": {},
        "description": "Verify save dialog"
      }
    ]
  }
}
```

### Pattern 3: Type & Submit (Form Filling)

Fill out a form and submit:

```json
{
  "tool": "run_workflow",
  "args": {
    "steps": [
      {
        "tool": "click",
        "args": {"x": 400, "y": 300},
        "wait_ms": 200,
        "description": "Focus username field"
      },
      {
        "tool": "type_text",
        "args": {"text": "user@example.com"},
        "wait_ms": 200,
        "description": "Type username"
      },
      {
        "tool": "press_key",
        "args": {"key": "tab"},
        "wait_ms": 200,
        "description": "Move to password field"
      },
      {
        "tool": "type_text",
        "args": {"text": "password123"},
        "wait_ms": 200,
        "description": "Type password"
      },
      {
        "tool": "press_key",
        "args": {"key": "return"},
        "wait_ms": 2000,
        "description": "Submit form"
      },
      {
        "tool": "screenshot",
        "args": {},
        "description": "Verify login success"
      }
    ]
  }
}
```

### Pattern 4: Drag & Drop

Perform drag and drop operations:

```json
{
  "tool": "run_workflow",
  "args": {
    "steps": [
      {
        "tool": "move_to",
        "args": {"x": 200, "y": 300},
        "description": "Position at drag source"
      },
      {
        "tool": "drag_to",
        "args": {"x": 600, "y": 400},
        "wait_ms": 500,
        "description": "Drag to destination"
      },
      {
        "tool": "screenshot",
        "args": {},
        "description": "Verify drop completed"
      }
    ]
  }
}
```

### Pattern 5: Error Recovery

Use `continue_on_error` for resilient workflows:

```json
{
  "tool": "run_workflow",
  "args": {
    "steps": [
      {
        "tool": "click",
        "args": {"x": 300, "y": 300},
        "wait_ms": 1000,
        "continue_on_error": true,
        "description": "Try clicking primary location"
      },
      {
        "tool": "click",
        "args": {"x": 310, "y": 310},
        "continue_on_error": false,
        "description": "Click alternative location if above failed"
      }
    ]
  }
}
```

### Pattern 6: Conditional Branching (with VLM)

Use `analyze_screen` to make decisions:

```json
{
  "tool": "run_workflow",
  "args": {
    "steps": [
      {
        "tool": "screenshot",
        "args": {},
        "description": "Get current screen"
      },
      {
        "tool": "analyze_screen",
        "args": {"prompt": "Is the login dialog visible?"},
        "wait_ms": 500,
        "description": "Check if login needed"
      }
    ]
  }
}
```

---

## Best Practices

### 1. Use Descriptive Step Descriptions

```json
// ✓ Good - Clear what's happening
{
  "description": "Click the 'Save' button in the File menu"
}

// ✗ Bad - Vague
{
  "description": "Click"
}
```

### 2. Set Appropriate Wait Times

```json
// ✓ Good - Realistic wait times based on operation
{
  "tool": "execute_command",
  "args": {"command": "libreoffice --calc myfile.xlsx"},
  "wait_ms": 3000  // App takes time to start
}

// ✗ Bad - Too short, action may fail
{
  "tool": "execute_command",
  "args": {"command": "libreoffice --calc myfile.xlsx"},
  "wait_ms": 100
}
```

### 3. Use Fast Paste for Long Text Input

For typing long strings (passwords, code, multiline text), use the `use_paste` option for dramatically faster input:

```json
// ✓ Good - Fast paste for long text (microseconds)
{
  "tool": "type_text",
  "args": {
    "text": "def calculate_fibonacci(n):\n    if n <= 1:\n        return n\n    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)",
    "use_paste": true
  },
  "wait_ms": 300,
  "description": "Paste long Python code"
}

// ✗ Slower - Character-by-character typing
{
  "tool": "type_text",
  "args": {
    "text": "def calculate_fibonacci(n):\n    if n <= 1:\n        return n\n    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)",
    "interval": 0.01
  },
  "wait_ms": 300,
  "description": "Type long Python code character by character"
}
```

**When to use `use_paste`:**
- Long text (>50 characters)
- Passwords or sensitive data (faster = less visual exposure)
- Multiline code or configuration
- Time-critical workflows

**When to use regular typing:**
- Short text (<20 characters)
- Applications with strict clipboard policies
- When clipboard contents must be preserved

### 4. Capture Verification Screenshots

```json
// ✓ Good - Verify each major step
{
  "steps": [
    {"tool": "click", "args": {"x": 100, "y": 100}, "wait_ms": 500},
    {"tool": "screenshot", "args": {}, "description": "Verify click worked"}
  ]
}
```

### 5. Use hotkey for Cross-Platform Keys

```json
// ✓ Good - Works on all platforms
{
  "tool": "hotkey",
  "args": {"keys": ["ctrl", "s"]},
  "description": "Save file"
}

// Might not work on macOS (uses cmd, not ctrl)
{
  "tool": "hotkey",
  "args": {"keys": ["ctrl", "s"]}
}
```

### 6. Keep Workflows Focused

```json
// ✓ Good - Single responsibility
{
  "description": "Open calculator and show result",
  "steps": [
    {"tool": "execute_command", "args": {"command": "gnome-calculator"}},
    {"tool": "screenshot", "args": {}}
  ]
}

// ✗ Bad - Too many unrelated steps
{
  "steps": [
    // Open calculator
    // Play music
    // Check email
    // Edit document
    // ...
  ]
}
```

### 7. Enable Error Recovery for Long Workflows

```json
// ✓ Good - Handle potential failures
{
  "steps": [
    {
      "tool": "click",
      "args": {"x": 500, "y": 300},
      "continue_on_error": true,
      "wait_ms": 1000
    }
  ]
}
```

### 8. Add Pauses Before Screenshot

```json
// ✓ Good - Give UI time to update
{
  "tool": "press_key",
  "args": {"key": "enter"},
  "wait_ms": 1500,  // Wait for animation
  "description": "Submit and wait for page load"
}

// ✗ Bad - Capture before UI updates
{
  "tool": "press_key",
  "args": {"key": "enter"},
  "wait_ms": 100
}
```

---

## Error Handling

### Understanding Failures

Workflows can fail at different points:

1. **Immediate Failure** - Step fails, workflow stops (unless `continue_on_error: true`)
2. **Silent Failure** - Tool returns success but action didn't work (verification screenshot catches this)
3. **Timeout** - Action takes longer than expected

### Debugging Failed Workflows

### Step 1: Check the Response

```json
{
  "success": false,
  "failed_step": 2,
  "error": "Click coordinates out of bounds",
  "results": [
    // Shows results of previous successful steps
  ]
}
```

### Step 2: Verify Coordinates

If a `click` or `move_to` fails:

```json
{
  "tool": "run_workflow",
  "args": {
    "steps": [
      {
        "tool": "get_screen_size",
        "args": {},
        "description": "Check screen dimensions"
      },
      {
        "tool": "screenshot",
        "args": {},
        "description": "Visual verification"
      }
    ]
  }
}
```

### Step 3: Increase Wait Times

If UI element wasn't ready:

```json
// Before (failed)
{"wait_ms": 500}

// After (should succeed)
{"wait_ms": 2000}
```

### Step 4: Use continue_on_error Wisely

```json
{
  "tool": "click",
  "args": {"x": 300, "y": 300},
  "continue_on_error": true,  // Try, but don't stop workflow
  "wait_ms": 1000
}
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Click not working | Wrong coordinates | Use screenshot to verify position |
| Text not appearing | Application didn't focus | Add `focus_window` before `type_text` |
| Command not executing | Terminal not ready | Increase `terminal_wait_ms` |
| Actions stuttering | Waits too short | Increase `wait_ms` values |

---

## Performance Optimization

### Minimize Network Calls

Instead of:
```json
// ✗ Bad - 4 separate API calls
call_tool("screenshot")
call_tool("analyze_screen")
call_tool("click")
call_tool("screenshot")
```

Use:
```json
// ✓ Good - 1 API call with all steps
run_workflow({
  "steps": [...]
})
```

### Batch Operations

```json
{
  "tool": "run_workflow",
  "args": {
    "steps": [
      {"tool": "click", "args": {"x": 100, "y": 100}, "wait_ms": 300},
      {"tool": "click", "args": {"x": 100, "y": 150}, "wait_ms": 300},
      {"tool": "click", "args": {"x": 100, "y": 200}, "wait_ms": 300},
      {"tool": "screenshot", "args": {}}
    ]
  }
}
```

### Parallel Workflows

For multiple PCs, send workflows in parallel:

```python
# Pseudocode: Send to 3 PCs simultaneously
results = await asyncio.gather(
    pc1_mcp.run_workflow(workflow1),
    pc2_mcp.run_workflow(workflow2),
    pc3_mcp.run_workflow(workflow3)
)
```

---

## Practical Examples

### Example 1: Update Game Settings

```json
{
  "tool": "run_workflow",
  "args": {
    "steps": [
      {
        "tool": "execute_command",
        "args": {"command": "steam"},
        "wait_ms": 3000,
        "description": "Launch Steam"
      },
      {
        "tool": "click",
        "args": {"x": 100, "y": 100},
        "wait_ms": 500,
        "description": "Click Settings"
      },
      {
        "tool": "scroll",
        "args": {"dx": 0, "dy": 5},
        "wait_ms": 300,
        "description": "Scroll to graphics"
      },
      {
        "tool": "screenshot",
        "args": {},
        "description": "Capture final state"
      },
      {
        "tool": "hotkey",
        "args": {"keys": ["alt", "F4"]},
        "description": "Close Steam"
      }
    ]
  }
}
```

### Example 2: Backup Save Files

```json
{
  "tool": "run_workflow",
  "args": {
    "steps": [
      {
        "tool": "list_files",
        "args": {"path": "/home/user/.local/share/game/"},
        "description": "List save files"
      },
      {
        "tool": "read_file",
        "args": {"path": "/home/user/.local/share/game/save.dat"},
        "description": "Read save file"
      },
      {
        "tool": "write_file",
        "args": {
          "path": "/home/user/backups/save_backup.dat",
          "content": "..." // The read content
        },
        "description": "Backup save file"
      }
    ]
  }
}
```

### Example 3: Multi-Step Game Automation

```json
{
  "tool": "run_workflow",
  "args": {
    "steps": [
      {
        "tool": "screenshot",
        "args": {},
        "description": "Check current state"
      },
      {
        "tool": "analyze_screen",
        "args": {"prompt": "What buttons are visible?"},
        "description": "Analyze screen with VLM"
      },
      {
        "tool": "click",
        "args": {"x": 960, "y": 540},
        "wait_ms": 1000,
        "description": "Click detected button"
      },
      {
        "tool": "type_text",
        "args": {"text": "my_character_name"},
        "wait_ms": 300,
        "description": "Enter character name"
      },
      {
        "tool": "press_key",
        "args": {"key": "return"},
        "wait_ms": 2000,
        "description": "Confirm entry"
      },
      {
        "tool": "screenshot",
        "args": {},
        "description": "Verify gameplay started"
      }
    ]
  }
}
```

### Example 4: Extract Game Data

```json
{
  "tool": "run_workflow",
  "args": {
    "steps": [
      {
        "tool": "execute_command",
        "args": {"command": "find /home/user/.game -name '*.log' -type f"},
        "wait_ms": 1000,
        "description": "Find log files"
      },
      {
        "tool": "read_file",
        "args": {"path": "/home/user/.game/latest.log"},
        "description": "Read latest log"
      },
      {
        "tool": "execute_command",
        "args": {"command": "grep -i 'level' /home/user/.game/latest.log"},
        "wait_ms": 500,
        "description": "Extract level info"
      }
    ]
  }
}
```

### Example 5: Fast Paste - Enter Long Password

```json
{
  "tool": "run_workflow",
  "args": {
    "steps": [
      {
        "tool": "click",
        "args": {"x": 400, "y": 300},
        "wait_ms": 200,
        "description": "Click password field"
      },
      {
        "tool": "type_text",
        "args": {
          "text": "MySecurePassword123!@#$%^&*()",
          "use_paste": true
        },
        "wait_ms": 200,
        "description": "Paste long password (faster and less exposure)"
      },
      {
        "tool": "press_key",
        "args": {"key": "return"},
        "wait_ms": 2000,
        "description": "Submit login"
      },
      {
        "tool": "screenshot",
        "args": {},
        "description": "Verify login success"
      }
    ]
  }
}
```

### Example 6: Fast Paste - Enter Code in Editor

```json
{
  "tool": "run_workflow",
  "args": {
    "steps": [
      {
        "tool": "execute_command",
        "args": {"command": "gedit /tmp/script.py"},
        "wait_ms": 2000,
        "description": "Open text editor"
      },
      {
        "tool": "type_text",
        "args": {
          "text": "#!/usr/bin/env python3\n# Fast script entry via paste\nimport os\nimport sys\n\nprint('Hello from pasted script!')\nprint(f'Platform: {sys.platform}')\nprint(f'Python: {sys.version}')\n",
          "use_paste": true
        },
        "wait_ms": 300,
        "description": "Paste Python script (use_paste is much faster for multiline)"
      },
      {
        "tool": "hotkey",
        "args": {"keys": ["ctrl", "s"]},
        "wait_ms": 500,
        "description": "Save file"
      },
      {
        "tool": "screenshot",
        "args": {},
        "description": "Verify code saved"
      }
    ]
  }
}
```

---

## Troubleshooting

### Workflow Runs Too Fast

**Problem:** Actions complete before UI updates

**Solution:** Increase `wait_ms` values

```json
{
  "tool": "click",
  "args": {"x": 500, "y": 500},
  "wait_ms": 2000  // Increased from 500
}
```

### Click Not Working at Coordinates

**Problem:** Position changed or coordinates wrong

**Solution:** Add screenshot step first

```json
{
  "tool": "screenshot",
  "args": {},
  "description": "Debug: see current state"
}
```

### Text Not Appearing

**Problem:** Application not focused

**Solution:** Use `focus_window` first

```json
{
  "tool": "focus_window",
  "args": {"window": "terminal"},
  "wait_ms": 300,
  "description": "Focus target window"
},
{
  "tool": "type_text",
  "args": {"text": "hello"},
  "description": "Now type"
}
```

### Terminal Command Fails

**Problem:** Environment or permissions

**Solution:** Execute in shell explicitly

```json
{
  "tool": "execute_command",
  "args": {"command": "bash -c 'cd /home/user && python script.py'"},
  "wait_ms": 5000
}
```

### analyze_screen Returns Error

**Problem:** VLM not configured

**Solution:** Check configuration

```bash
gaming-agent config  # View current config
```

Then ensure:
```json
{
  "vlm": {
    "enabled": true,
    "provider": "ollama",
    "model": "qwen2.5-vl:3b"
  }
}
```

---

## Advanced Topics

### Custom Workflows in Python

Create workflow files programmatically:

```python
from ai_gaming_agent import MCP

async def create_workflow():
    workflow = {
        "tool": "run_workflow",
        "args": {
            "steps": [
                {"tool": "screenshot", "args": {}},
                {"tool": "click", "args": {"x": 100, "y": 100}},
            ]
        }
    }

    result = await mcp.execute_tool(workflow)
    return result
```

### Workflow Templates

Store reusable workflow templates:

```json
{
  "name": "terminal_demo",
  "description": "Demo workflow for testing",
  "template": {
    "tool": "demo_terminal_workflow",
    "args": {
      "text": "${command}",
      "capture_screenshot": true,
      "close_terminal": true
    }
  }
}
```

### Performance Metrics

Workflows return timing information:

```json
{
  "success": true,
  "total_time_ms": 5234,
  "results": [
    {
      "step": 0,
      "time_ms": 3000,
      "tool": "execute_command"
    }
  ]
}
```

---

## Summary

Workflows are powerful tools for automation:

- **Simple:** Use `demo_terminal_workflow` for quick tests
- **Flexible:** Use `run_workflow` for complex sequences
- **Reliable:** Built-in error handling and verification
- **Efficient:** Batch multiple actions in one call
- **Observable:** Detailed responses with timing data

Start with simple workflows and gradually increase complexity as you gain experience.

---

## See Also

- [README.md](../README.md) - Quick start and overview
- [tools.txt](./tools.txt) - Tool reference documentation
- [configuration.md](./configuration.md) - Configuration guide
- [architecture.txt](./architecture.txt) - System architecture
