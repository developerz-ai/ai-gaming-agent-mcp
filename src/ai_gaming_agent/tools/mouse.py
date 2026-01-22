"""Mouse control tools."""

from __future__ import annotations

from typing import Any, Literal

import pyautogui

# Disable pyautogui fail-safe for automation
pyautogui.FAILSAFE = False


def click(
    x: int,
    y: int,
    button: Literal["left", "right", "middle"] = "left",
) -> dict[str, Any]:
    """Click at screen coordinates.

    Args:
        x: X coordinate (pixels from left).
        y: Y coordinate (pixels from top).
        button: Mouse button to click.

    Returns:
        Success status.
    """
    try:
        pyautogui.click(x=x, y=y, button=button)
        return {"success": True, "x": x, "y": y, "button": button}
    except Exception as e:
        return {"success": False, "error": str(e)}


def double_click(x: int, y: int) -> dict[str, Any]:
    """Double-click at coordinates.

    Args:
        x: X coordinate.
        y: Y coordinate.

    Returns:
        Success status.
    """
    try:
        pyautogui.doubleClick(x=x, y=y)
        return {"success": True, "x": x, "y": y}
    except Exception as e:
        return {"success": False, "error": str(e)}


def move_to(x: int, y: int, duration: float = 0.0) -> dict[str, Any]:
    """Move mouse cursor to position.

    Args:
        x: Target X coordinate.
        y: Target Y coordinate.
        duration: Movement time in seconds.

    Returns:
        Success status.
    """
    try:
        pyautogui.moveTo(x=x, y=y, duration=duration)
        return {"success": True, "x": x, "y": y}
    except Exception as e:
        return {"success": False, "error": str(e)}


def drag_to(x: int, y: int, duration: float = 0.5) -> dict[str, Any]:
    """Drag from current position to target.

    Args:
        x: Target X coordinate.
        y: Target Y coordinate.
        duration: Drag duration in seconds.

    Returns:
        Success status.
    """
    try:
        pyautogui.dragTo(x=x, y=y, duration=duration)
        return {"success": True, "x": x, "y": y}
    except Exception as e:
        return {"success": False, "error": str(e)}


def scroll(clicks: int, x: int | None = None, y: int | None = None) -> dict[str, Any]:
    """Scroll mouse wheel.

    Args:
        clicks: Number of scroll ticks (positive=up, negative=down).
        x: Optional X position to scroll at.
        y: Optional Y position to scroll at.

    Returns:
        Success status.
    """
    try:
        pyautogui.scroll(clicks, x=x, y=y)
        return {"success": True, "clicks": clicks}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_mouse_position() -> dict[str, Any]:
    """Get current mouse cursor position.

    Returns:
        Dict with x and y coordinates.
    """
    try:
        pos = pyautogui.position()
        return {"success": True, "x": pos.x, "y": pos.y}
    except Exception as e:
        return {"success": False, "error": str(e)}
