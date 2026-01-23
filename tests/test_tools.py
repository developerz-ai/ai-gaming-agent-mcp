"""Tests for tool modules."""

import tempfile
from pathlib import Path

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
