"""Keyboard control tools."""

from __future__ import annotations

from typing import Any

import pyautogui


def type_text(text: str, interval: float = 0.0) -> dict[str, Any]:
    """Type a string of text.

    Args:
        text: Text to type.
        interval: Delay between keystrokes in seconds.

    Returns:
        Success status.
    """
    try:
        pyautogui.write(text, interval=interval)
        return {"success": True, "text": text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def press_key(key: str, modifiers: list[str] | None = None) -> dict[str, Any]:
    """Press a single keyboard key.

    Args:
        key: Key name (e.g., 'enter', 'escape', 'tab', 'f1').
        modifiers: Optional list of modifier keys (ctrl, alt, shift).

    Returns:
        Success status.
    """
    try:
        if modifiers:
            # Press with modifiers
            with pyautogui.hold(modifiers):
                pyautogui.press(key)
        else:
            pyautogui.press(key)
        return {"success": True, "key": key, "modifiers": modifiers}
    except Exception as e:
        return {"success": False, "error": str(e)}


def hotkey(keys: list[str]) -> dict[str, Any]:
    """Press a key combination.

    Args:
        keys: List of keys to press together (e.g., ['ctrl', 'c']).

    Returns:
        Success status.
    """
    try:
        pyautogui.hotkey(*keys)
        return {"success": True, "keys": keys}
    except Exception as e:
        return {"success": False, "error": str(e)}
