"""MCP Server implementation for AI Gaming Agent."""

from __future__ import annotations

import logging
from typing import Any

from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp.types import CallToolRequestParams, CallToolResult, ImageContent, ListToolsResult, TextContent, Tool

from ai_gaming_agent import __version__, tools
from ai_gaming_agent.config import Config

logger = logging.getLogger(__name__)

# Tool definitions for MCP
TOOL_DEFINITIONS = [
    # Screen tools
    Tool(
        name="screenshot",
        description="Capture the current screen. Returns a base64-encoded PNG image.",
        inputSchema={
            "type": "object",
            "properties": {
                "monitor": {"type": "integer", "description": "Monitor index for multi-monitor setups"},
            },
        },
    ),
    Tool(
        name="get_screen_size",
        description="Get screen dimensions in pixels.",
        inputSchema={
            "type": "object",
            "properties": {
                "monitor": {"type": "integer", "description": "Monitor index"},
            },
        },
    ),
    # Mouse tools
    Tool(
        name="click",
        description="Click at screen coordinates.",
        inputSchema={
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate (pixels from left)"},
                "y": {"type": "integer", "description": "Y coordinate (pixels from top)"},
                "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
            },
            "required": ["x", "y"],
        },
    ),
    Tool(
        name="double_click",
        description="Double-click at coordinates.",
        inputSchema={
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate"},
                "y": {"type": "integer", "description": "Y coordinate"},
            },
            "required": ["x", "y"],
        },
    ),
    Tool(
        name="move_to",
        description="Move mouse cursor to position.",
        inputSchema={
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Target X coordinate"},
                "y": {"type": "integer", "description": "Target Y coordinate"},
                "duration": {"type": "number", "description": "Movement time in seconds"},
            },
            "required": ["x", "y"],
        },
    ),
    Tool(
        name="drag_to",
        description="Drag from current position to target.",
        inputSchema={
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Target X coordinate"},
                "y": {"type": "integer", "description": "Target Y coordinate"},
                "duration": {"type": "number", "description": "Drag duration in seconds"},
            },
            "required": ["x", "y"],
        },
    ),
    Tool(
        name="scroll",
        description="Scroll mouse wheel.",
        inputSchema={
            "type": "object",
            "properties": {
                "clicks": {"type": "integer", "description": "Scroll ticks (positive=up, negative=down)"},
                "x": {"type": "integer", "description": "X position to scroll at"},
                "y": {"type": "integer", "description": "Y position to scroll at"},
            },
            "required": ["clicks"],
        },
    ),
    Tool(
        name="get_mouse_position",
        description="Get current mouse cursor position.",
        inputSchema={"type": "object", "properties": {}},
    ),
    # Keyboard tools
    Tool(
        name="type_text",
        description="Type a string of text. Supports fast input via clipboard paste.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to type"},
                "interval": {
                    "type": "number",
                    "description": "Delay between keystrokes in seconds (ignored if use_paste=True)",
                },
                "use_paste": {
                    "type": "boolean",
                    "description": "Use clipboard paste for faster input (copies to clipboard and pastes)",
                    "default": False,
                },
            },
            "required": ["text"],
        },
    ),
    Tool(
        name="press_key",
        description="Press a single keyboard key.",
        inputSchema={
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key name (e.g., enter, escape, tab, f1)"},
                "modifiers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Modifier keys (ctrl, alt, shift)",
                },
            },
            "required": ["key"],
        },
    ),
    Tool(
        name="hotkey",
        description="Press a key combination.",
        inputSchema={
            "type": "object",
            "properties": {
                "keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keys to press together (e.g., ['ctrl', 'c'])",
                },
            },
            "required": ["keys"],
        },
    ),
    # File tools
    Tool(
        name="read_file",
        description="Read file contents.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="write_file",
        description="Write content to file.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "Content to write"},
                "binary": {"type": "boolean", "description": "Content is base64 binary"},
            },
            "required": ["path", "content"],
        },
    ),
    Tool(
        name="list_files",
        description="List directory contents.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path"},
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="upload_file",
        description="Upload file to the PC.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Destination path"},
                "content": {"type": "string", "description": "File content"},
                "binary": {"type": "boolean", "description": "Content is base64"},
            },
            "required": ["path", "content"],
        },
    ),
    Tool(
        name="download_file",
        description="Download file from PC (returns base64).",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to download"},
            },
            "required": ["path"],
        },
    ),
    # System tools
    Tool(
        name="execute_command",
        description="Run a shell command.",
        inputSchema={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Command to execute"},
                "timeout": {"type": "integer", "description": "Max execution time in seconds"},
            },
            "required": ["command"],
        },
    ),
    Tool(
        name="get_system_info",
        description="Get system resource usage (CPU, RAM, disk).",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="list_windows",
        description="List all open windows.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="focus_window",
        description="Bring a window to the foreground.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Window title (partial match)"},
                "handle": {"type": "integer", "description": "Window handle ID"},
            },
        },
    ),
    # Workflow tools
    Tool(
        name="run_workflow",
        description=(
            "Execute a sequence of tool actions as a single workflow. "
            "Allows chaining multiple tool calls together with optional delays. "
            "Useful for complex automation tasks like opening a terminal, "
            "typing commands, and closing it - all in one call."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "description": "List of steps to execute sequentially",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": {
                                "type": "string",
                                "description": "Name of the tool to call",
                            },
                            "args": {
                                "type": "object",
                                "description": "Arguments to pass to the tool",
                                "default": {},
                            },
                            "wait_ms": {
                                "type": "integer",
                                "description": "Milliseconds to wait after this step",
                                "default": 0,
                            },
                            "description": {
                                "type": "string",
                                "description": "Human-readable description of the step",
                            },
                            "continue_on_error": {
                                "type": "boolean",
                                "description": "Continue workflow if this step fails",
                                "default": False,
                            },
                        },
                        "required": ["tool"],
                    },
                },
            },
            "required": ["steps"],
        },
    ),
    Tool(
        name="demo_terminal_workflow",
        description=(
            "Execute a complete terminal demo workflow: open terminal, "
            "type a command, press Enter, take a screenshot, and close the terminal. "
            "This is a convenience function that demonstrates full automation capability "
            "in a single call. Automatically detects the appropriate terminal application "
            "for the current platform (Linux, macOS, Windows)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text/command to type in the terminal",
                    "default": "echo hello world",
                },
                "terminal_wait_ms": {
                    "type": "integer",
                    "description": "Milliseconds to wait for terminal to open",
                    "default": 2000,
                },
                "post_type_wait_ms": {
                    "type": "integer",
                    "description": "Milliseconds to wait after typing",
                    "default": 500,
                },
                "post_enter_wait_ms": {
                    "type": "integer",
                    "description": "Milliseconds to wait after pressing Enter",
                    "default": 1000,
                },
                "capture_screenshot": {
                    "type": "boolean",
                    "description": "Whether to take a screenshot after command execution",
                    "default": True,
                },
                "close_terminal": {
                    "type": "boolean",
                    "description": "Whether to close the terminal at the end",
                    "default": True,
                },
            },
        },
    ),
    # VLM tools
    Tool(
        name="analyze_screen",
        description=(
            "Analyze the current screen using a Vision Language Model (VLM). "
            "Takes a screenshot and sends it to the configured VLM (e.g., Ollama with qwen2.5-vl) "
            "along with a prompt for analysis. Useful for understanding game state, reading text, "
            "or identifying UI elements. Requires VLM to be enabled in config."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "The analysis prompt/question about the screen content. "
                        "Examples: 'What is the current health bar percentage?', "
                        "'Is there a dialog box on screen?', 'List all visible menu options'"
                    ),
                },
                "monitor": {
                    "type": "integer",
                    "description": "Optional monitor index for multi-monitor setups",
                },
            },
            "required": ["prompt"],
        },
    ),
]

# Map tool names to functions
TOOL_HANDLERS = {
    "screenshot": tools.screenshot,
    "get_screen_size": tools.get_screen_size,
    "click": tools.click,
    "double_click": tools.double_click,
    "move_to": tools.move_to,
    "drag_to": tools.drag_to,
    "scroll": tools.scroll,
    "get_mouse_position": tools.get_mouse_position,
    "type_text": tools.type_text,
    "press_key": tools.press_key,
    "hotkey": tools.hotkey,
    "read_file": tools.read_file,
    "write_file": tools.write_file,
    "list_files": tools.list_files,
    "upload_file": tools.upload_file,
    "download_file": tools.download_file,
    "execute_command": tools.execute_command,
    "get_system_info": tools.get_system_info,
    "list_windows": tools.list_windows,
    "focus_window": tools.focus_window,
    # Workflow
    "run_workflow": tools.run_workflow,
    "demo_terminal_workflow": tools.demo_terminal_workflow,
    # VLM
    "analyze_screen": tools.analyze_screen,
}


async def _list_tools(
    ctx: ServerRequestContext[Any],
    params: Any,
) -> ListToolsResult:
    """Answer ``tools/list`` with the registered tool definitions."""
    return ListToolsResult(tools=TOOL_DEFINITIONS)


async def _call_tool(
    ctx: ServerRequestContext[Any],
    params: CallToolRequestParams,
) -> CallToolResult:
    """Dispatch one ``tools/call`` request to its handler.

    A handler that raises becomes a tool result carrying ``is_error``, as mcp 1's
    ``call_tool`` decorator did. mcp 2 dispatches handlers without that wrapper,
    so an unsheltered raise would reach the client as a JSON-RPC protocol error
    instead of the per-call tool failure it is.
    """
    name = params.name
    arguments = params.arguments or {}

    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return CallToolResult(content=[TextContent(type="text", text=f"Unknown tool: {name}")], is_error=True)

    try:
        result = handler(**arguments)
    except Exception as exc:
        logger.exception("Tool %r raised", name)
        return CallToolResult(content=[TextContent(type="text", text=str(exc))], is_error=True)

    # Special handling for screenshot - return image
    if name == "screenshot" and result.get("success") and "image" in result:
        return CallToolResult(
            content=[
                ImageContent(
                    type="image",
                    data=result["image"],
                    mimeType="image/png",
                )
            ]
        )

    # Return text result
    import json

    return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, indent=2))])


def create_server(config: Config | None = None) -> Server:
    """Create and configure the MCP server.

    The version is named explicitly: mcp 1.x substituted the SDK's own package
    version into ``serverInfo`` for an unversioned server, while mcp 2 passes
    the constructor's version through unchanged and reports an empty one. A
    client reads ``serverInfo.version`` to identify this server, so it carries
    the agent's version.
    """
    return Server(
        "ai-gaming-agent",
        version=__version__,
        on_list_tools=_list_tools,
        on_call_tool=_call_tool,
    )


async def run_server(config: Config | None = None) -> None:
    """Run the MCP server."""
    server = create_server(config)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
