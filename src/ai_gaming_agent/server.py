"""MCP Server implementation for AI Gaming Agent."""

from __future__ import annotations

import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import ImageContent, TextContent, Tool

from ai_gaming_agent import tools
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
        description="Type a string of text.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to type"},
                "interval": {"type": "number", "description": "Delay between keystrokes in seconds"},
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
}


def create_server(config: Config | None = None) -> Server:
    """Create and configure the MCP server."""
    server = Server("ai-gaming-agent")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOL_DEFINITIONS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent | ImageContent]:
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        result = handler(**arguments)

        # Special handling for screenshot - return image
        if name == "screenshot" and result.get("success") and "image" in result:
            return [
                ImageContent(
                    type="image",
                    data=result["image"],
                    mimeType="image/png",
                )
            ]

        # Return text result
        import json

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    return server


async def run_server(config: Config | None = None) -> None:
    """Run the MCP server."""
    server = create_server(config)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
