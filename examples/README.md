# AI Gaming Agent Examples

This directory contains standalone Python scripts demonstrating how to use the AI Gaming Agent MCP Server.

## Table of Contents

- [Quick Start](#quick-start)
- [Examples](#examples)
  - [terminal_demo.py](#terminal_demopy)
- [Running Examples](#running-examples)
- [Requirements](#requirements)

## Quick Start

### 1. Start the MCP Server

In one terminal, start the server:

```bash
# Initialize configuration (first time only)
gaming-agent init --password mypassword

# Start the server
gaming-agent serve
```

The server will be available at `http://localhost:8765`

### 2. Run an Example

In another terminal, run an example script:

```bash
cd examples
uv run terminal_demo.py --password mypassword
```

## Examples

### terminal_demo.py

A complete example that demonstrates the end-to-end workflow:

1. **Connects** to the MCP server via HTTP
2. **Authenticates** with a password
3. **Calls** the `demo_terminal_workflow` tool
4. **Executes** a command in a new terminal
5. **Captures** a screenshot of the output
6. **Saves** the screenshot to disk
7. **Displays** detailed results

#### Basic Usage

```bash
# Run with default command "echo hello world"
uv run terminal_demo.py --password mypassword

# Run with custom command
uv run terminal_demo.py --password mypassword --command "ls -la"

# Keep terminal open (don't close after command)
uv run terminal_demo.py --password mypassword --keep-open

# Use custom server
uv run terminal_demo.py --url http://192.168.1.100:8765 --password secret

# Verbose output for debugging
uv run terminal_demo.py --password mypassword -v
```

#### Features Demonstrated

The script shows how to:

- **Parse CLI arguments** for flexible configuration
- **Create MCP client** with HTTP authentication
- **Check server health** before making requests
- **Call MCP tools** with specific parameters
- **Handle responses** from workflow execution
- **Process screenshots** in base64 format
- **Log detailed results** with proper formatting
- **Handle errors** gracefully

#### Output Example

```
================================================================================
AI Gaming Agent - Terminal Demo
================================================================================
2024-01-22 10:15:30,123 - __main__ - INFO - Checking server health...
2024-01-22 10:15:30,234 - __main__ - INFO - Server status: ok
2024-01-22 10:15:30,234 - __main__ - INFO - Server version: 0.1.0
2024-01-22 10:15:30,345 - __main__ - INFO - Connecting to MCP server...
2024-01-22 10:15:30,456 - __main__ - INFO - Running terminal workflow: echo hello world
--------------------------------------------------------------------------------
2024-01-22 10:15:30,567 - __main__ - INFO - Calling tool: demo_terminal_workflow
2024-01-22 10:15:34,678 - __main__ - INFO - Tool demo_terminal_workflow completed
--------------------------------------------------------------------------------
WORKFLOW RESULTS
--------------------------------------------------------------------------------
2024-01-22 10:15:34,789 - __main__ - INFO - Success: True
2024-01-22 10:15:34,789 - __main__ - INFO - Platform: Linux
2024-01-22 10:15:34,789 - __main__ - INFO - Terminal: gnome-terminal
2024-01-22 10:15:34,789 - __main__ - INFO - Text typed: echo hello world
2024-01-22 10:15:34,789 - __main__ - INFO - Total time: 4523ms
2024-01-22 10:15:34,789 - __main__ - INFO - Completed steps (7):
2024-01-22 10:15:34,789 - __main__ - INFO -   ✓ detect_terminal
2024-01-22 10:15:34,789 - __main__ - INFO -   ✓ open_terminal
2024-01-22 10:15:34,789 - __main__ - INFO -   ✓ wait_for_terminal
2024-01-22 10:15:34,789 - __main__ - INFO -   ✓ type_text
2024-01-22 10:15:34,789 - __main__ - INFO -   ✓ press_enter
2024-01-22 10:15:34,789 - __main__ - INFO -   ✓ capture_screenshot
2024-01-22 10:15:34,789 - __main__ - INFO -   ✓ close_terminal
2024-01-22 10:15:34,789 - __main__ - INFO - Saving screenshot...
2024-01-22 10:15:34,890 - __main__ - INFO - Screenshot saved: ./screenshots/terminal_output.png
================================================================================
Demo complete!
================================================================================
```

#### Command-Line Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--url` | string | `http://localhost:8765` | URL of the MCP server |
| `--password` | string | *required* | Server password for authentication |
| `--command` | string | `echo hello world` | Command to execute in terminal |
| `--keep-open` | flag | - | Keep terminal open after execution |
| `--no-screenshots` | flag | - | Don't save screenshots to disk |
| `-v, --verbose` | flag | - | Enable debug-level logging |

## Running Examples

### Using `uv run`

The easiest way to run examples (uses project's dependencies):

```bash
# List available examples
ls examples/

# Run terminal demo
uv run examples/terminal_demo.py --password mypassword
```

### Using Python Directly

If you have the dependencies installed globally:

```bash
pip install mcp httpx
python examples/terminal_demo.py --password mypassword
```

### From within examples directory

```bash
cd examples
uv run terminal_demo.py --password mypassword
```

## Requirements

### System Requirements

- Python 3.12+
- MCP server running and accessible
- Network connectivity to the server

### Python Dependencies

- `mcp>=1.0.0` - MCP protocol implementation
- `httpx` - Async HTTP client (optional, for this demo)

### Optional

- `pillow>=10.0.0` - For image handling (only if saving screenshots)

## Server Configuration

### Starting the Server

```bash
# Initialize (first time)
gaming-agent init --password mypassword

# Start the server
gaming-agent serve
```

The server listens on:
- **Address:** `0.0.0.0` (all interfaces)
- **Port:** `8765` (default)
- **Protocol:** HTTP with SSE transport

### Server Configuration File

Configuration is stored in `~/.gaming-agent/config.json`:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8765,
    "password": "mypassword"
  },
  "vlm": {
    "enabled": false,
    "provider": "ollama",
    "model": "qwen2.5-vl:3b",
    "endpoint": "http://localhost:11434"
  }
}
```

## Troubleshooting

### Connection Refused

**Problem:** `Connection refused` when running example

**Solution:** Ensure server is running:
```bash
gaming-agent serve
```

### Authentication Failed

**Problem:** `Invalid authentication token`

**Solution:** Check that you're using the correct password:
```bash
# View current password
gaming-agent config

# Update password if needed
gaming-agent init --password newpassword
```

### Server Not Found

**Problem:** `Name resolution failed` or `Connection timeout`

**Solution:** Check server URL:
```bash
# For local server
uv run examples/terminal_demo.py --url http://localhost:8765 --password mypassword

# For remote server
uv run examples/terminal_demo.py --url http://192.168.1.100:8765 --password mypassword
```

### Screenshot Save Failed

**Problem:** `Failed to save screenshot`

**Solution:** Ensure screenshot directory is writable:
```bash
# Create screenshots directory manually
mkdir -p screenshots
chmod 755 screenshots
```

## Next Steps

1. **Read the main README** for an overview of the AI Gaming Agent
2. **Check docs/workflow.md** for detailed workflow documentation
3. **Review tools.txt** for the complete tool reference
4. **Explore the source code** in `src/ai_gaming_agent/`

## Examples for Other Use Cases

More examples coming soon:

- `browser_demo.py` - Automate web browser interactions
- `game_automation.py` - Control game clients
- `multi_pc_demo.py` - Control multiple PCs simultaneously
- `workflow_builder.py` - Create and manage complex workflows

## Contributing

To add new examples:

1. Create a new `.py` file in this directory
2. Include comprehensive docstring and comments
3. Add both basic and advanced usage examples
4. Update this README with the new example
5. Test thoroughly before submitting

## License

These examples are part of the AI Gaming Agent project and are licensed under MIT.
