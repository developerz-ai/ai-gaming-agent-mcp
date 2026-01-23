"""Tests for tool modules."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Skip GUI tests if pyautogui not importable (CI without display/tkinter)
try:
    import pyautogui  # noqa: F401

    HAS_GUI = True
except (ImportError, SystemExit, Exception):
    HAS_GUI = False


def test_write_and_read_file():
    """Test writing and reading files."""
    from ai_gaming_agent.tools.files import read_file, write_file

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = str(Path(tmpdir) / "test.txt")

        # Write file
        result = write_file(file_path, "Hello, World!")
        assert result["success"] is True

        # Read file
        result = read_file(file_path)
        assert result["success"] is True
        assert result["content"] == "Hello, World!"
        assert result["binary"] is False


def test_list_files():
    """Test listing directory contents."""
    from ai_gaming_agent.tools.files import list_files

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some files
        (Path(tmpdir) / "file1.txt").write_text("content1")
        (Path(tmpdir) / "file2.txt").write_text("content2")
        (Path(tmpdir) / "subdir").mkdir()

        result = list_files(tmpdir)
        assert result["success"] is True
        assert len(result["items"]) == 3

        names = {item["name"] for item in result["items"]}
        assert "file1.txt" in names
        assert "file2.txt" in names
        assert "subdir" in names


def test_read_nonexistent_file():
    """Test reading a file that doesn't exist."""
    from ai_gaming_agent.tools.files import read_file

    result = read_file("/nonexistent/file.txt")
    assert result["success"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.skipif(not HAS_GUI, reason="GUI not available")
def test_keyboard_functions_return_dict():
    """Test that keyboard functions return proper dicts."""
    from ai_gaming_agent.tools.keyboard import hotkey, press_key, type_text

    result = type_text("test")
    assert isinstance(result, dict)
    assert "success" in result
    assert result.get("method") == "type"

    result = press_key("enter")
    assert isinstance(result, dict)
    assert "success" in result

    result = hotkey(["ctrl", "c"])
    assert isinstance(result, dict)
    assert "success" in result


@pytest.mark.skipif(not HAS_GUI, reason="GUI not available")
def test_type_text_with_paste():
    """Test type_text with use_paste=True for fast clipboard-based input."""
    from ai_gaming_agent.tools.keyboard import type_text

    # Test paste method returns correct result structure
    result = type_text("hello world", use_paste=True)
    assert isinstance(result, dict)
    assert "success" in result
    if result["success"]:
        assert result.get("method") == "paste"
        assert result.get("text") == "hello world"


@pytest.mark.skipif(not HAS_GUI, reason="GUI not available")
def test_type_text_method_field():
    """Test that type_text returns 'method' field indicating input method used."""
    from ai_gaming_agent.tools.keyboard import type_text

    # Regular typing should report "type" method
    result = type_text("test", use_paste=False)
    if result["success"]:
        assert result.get("method") == "type"

    # Paste should report "paste" method
    result = type_text("test", use_paste=True)
    if result["success"]:
        assert result.get("method") == "paste"


# ============================================================================
# UNIT TESTS FOR PASTE FUNCTIONALITY (mocked - works in CI)
# ============================================================================


class TestTypeTextPasteMocked:
    """Unit tests for type_text paste functionality using mocks.

    These tests mock pyperclip and pyautogui to test the paste logic
    without requiring a real display or clipboard.
    """

    def test_type_text_paste_copies_to_clipboard(self):
        """Test that use_paste=True copies text to clipboard."""
        # Create mock for pyperclip
        mock_pyperclip = MagicMock()
        mock_pyperclip.paste.return_value = "original"

        with (
            patch.dict(sys.modules, {"pyperclip": mock_pyperclip}),
            patch("ai_gaming_agent.tools.keyboard.pyautogui"),
            patch("ai_gaming_agent.tools.keyboard.platform") as mock_platform,
        ):
            mock_platform.system.return_value = "Linux"

            from ai_gaming_agent.tools.keyboard import type_text

            result = type_text("hello world", use_paste=True)

            assert result["success"] is True
            assert result["method"] == "paste"
            assert result["text"] == "hello world"
            mock_pyperclip.copy.assert_any_call("hello world")

    def test_type_text_paste_uses_ctrl_v_on_linux(self):
        """Test that paste uses Ctrl+V on Linux."""
        mock_pyperclip = MagicMock()
        mock_pyperclip.paste.return_value = ""

        with (
            patch.dict(sys.modules, {"pyperclip": mock_pyperclip}),
            patch("ai_gaming_agent.tools.keyboard.pyautogui") as mock_pyautogui,
            patch("ai_gaming_agent.tools.keyboard.platform") as mock_platform,
        ):
            mock_platform.system.return_value = "Linux"

            from ai_gaming_agent.tools.keyboard import type_text

            type_text("test", use_paste=True)

            mock_pyautogui.hotkey.assert_called_with("ctrl", "v")

    def test_type_text_paste_uses_ctrl_v_on_windows(self):
        """Test that paste uses Ctrl+V on Windows."""
        mock_pyperclip = MagicMock()
        mock_pyperclip.paste.return_value = ""

        with (
            patch.dict(sys.modules, {"pyperclip": mock_pyperclip}),
            patch("ai_gaming_agent.tools.keyboard.pyautogui") as mock_pyautogui,
            patch("ai_gaming_agent.tools.keyboard.platform") as mock_platform,
        ):
            mock_platform.system.return_value = "Windows"

            from ai_gaming_agent.tools.keyboard import type_text

            type_text("test", use_paste=True)

            mock_pyautogui.hotkey.assert_called_with("ctrl", "v")

    def test_type_text_paste_uses_cmd_v_on_macos(self):
        """Test that paste uses Cmd+V on macOS."""
        mock_pyperclip = MagicMock()
        mock_pyperclip.paste.return_value = ""

        with (
            patch.dict(sys.modules, {"pyperclip": mock_pyperclip}),
            patch("ai_gaming_agent.tools.keyboard.pyautogui") as mock_pyautogui,
            patch("ai_gaming_agent.tools.keyboard.platform") as mock_platform,
        ):
            mock_platform.system.return_value = "Darwin"

            from ai_gaming_agent.tools.keyboard import type_text

            type_text("test", use_paste=True)

            mock_pyautogui.hotkey.assert_called_with("command", "v")

    def test_type_text_paste_restores_original_clipboard(self):
        """Test that paste restores original clipboard content."""
        mock_pyperclip = MagicMock()
        mock_pyperclip.paste.return_value = "original content"

        with (
            patch.dict(sys.modules, {"pyperclip": mock_pyperclip}),
            patch("ai_gaming_agent.tools.keyboard.pyautogui"),
            patch("ai_gaming_agent.tools.keyboard.platform") as mock_platform,
        ):
            mock_platform.system.return_value = "Linux"

            from ai_gaming_agent.tools.keyboard import type_text

            type_text("new text", use_paste=True)

            # Verify clipboard operations in order
            copy_calls = mock_pyperclip.copy.call_args_list
            assert len(copy_calls) == 2
            assert copy_calls[0][0][0] == "new text"  # First copy: the text to paste
            assert copy_calls[1][0][0] == "original content"  # Second copy: restore original

    def test_type_text_paste_handles_empty_original_clipboard(self):
        """Test that paste handles case when original clipboard is empty."""
        mock_pyperclip = MagicMock()
        mock_pyperclip.paste.return_value = ""

        with (
            patch.dict(sys.modules, {"pyperclip": mock_pyperclip}),
            patch("ai_gaming_agent.tools.keyboard.pyautogui"),
            patch("ai_gaming_agent.tools.keyboard.platform") as mock_platform,
        ):
            mock_platform.system.return_value = "Linux"

            from ai_gaming_agent.tools.keyboard import type_text

            result = type_text("test", use_paste=True)

            assert result["success"] is True
            # Empty string is not None, so it should try to restore
            copy_calls = mock_pyperclip.copy.call_args_list
            assert len(copy_calls) == 2

    def test_type_text_paste_handles_clipboard_read_error(self):
        """Test that paste handles errors when reading original clipboard."""
        mock_pyperclip = MagicMock()
        mock_pyperclip.paste.side_effect = Exception("Clipboard unavailable")

        with (
            patch.dict(sys.modules, {"pyperclip": mock_pyperclip}),
            patch("ai_gaming_agent.tools.keyboard.pyautogui"),
            patch("ai_gaming_agent.tools.keyboard.platform") as mock_platform,
        ):
            mock_platform.system.return_value = "Linux"

            from ai_gaming_agent.tools.keyboard import type_text

            result = type_text("test", use_paste=True)

            assert result["success"] is True
            # Should still work, just won't restore clipboard
            mock_pyperclip.copy.assert_called_once_with("test")

    def test_type_text_paste_handles_clipboard_restore_error(self):
        """Test that paste handles errors when restoring clipboard."""
        mock_pyperclip = MagicMock()
        mock_pyperclip.paste.return_value = "original"
        # First call to copy succeeds, second fails
        mock_pyperclip.copy.side_effect = [None, Exception("Restore failed")]

        with (
            patch.dict(sys.modules, {"pyperclip": mock_pyperclip}),
            patch("ai_gaming_agent.tools.keyboard.pyautogui"),
            patch("ai_gaming_agent.tools.keyboard.platform") as mock_platform,
        ):
            mock_platform.system.return_value = "Linux"

            from ai_gaming_agent.tools.keyboard import type_text

            result = type_text("test", use_paste=True)

            # Should still succeed even if restore fails
            assert result["success"] is True

    def test_type_text_paste_returns_error_on_copy_failure(self):
        """Test that paste returns error if initial copy fails."""
        mock_pyperclip = MagicMock()
        mock_pyperclip.paste.return_value = "original"
        mock_pyperclip.copy.side_effect = Exception("Copy failed")

        with (
            patch.dict(sys.modules, {"pyperclip": mock_pyperclip}),
            patch("ai_gaming_agent.tools.keyboard.pyautogui"),
            patch("ai_gaming_agent.tools.keyboard.platform") as mock_platform,
        ):
            mock_platform.system.return_value = "Linux"

            from ai_gaming_agent.tools.keyboard import type_text

            result = type_text("test", use_paste=True)

            assert result["success"] is False
            assert "Copy failed" in result["error"]

    def test_type_text_paste_returns_error_on_hotkey_failure(self):
        """Test that paste returns error if hotkey paste fails."""
        mock_pyperclip = MagicMock()
        mock_pyperclip.paste.return_value = "original"

        with (
            patch.dict(sys.modules, {"pyperclip": mock_pyperclip}),
            patch("ai_gaming_agent.tools.keyboard.pyautogui") as mock_pyautogui,
            patch("ai_gaming_agent.tools.keyboard.platform") as mock_platform,
        ):
            mock_platform.system.return_value = "Linux"
            mock_pyautogui.hotkey.side_effect = Exception("Hotkey failed")

            from ai_gaming_agent.tools.keyboard import type_text

            result = type_text("test", use_paste=True)

            assert result["success"] is False
            assert "Hotkey failed" in result["error"]

    def test_type_text_normal_uses_pyautogui_write(self):
        """Test that use_paste=False uses pyautogui.write."""
        with patch("ai_gaming_agent.tools.keyboard.pyautogui") as mock_pyautogui:
            from ai_gaming_agent.tools.keyboard import type_text

            result = type_text("test", use_paste=False)

            assert result["success"] is True
            assert result["method"] == "type"
            mock_pyautogui.write.assert_called_once_with("test", interval=0.0)

    def test_type_text_normal_with_interval(self):
        """Test that interval parameter is passed to pyautogui.write."""
        with patch("ai_gaming_agent.tools.keyboard.pyautogui") as mock_pyautogui:
            from ai_gaming_agent.tools.keyboard import type_text

            result = type_text("test", interval=0.1, use_paste=False)

            assert result["success"] is True
            mock_pyautogui.write.assert_called_once_with("test", interval=0.1)

    def test_type_text_default_is_normal_typing(self):
        """Test that default behavior is normal typing, not paste."""
        with patch("ai_gaming_agent.tools.keyboard.pyautogui") as mock_pyautogui:
            from ai_gaming_agent.tools.keyboard import type_text

            result = type_text("test")

            assert result["success"] is True
            assert result["method"] == "type"
            mock_pyautogui.write.assert_called_once()


@pytest.mark.skipif(not HAS_GUI, reason="GUI not available")
def test_mouse_functions_return_dict():
    """Test that mouse functions return proper dicts."""
    from ai_gaming_agent.tools.mouse import click, get_mouse_position, scroll

    result = click(100, 100)
    assert isinstance(result, dict)
    assert "success" in result

    result = scroll(3)
    assert isinstance(result, dict)
    assert "success" in result

    result = get_mouse_position()
    assert isinstance(result, dict)
    assert "success" in result
