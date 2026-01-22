"""MCP Tools for AI Gaming Agent.

Tools are organized into modules:
- screen: screenshot, get_screen_size, analyze_screen
- mouse: click, double_click, move_to, drag_to, scroll, get_mouse_position
- keyboard: type_text, press_key, hotkey
- files: read_file, write_file, list_files, upload_file, download_file
- system: execute_command, get_system_info, list_windows, focus_window

Import tools directly from submodules to avoid GUI dependency issues:
    from ai_gaming_agent.tools.files import read_file
"""

import importlib

__all__ = [
    # Screen
    "screenshot",
    "get_screen_size",
    # Mouse
    "click",
    "double_click",
    "move_to",
    "drag_to",
    "scroll",
    "get_mouse_position",
    # Keyboard
    "type_text",
    "press_key",
    "hotkey",
    # Files
    "read_file",
    "write_file",
    "list_files",
    "upload_file",
    "download_file",
    # System
    "execute_command",
    "get_system_info",
    "list_windows",
    "focus_window",
]

_MODULE_MAP = {
    "screenshot": "screen",
    "get_screen_size": "screen",
    "click": "mouse",
    "double_click": "mouse",
    "move_to": "mouse",
    "drag_to": "mouse",
    "scroll": "mouse",
    "get_mouse_position": "mouse",
    "type_text": "keyboard",
    "press_key": "keyboard",
    "hotkey": "keyboard",
    "read_file": "files",
    "write_file": "files",
    "list_files": "files",
    "upload_file": "files",
    "download_file": "files",
    "execute_command": "system",
    "get_system_info": "system",
    "list_windows": "system",
    "focus_window": "system",
}


def __getattr__(name: str):
    """Lazy import to avoid loading GUI dependencies unnecessarily."""
    if name in _MODULE_MAP:
        module = importlib.import_module(f".{_MODULE_MAP[name]}", __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
