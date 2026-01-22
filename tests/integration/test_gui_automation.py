"""Integration tests for GUI automation.

These tests perform REAL actions on your desktop:
- Take screenshots
- Move mouse
- Type text
- Open/close applications

Run locally only: uv run pytest tests/integration -v

Requirements:
- A display (X11, Wayland with XWayland, Windows, macOS)
- pyautogui and pytesseract installed
- tesseract-ocr system package (apt install tesseract-ocr)
"""

import platform
import subprocess
import time

import pytest

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def ensure_gui():
    """Ensure GUI dependencies are available."""
    import pyautogui

    pyautogui.FAILSAFE = False
    yield pyautogui


class TestScreenCapture:
    """Tests for screen capture functionality."""

    def test_screenshot_returns_image(self, ensure_gui):
        """Test that screenshot captures actual screen content."""
        from ai_gaming_agent.tools.screen import screenshot

        result = screenshot()

        assert result["success"] is True
        assert "image" in result
        assert result["width"] > 0
        assert result["height"] > 0
        assert len(result["image"]) > 1000  # Base64 should have substantial content

    def test_get_screen_size(self, ensure_gui):
        """Test screen size detection."""
        from ai_gaming_agent.tools.screen import get_screen_size

        result = get_screen_size()

        assert result["success"] is True
        assert result["width"] >= 800  # Minimum reasonable resolution
        assert result["height"] >= 600


class TestOCR:
    """Tests for OCR (Optical Character Recognition)."""

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

    def test_ocr_screen_content(self, ensure_gui, ocr_available):
        """Test OCR can read text from screen."""
        import base64
        import io

        from PIL import Image

        from ai_gaming_agent.tools.screen import screenshot

        # Take screenshot
        result = screenshot()
        assert result["success"] is True

        # Decode and run OCR
        image_data = base64.b64decode(result["image"])
        image = Image.open(io.BytesIO(image_data))

        text = ocr_available.image_to_string(image)

        # Should find some text on screen (desktop usually has something)
        # This is a basic sanity check - actual content varies
        assert isinstance(text, str)
        print(f"OCR detected text (first 200 chars): {text[:200]}")


class TestMouseControl:
    """Tests for mouse control."""

    def test_mouse_position(self, ensure_gui):
        """Test getting mouse position."""
        from ai_gaming_agent.tools.mouse import get_mouse_position

        result = get_mouse_position()

        assert result["success"] is True
        assert "x" in result
        assert "y" in result
        assert result["x"] >= 0
        assert result["y"] >= 0

    def test_mouse_move(self, ensure_gui):
        """Test moving mouse to position."""
        from ai_gaming_agent.tools.mouse import get_mouse_position, move_to

        # Move to known position
        result = move_to(100, 100, duration=0.1)
        assert result["success"] is True

        # Verify position
        time.sleep(0.1)
        pos = get_mouse_position()
        assert pos["success"] is True
        # Allow small tolerance for movement
        assert abs(pos["x"] - 100) < 5
        assert abs(pos["y"] - 100) < 5

    def test_mouse_click(self, ensure_gui):
        """Test mouse click (clicks in safe area)."""
        from ai_gaming_agent.tools.mouse import click, move_to
        from ai_gaming_agent.tools.screen import get_screen_size

        # Get screen size and click in center (usually safe)
        size = get_screen_size()
        center_x = size["width"] // 2
        center_y = size["height"] // 2

        # Move first, then click
        move_to(center_x, center_y, duration=0.1)
        time.sleep(0.1)

        result = click(center_x, center_y)
        assert result["success"] is True


class TestKeyboardControl:
    """Tests for keyboard control."""

    def test_type_text(self, ensure_gui):
        """Test typing text."""
        from ai_gaming_agent.tools.keyboard import type_text

        # Type something harmless
        result = type_text("test", interval=0.05)
        assert result["success"] is True

    def test_press_key(self, ensure_gui):
        """Test pressing a key."""
        from ai_gaming_agent.tools.keyboard import press_key

        # Press escape (generally safe)
        result = press_key("escape")
        assert result["success"] is True

    def test_hotkey(self, ensure_gui):
        """Test key combination."""
        from ai_gaming_agent.tools.keyboard import hotkey

        # Press Ctrl+A (select all - generally safe)
        result = hotkey(["ctrl", "a"])
        assert result["success"] is True


class TestTerminalAutomation:
    """End-to-end test: open terminal, type command, close."""

    def _get_terminal_command(self):
        """Get platform-specific terminal command."""
        system = platform.system()
        if system == "Linux":
            # Try common Linux terminals
            terminals = ["gnome-terminal", "konsole", "xterm", "xfce4-terminal"]
            for term in terminals:
                try:
                    subprocess.run(["which", term], check=True, capture_output=True)
                    return term
                except subprocess.CalledProcessError:
                    continue
            return None
        elif system == "Darwin":
            return "open -a Terminal"
        elif system == "Windows":
            return "cmd"
        return None

    def test_terminal_workflow(self, ensure_gui):
        """
        Full integration test: open terminal, type command, read output, close.

        This test:
        1. Opens a terminal window
        2. Types a simple command (echo)
        3. Waits for output
        4. Takes screenshot
        5. Closes terminal
        """
        from ai_gaming_agent.tools.keyboard import hotkey, press_key, type_text
        from ai_gaming_agent.tools.screen import screenshot

        terminal_cmd = self._get_terminal_command()
        if not terminal_cmd:
            pytest.skip("No supported terminal found")

        try:
            # Step 1: Open terminal
            print(f"Opening terminal: {terminal_cmd}")
            if platform.system() == "Linux":
                subprocess.Popen([terminal_cmd])
            else:
                subprocess.Popen(terminal_cmd, shell=True)

            time.sleep(2)  # Wait for terminal to open

            # Step 2: Type a command
            print("Typing command...")
            type_text('echo "Hello from AI Gaming Agent"', interval=0.02)
            time.sleep(0.3)

            # Step 3: Press Enter to execute
            press_key("enter")
            time.sleep(1)  # Wait for command to execute

            # Step 4: Take screenshot
            print("Taking screenshot...")
            result = screenshot()
            assert result["success"] is True
            print(f"Screenshot captured: {result['width']}x{result['height']}")

            # Step 5: Close terminal
            print("Closing terminal...")
            if platform.system() == "Darwin":
                hotkey(["cmd", "q"])
            else:
                hotkey(["alt", "f4"])

            time.sleep(0.5)
            print("Terminal workflow completed successfully!")

        except Exception as e:
            # Try to close terminal on error
            try:
                if platform.system() == "Darwin":
                    hotkey(["cmd", "q"])
                else:
                    hotkey(["alt", "f4"])
            except Exception:
                pass
            raise e

    def test_terminal_with_ocr_verification(self, ensure_gui):
        """
        Full integration test with OCR verification.

        This test:
        1. Opens a terminal
        2. Types a command with unique output
        3. Uses OCR to verify the output appeared
        4. Closes terminal
        """
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
        except Exception as e:
            pytest.skip(f"Tesseract not available: {e}")

        import base64
        import io
        import uuid

        from PIL import Image

        from ai_gaming_agent.tools.keyboard import hotkey, press_key, type_text
        from ai_gaming_agent.tools.screen import screenshot

        terminal_cmd = self._get_terminal_command()
        if not terminal_cmd:
            pytest.skip("No supported terminal found")

        # Generate unique string to verify
        unique_id = str(uuid.uuid4())[:8]
        expected_text = f"AGENT_TEST_{unique_id}"

        try:
            # Open terminal
            if platform.system() == "Linux":
                subprocess.Popen([terminal_cmd])
            else:
                subprocess.Popen(terminal_cmd, shell=True)
            time.sleep(2)

            # Type command with unique output
            type_text(f'echo "{expected_text}"', interval=0.02)
            time.sleep(0.3)
            press_key("enter")
            time.sleep(1)

            # Take screenshot and OCR
            result = screenshot()
            assert result["success"] is True

            image_data = base64.b64decode(result["image"])
            image = Image.open(io.BytesIO(image_data))
            ocr_text = pytesseract.image_to_string(image)

            print(f"Looking for: {expected_text}")
            print(f"OCR found (first 500 chars): {ocr_text[:500]}")

            # Verify our unique text appears in OCR output
            # Note: OCR might have minor errors, so we check partial match
            assert expected_text in ocr_text or unique_id in ocr_text, (
                f"Expected '{expected_text}' not found in OCR output"
            )

            # Close terminal
            if platform.system() == "Darwin":
                hotkey(["cmd", "q"])
            else:
                hotkey(["alt", "f4"])

            print("Terminal OCR verification completed successfully!")

        except Exception as e:
            try:
                if platform.system() == "Darwin":
                    hotkey(["cmd", "q"])
                else:
                    hotkey(["alt", "f4"])
            except Exception:
                pass
            raise e


class TestBatchOperations:
    """Test running multiple operations in sequence."""

    def test_batch_gui_operations(self, ensure_gui):
        """
        Run a batch of GUI operations in sequence.

        Operations:
        1. Get screen size
        2. Take screenshot
        3. Move mouse to center
        4. Click
        5. Type text
        6. Press escape
        7. Take final screenshot
        """
        from ai_gaming_agent.tools.keyboard import press_key, type_text
        from ai_gaming_agent.tools.mouse import click, move_to
        from ai_gaming_agent.tools.screen import get_screen_size, screenshot

        results = []

        # 1. Get screen size
        size_result = get_screen_size()
        results.append(("get_screen_size", size_result["success"]))
        assert size_result["success"]

        # 2. Take screenshot
        shot1 = screenshot()
        results.append(("screenshot_1", shot1["success"]))
        assert shot1["success"]

        # 3. Move mouse to center
        center_x = size_result["width"] // 2
        center_y = size_result["height"] // 2
        move_result = move_to(center_x, center_y, duration=0.2)
        results.append(("move_to_center", move_result["success"]))
        assert move_result["success"]

        time.sleep(0.2)

        # 4. Click
        click_result = click(center_x, center_y)
        results.append(("click", click_result["success"]))
        assert click_result["success"]

        time.sleep(0.2)

        # 5. Type text (harmless)
        type_result = type_text("test", interval=0.05)
        results.append(("type_text", type_result["success"]))
        assert type_result["success"]

        time.sleep(0.2)

        # 6. Press escape (cancel any dialogs)
        esc_result = press_key("escape")
        results.append(("press_escape", esc_result["success"]))
        assert esc_result["success"]

        time.sleep(0.2)

        # 7. Final screenshot
        shot2 = screenshot()
        results.append(("screenshot_2", shot2["success"]))
        assert shot2["success"]

        # Print summary
        print("\nBatch operations summary:")
        for op, success in results:
            status = "OK" if success else "FAIL"
            print(f"  {op}: {status}")

        # All should succeed
        assert all(success for _, success in results)
