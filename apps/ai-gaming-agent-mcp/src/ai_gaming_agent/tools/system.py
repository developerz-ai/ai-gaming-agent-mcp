"""System tools."""

from __future__ import annotations

import subprocess
import sys
from typing import Any

import psutil

from ai_gaming_agent.config import get_config


def _is_command_blocked(command: str) -> bool:
    """Check if command contains blocked patterns."""
    config = get_config()
    cmd_lower = command.lower()
    for blocked in config.security.blocked_commands:
        if blocked.lower() in cmd_lower:
            return True
    return False


def execute_command(command: str, timeout: int | None = None) -> dict[str, Any]:
    """Run a shell command.

    Args:
        command: Command to execute.
        timeout: Max execution time in seconds.

    Returns:
        stdout, stderr, and exit code.
    """
    config = get_config()

    if not config.features.command_execution:
        return {"success": False, "error": "Command execution is disabled"}

    if _is_command_blocked(command):
        return {"success": False, "error": f"Command blocked by security policy: {command}"}

    if timeout is None:
        timeout = config.security.max_command_timeout

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Command timed out after {timeout} seconds"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_system_info() -> dict[str, Any]:
    """Get system resource usage.

    Returns:
        CPU, RAM, and disk usage statistics.
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        info = {
            "success": True,
            "cpu_percent": cpu_percent,
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
            },
            "disk": {
                "total": disk.total,
                "free": disk.free,
                "percent": disk.percent,
            },
            "platform": sys.platform,
        }

        # Try to get GPU info if available
        try:
            import pynvml

            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            gpu_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            info["gpu"] = {
                "total": gpu_info.total,
                "used": gpu_info.used,
                "free": gpu_info.free,
            }
            pynvml.nvmlShutdown()
        except Exception:
            pass  # GPU info not available

        return info
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_windows() -> dict[str, Any]:
    """List all open windows.

    Returns:
        List of window titles and handles.
    """
    try:
        windows = []

        if sys.platform == "win32":
            import win32gui

            def enum_handler(hwnd: int, results: list) -> None:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        results.append({"handle": hwnd, "title": title})

            win32gui.EnumWindows(enum_handler, windows)

        elif sys.platform == "linux":
            # Use wmctrl if available
            result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    parts = line.split(None, 3)
                    if len(parts) >= 4:
                        windows.append({"handle": parts[0], "title": parts[3]})

        elif sys.platform == "darwin":
            # macOS - use AppleScript
            script = 'tell application "System Events" to get name of every window of every process'
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode == 0:
                for i, title in enumerate(result.stdout.strip().split(", ")):
                    if title:
                        windows.append({"handle": i, "title": title})

        return {"success": True, "windows": windows}
    except Exception as e:
        return {"success": False, "error": str(e)}


def focus_window(title: str | None = None, handle: int | None = None) -> dict[str, Any]:
    """Bring a window to the foreground.

    Args:
        title: Window title (partial match).
        handle: Window handle ID.

    Returns:
        Success status.
    """
    try:
        if not title and handle is None:
            return {"success": False, "error": "Must provide title or handle"}

        if sys.platform == "win32":
            import win32gui

            if handle:
                win32gui.SetForegroundWindow(handle)
            else:

                def enum_handler(hwnd: int, target: str) -> None:
                    if target.lower() in win32gui.GetWindowText(hwnd).lower():
                        win32gui.SetForegroundWindow(hwnd)

                win32gui.EnumWindows(enum_handler, title)

        elif sys.platform == "linux":
            if title:
                subprocess.run(["wmctrl", "-a", title])
            else:
                subprocess.run(["wmctrl", "-i", "-a", str(handle)])

        elif sys.platform == "darwin":
            if title:
                script = f'tell application "{title}" to activate'
                subprocess.run(["osascript", "-e", script])

        return {"success": True, "title": title, "handle": handle}
    except Exception as e:
        return {"success": False, "error": str(e)}
