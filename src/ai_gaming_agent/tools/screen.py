"""Screen capture tools."""

from __future__ import annotations

import base64
import io
from typing import Any

import pyautogui
from screeninfo import get_monitors


def screenshot(monitor: int | None = None) -> dict[str, Any]:
    """Capture the current screen.

    Args:
        monitor: Optional monitor index for multi-monitor setups.

    Returns:
        Dict with base64-encoded PNG image.
    """
    try:
        if monitor is not None:
            monitors = get_monitors()
            if monitor < 0 or monitor >= len(monitors):
                return {"success": False, "error": f"Invalid monitor index: {monitor}"}
            m = monitors[monitor]
            img = pyautogui.screenshot(region=(m.x, m.y, m.width, m.height))
        else:
            img = pyautogui.screenshot()

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        b64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return {
            "success": True,
            "image": b64_image,
            "width": img.width,
            "height": img.height,
            "format": "png",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_screen_size(monitor: int | None = None) -> dict[str, Any]:
    """Get screen dimensions.

    Args:
        monitor: Optional monitor index.

    Returns:
        Dict with width and height.
    """
    try:
        monitors = get_monitors()

        if monitor is not None:
            if monitor < 0 or monitor >= len(monitors):
                return {"success": False, "error": f"Invalid monitor index: {monitor}"}
            m = monitors[monitor]
            return {"success": True, "width": m.width, "height": m.height}

        # Return primary monitor size
        primary = next((m for m in monitors if m.is_primary), monitors[0])
        return {
            "success": True,
            "width": primary.width,
            "height": primary.height,
            "monitors": len(monitors),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
