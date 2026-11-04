"""Keyboard control tools."""

from __future__ import annotations

import platform
from typing import Any

import pyautogui


def type_text(
    text: str, interval: float = 0.0, use_paste: bool = False
) -> dict[str, Any]:
    """Type a string of text.

    Args:
        text: Text to type.
        interval: Delay between keystrokes in seconds (ignored if use_paste=True).
        use_paste: If True, use clipboard paste for faster input. This copies
            the text to the clipboard and simulates Ctrl+V (or Cmd+V on macOS).
            Much faster for long text but requires clipboard access.

    Returns:
        Success status with method used.
    """
    try:
        if use_paste:
            # Use clipboard-based fast input
            import pyperclip

            # Save original clipboard content
            try:
                original_clipboard = pyperclip.paste()
            except Exception:
                original_clipboard = None

            # Copy text to clipboard
            pyperclip.copy(text)

            # Paste using platform-appropriate hotkey
            if platform.system() == "Darwin":
                pyautogui.hotkey("command", "v")
            else:
                pyautogui.hotkey("ctrl", "v")

            # Restore original clipboard content (optional, best effort)
            if original_clipboard is not None:
                try:
                    pyperclip.copy(original_clipboard)
                except Exception:
                    pass  # Ignore restore failures

            return {"success": True, "text": text, "method": "paste"}
        else:
            pyautogui.write(text, interval=interval)
            return {"success": True, "text": text, "method": "type"}
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
