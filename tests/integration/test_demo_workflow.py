"""Integration tests for demo_terminal_workflow.

These tests perform REAL GUI actions on your desktop:
- Open a terminal window
- Type commands
- Capture screenshots
- Close the terminal

Run locally only: uv run pytest tests/integration/test_demo_workflow.py -v

Requirements:
- A display (X11, Wayland with XWayland, Windows, macOS)
- pyautogui installed
- A terminal application available (gnome-terminal, konsole, xterm, etc.)
- Optional: tesseract-ocr for OCR verification tests
"""

from __future__ import annotations

import platform

import pytest

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def ensure_gui():
    """Ensure GUI dependencies are available."""
    import pyautogui

    pyautogui.FAILSAFE = False
    yield pyautogui


class TestDemoTerminalWorkflow:
    """Tests for the demo_terminal_workflow convenience function."""

    def test_basic_workflow(self, ensure_gui):
        """Test basic terminal workflow with default parameters."""
        from ai_gaming_agent.tools.workflow import demo_terminal_workflow

        result = demo_terminal_workflow(text="echo hello world")

        # Check structure
        assert "success" in result
        assert "terminal_command" in result
        assert "platform" in result
        assert "text_typed" in result
        assert "steps_completed" in result
        assert "total_time_ms" in result
        assert "error" in result

        # Verify success
        assert result["success"] is True, f"Workflow failed: {result.get('error')}"
        assert result["text_typed"] == "echo hello world"
        assert result["platform"] == platform.system()
        assert result["terminal_command"] is not None

        # Check steps completed
        expected_steps = [
            "detect_terminal",
            "open_terminal",
            "wait_for_terminal",
            "type_text",
            "press_enter",
        ]
        for step in expected_steps:
            assert step in result["steps_completed"], f"Missing step: {step}"

        # Screenshot and close should be in there too (defaults are True)
        assert "capture_screenshot" in result["steps_completed"]
        assert "close_terminal" in result["steps_completed"]

        print(f"Workflow completed in {result['total_time_ms']}ms")
        print(f"Terminal used: {result['terminal_command']}")
        print(f"Steps: {result['steps_completed']}")

    def test_workflow_without_close(self, ensure_gui):
        """Test workflow that doesn't close the terminal."""
        from ai_gaming_agent.tools.keyboard import hotkey
        from ai_gaming_agent.tools.workflow import demo_terminal_workflow

        try:
            result = demo_terminal_workflow(
                text="echo test without close",
                close_terminal=False,
            )

            assert result["success"] is True, f"Workflow failed: {result.get('error')}"
            assert "close_terminal" not in result["steps_completed"]

            print("Workflow completed without closing terminal")

        finally:
            # Clean up - close the terminal manually
            import time

            time.sleep(0.5)
            if platform.system() == "Darwin":
                hotkey(keys=["cmd", "q"])
            else:
                hotkey(keys=["alt", "f4"])
            time.sleep(0.5)

    def test_workflow_without_screenshot(self, ensure_gui):
        """Test workflow that doesn't capture a screenshot."""
        from ai_gaming_agent.tools.workflow import demo_terminal_workflow

        result = demo_terminal_workflow(
            text="echo no screenshot test",
            capture_screenshot=False,
        )

        assert result["success"] is True, f"Workflow failed: {result.get('error')}"
        assert "capture_screenshot" not in result["steps_completed"]
        assert result["screenshot"] is None

        print("Workflow completed without screenshot")

    def test_workflow_custom_timings(self, ensure_gui):
        """Test workflow with custom timing parameters."""
        from ai_gaming_agent.tools.workflow import demo_terminal_workflow

        result = demo_terminal_workflow(
            text="echo custom timings",
            terminal_wait_ms=3000,
            post_type_wait_ms=800,
            post_enter_wait_ms=1500,
        )

        assert result["success"] is True, f"Workflow failed: {result.get('error')}"
        # With longer waits, total time should be at least 5 seconds
        assert result["total_time_ms"] >= 5000

        print(f"Workflow with custom timings completed in {result['total_time_ms']}ms")

    def test_workflow_with_screenshot_verification(self, ensure_gui):
        """Test workflow and verify screenshot was captured correctly."""
        from ai_gaming_agent.tools.workflow import demo_terminal_workflow

        result = demo_terminal_workflow(text="echo screenshot test")

        assert result["success"] is True, f"Workflow failed: {result.get('error')}"
        assert result["screenshot"] is not None
        assert result["screenshot"]["success"] is True
        assert "image" in result["screenshot"]
        assert result["screenshot"]["width"] > 0
        assert result["screenshot"]["height"] > 0

        # Verify image is substantial base64 data
        assert len(result["screenshot"]["image"]) > 1000

        print(f"Screenshot captured: {result['screenshot']['width']}x{result['screenshot']['height']}")


class TestDemoWorkflowWithOCR:
    """Tests that verify terminal output using OCR."""

    @pytest.fixture
    def ocr_available(self):
        """Check if tesseract is installed."""
        try:
            import pytesseract

            # Verify tesseract binary exists
            pytesseract.get_tesseract_version()
            return pytesseract
        except Exception as e:
            pytest.skip(f"Tesseract not available: {e}")

    def test_workflow_with_ocr_verification(self, ensure_gui, ocr_available):
        """Test workflow and verify output text appears using OCR."""
        import base64
        import io
        import uuid

        from PIL import Image

        from ai_gaming_agent.tools.workflow import demo_terminal_workflow

        # Generate unique string to verify
        unique_id = str(uuid.uuid4())[:8]
        expected_text = f"AGENT_TEST_{unique_id}"

        result = demo_terminal_workflow(
            text=f'echo "{expected_text}"',
            post_enter_wait_ms=1500,  # Give more time for output
        )

        assert result["success"] is True, f"Workflow failed: {result.get('error')}"
        assert result["screenshot"] is not None
        assert result["screenshot"]["success"] is True

        # Decode screenshot and run OCR
        image_data = base64.b64decode(result["screenshot"]["image"])
        image = Image.open(io.BytesIO(image_data))
        ocr_text = ocr_available.image_to_string(image)

        print(f"Looking for: {expected_text}")
        print(f"OCR found (first 500 chars): {ocr_text[:500]}")

        # Verify our unique text appears in OCR output
        # Note: OCR might have minor errors, so we check partial match
        assert expected_text in ocr_text or unique_id in ocr_text, f"Expected '{expected_text}' not found in OCR output"

        print("OCR verification passed!")


class TestDemoWorkflowPlatformDetection:
    """Tests for platform and terminal detection."""

    def test_detect_terminal_command(self):
        """Test that terminal detection works on current platform."""
        from ai_gaming_agent.tools.workflow import _detect_terminal_command

        terminal_cmd = _detect_terminal_command()

        system = platform.system()
        print(f"Platform: {system}")
        print(f"Detected terminal: {terminal_cmd}")

        if system == "Linux":
            # Should find at least one Linux terminal
            assert terminal_cmd is not None, "No terminal found on Linux"
            # Common Linux terminal names
            valid_terminals = [
                "gnome-terminal",
                "konsole",
                "xfce4-terminal",
                "mate-terminal",
                "tilix",
                "terminator",
                "xterm",
            ]
            assert terminal_cmd in valid_terminals, f"Unexpected terminal: {terminal_cmd}"

        elif system == "Darwin":
            assert terminal_cmd == "open -a Terminal"

        elif system == "Windows":
            assert terminal_cmd == "cmd"

    def test_get_close_terminal_keys(self):
        """Test that close hotkey detection works."""
        from ai_gaming_agent.tools.workflow import _get_close_terminal_keys

        keys = _get_close_terminal_keys()

        system = platform.system()
        print(f"Platform: {system}")
        print(f"Close keys: {keys}")

        if system == "Darwin":
            assert keys == ["cmd", "q"]
        else:
            assert keys == ["alt", "f4"]
