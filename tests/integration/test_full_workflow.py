"""Full end-to-end integration tests for the AI Gaming Agent.

These tests perform a COMPLETE workflow:
1. Start the HTTP server in background
2. Connect via HTTP/SSE
3. Call demo_terminal_workflow("echo hello world")
4. Validate output with OCR (if available)
5. Clean up resources

Run locally only: uv run pytest tests/integration/test_full_workflow.py -v

Requirements:
- A display (X11, Wayland with XWayland, Windows, macOS)
- pyautogui installed
- A terminal application available
- Optional: tesseract-ocr for OCR verification
- httpx for HTTP client
"""

from __future__ import annotations

import multiprocessing
import platform
import socket
import time
from typing import Any, Generator

import pytest

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


def get_free_port() -> int:
    """Get a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def run_http_server(host: str, port: int, password: str, ready_event: Any) -> None:
    """Run the HTTP server in a subprocess.

    Args:
        host: Host to bind to.
        port: Port to bind to.
        password: Authentication password.
        ready_event: Event to signal when server is ready.
    """
    import asyncio
    import logging

    import uvicorn

    from ai_gaming_agent.config import Config
    from ai_gaming_agent.http_server import create_app

    # Set up minimal logging
    logging.basicConfig(level=logging.WARNING)

    # Create config with test settings
    config = Config()
    config.server.host = host
    config.server.port = port
    config.server.password = password

    # Create the app
    app = create_app(config)

    # Custom uvicorn server that signals when ready
    class ReadyServer(uvicorn.Server):
        def install_signal_handlers(self) -> None:
            # Don't install signal handlers in subprocess
            pass

        async def startup(self, sockets: list | None = None) -> None:
            await super().startup(sockets)
            ready_event.set()

    # Run the server
    server_config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",
        loop="asyncio",
    )
    server = ReadyServer(server_config)
    asyncio.run(server.serve())


@pytest.fixture
def ensure_gui():
    """Ensure GUI dependencies are available."""
    import pyautogui

    pyautogui.FAILSAFE = False
    yield pyautogui


@pytest.fixture
def http_server() -> Generator[dict[str, Any], None, None]:
    """Start HTTP server in background and return connection info.

    Yields:
        Dictionary with 'host', 'port', 'password', and 'base_url'.
    """
    host = "127.0.0.1"
    port = get_free_port()
    password = "test-integration-password"

    # Use multiprocessing to run server in separate process
    ready_event = multiprocessing.Event()
    server_process = multiprocessing.Process(
        target=run_http_server,
        args=(host, port, password, ready_event),
        daemon=True,
    )
    server_process.start()

    # Wait for server to be ready (up to 10 seconds)
    if not ready_event.wait(timeout=10):
        server_process.terminate()
        server_process.join(timeout=5)
        pytest.fail("Server failed to start within 10 seconds")

    # Give it a moment to fully initialize
    time.sleep(0.5)

    yield {
        "host": host,
        "port": port,
        "password": password,
        "base_url": f"http://{host}:{port}",
    }

    # Cleanup
    server_process.terminate()
    server_process.join(timeout=5)
    if server_process.is_alive():
        server_process.kill()
        server_process.join(timeout=2)


class TestHttpServerIntegration:
    """Tests for HTTP server connectivity and health."""

    def test_server_health_endpoint(self, http_server: dict[str, Any]):
        """Test that the HTTP server responds to health checks."""
        import httpx

        response = httpx.get(f"{http_server['base_url']}/health", timeout=5.0)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

        print(f"Server health: {data}")

    def test_server_requires_auth_for_mcp(self, http_server: dict[str, Any]):
        """Test that MCP endpoint requires authentication."""
        import httpx

        response = httpx.get(f"{http_server['base_url']}/mcp", timeout=5.0)

        # Should reject without auth
        assert response.status_code in [401, 403]

    def test_server_accepts_valid_auth(self, http_server: dict[str, Any]):
        """Test that MCP endpoint accepts valid authentication."""
        import httpx

        headers = {"Authorization": f"Bearer {http_server['password']}"}

        # For SSE endpoint, we can't fully test without async SSE client
        # but we can verify auth doesn't reject with valid token
        # The endpoint might return 500 if SSE setup fails but not 401/403
        response = httpx.get(
            f"{http_server['base_url']}/mcp",
            headers=headers,
            timeout=5.0,
        )

        # With valid auth, we should NOT get 401/403
        assert response.status_code not in [401, 403], f"Auth should be accepted, got {response.status_code}"


class TestDirectWorkflowExecution:
    """Tests that call workflow functions directly (bypassing HTTP for reliability)."""

    def test_demo_terminal_workflow_direct(self, ensure_gui):
        """Test the demo_terminal_workflow function directly.

        This test validates the core functionality without the HTTP layer,
        ensuring the terminal workflow works on the current platform.
        """
        from ai_gaming_agent.tools.workflow import demo_terminal_workflow

        result = demo_terminal_workflow(text="echo hello world")

        # Verify result structure
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
            "capture_screenshot",
            "close_terminal",
        ]
        for step in expected_steps:
            assert step in result["steps_completed"], f"Missing step: {step}"

        print(f"Workflow completed successfully in {result['total_time_ms']}ms")
        print(f"Terminal used: {result['terminal_command']}")
        print(f"Platform: {result['platform']}")
        print(f"Steps: {', '.join(result['steps_completed'])}")

    def test_run_workflow_terminal_sequence(self, ensure_gui):
        """Test run_workflow with a terminal automation sequence.

        This tests the generic run_workflow function with a sequence
        of steps that mimics the terminal workflow.
        """
        from ai_gaming_agent.tools.workflow import _detect_terminal_command, _get_close_terminal_keys, run_workflow

        # Detect terminal for this platform
        terminal_cmd = _detect_terminal_command()
        if terminal_cmd is None:
            pytest.skip("No terminal detected for this platform")

        close_keys = _get_close_terminal_keys()

        # Build the workflow steps
        steps = [
            {
                "tool": "execute_command",
                "args": {"command": terminal_cmd},
                "wait_ms": 2000,
                "description": "Open terminal",
            },
            {
                "tool": "type_text",
                "args": {"text": "echo workflow test", "interval": 0.02},
                "wait_ms": 300,
                "description": "Type command",
            },
            {
                "tool": "press_key",
                "args": {"key": "enter"},
                "wait_ms": 1000,
                "description": "Execute command",
            },
            {
                "tool": "screenshot",
                "args": {},
                "wait_ms": 100,
                "description": "Capture result",
            },
            {
                "tool": "hotkey",
                "args": {"keys": close_keys},
                "wait_ms": 500,
                "description": "Close terminal",
            },
        ]

        result = run_workflow(steps=steps)

        # Verify workflow completed
        assert result["success"] is True, f"Workflow failed at step {result.get('failed_step')}: {result.get('error')}"
        assert result["total_steps"] == 5
        assert result["completed_steps"] == 5
        assert result["failed_step"] is None

        # Check each step result
        for i, step_result in enumerate(result["results"]):
            assert step_result["success"], f"Step {i} ({step_result['tool']}) failed: {step_result.get('error')}"

        print(f"Workflow completed in {result['total_time_ms']}ms")
        print(f"Steps executed: {result['completed_steps']}/{result['total_steps']}")


class TestWorkflowWithOcrVerification:
    """Tests that verify workflow output using OCR."""

    @pytest.fixture
    def ocr_available(self):
        """Check if tesseract is installed."""
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
            return pytesseract
        except Exception as e:
            pytest.skip(f"Tesseract not available: {e}")

    def test_workflow_output_verification(self, ensure_gui, ocr_available):
        """Test workflow and verify output text appears using OCR.

        This is the full end-to-end test:
        1. Run demo_terminal_workflow with a unique string
        2. Capture screenshot
        3. Use OCR to verify the string appeared
        """
        import base64
        import io
        import uuid

        from PIL import Image

        from ai_gaming_agent.tools.workflow import demo_terminal_workflow

        # Generate unique string to verify
        unique_id = str(uuid.uuid4())[:8]
        expected_text = f"E2E_TEST_{unique_id}"

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
        # Check for either full text or just the UUID part (OCR might have errors)
        found = expected_text in ocr_text or unique_id in ocr_text

        assert found, f"Expected '{expected_text}' not found in OCR output. OCR text: {ocr_text[:200]}..."

        print("OCR verification passed!")
        print(f"Full workflow completed in {result['total_time_ms']}ms")


class TestWorkflowEdgeCases:
    """Tests for workflow edge cases and error handling."""

    def test_workflow_with_invalid_tool(self, ensure_gui):
        """Test that workflow handles invalid tool names gracefully."""
        from ai_gaming_agent.tools.workflow import run_workflow

        steps = [
            {"tool": "nonexistent_tool", "args": {}},
        ]

        result = run_workflow(steps=steps)

        assert result["success"] is False
        assert result["failed_step"] == 0
        assert "Unknown tool" in result["error"]

    def test_workflow_with_continue_on_error(self, ensure_gui):
        """Test that continue_on_error allows workflow to proceed."""
        from ai_gaming_agent.tools.workflow import run_workflow

        steps = [
            {
                "tool": "nonexistent_tool",
                "args": {},
                "continue_on_error": True,
                "description": "This will fail",
            },
            {
                "tool": "get_screen_size",
                "args": {},
                "description": "This should still run",
            },
        ]

        result = run_workflow(steps=steps)

        # Workflow should complete even though first step failed
        assert result["success"] is True
        assert result["total_steps"] == 2
        assert result["completed_steps"] == 1  # Only second step succeeded
        assert result["failed_step"] is None  # No hard failure

    def test_empty_workflow(self, ensure_gui):
        """Test that empty workflow is handled."""
        from ai_gaming_agent.tools.workflow import run_workflow

        result = run_workflow(steps=[])

        assert result["success"] is False
        assert "No steps provided" in result["error"]


class TestBatchGuiOperations:
    """Test running multiple GUI operations as a batch workflow."""

    def test_batch_mouse_keyboard_operations(self, ensure_gui):
        """Test a batch of mouse and keyboard operations via workflow."""
        from ai_gaming_agent.tools.screen import get_screen_size
        from ai_gaming_agent.tools.workflow import run_workflow

        # Get screen size first
        size = get_screen_size()
        center_x = size["width"] // 2
        center_y = size["height"] // 2

        steps = [
            {
                "tool": "get_screen_size",
                "args": {},
                "description": "Get screen dimensions",
            },
            {
                "tool": "screenshot",
                "args": {},
                "description": "Initial screenshot",
            },
            {
                "tool": "move_to",
                "args": {"x": center_x, "y": center_y, "duration": 0.2},
                "wait_ms": 200,
                "description": "Move to center",
            },
            {
                "tool": "click",
                "args": {"x": center_x, "y": center_y},
                "wait_ms": 100,
                "description": "Click center",
            },
            {
                "tool": "press_key",
                "args": {"key": "escape"},
                "wait_ms": 100,
                "description": "Press escape",
            },
            {
                "tool": "screenshot",
                "args": {},
                "description": "Final screenshot",
            },
        ]

        result = run_workflow(steps=steps)

        assert result["success"] is True, f"Batch failed: {result.get('error')}"
        assert result["total_steps"] == 6
        assert result["completed_steps"] == 6

        print(f"Batch operations completed in {result['total_time_ms']}ms")

        # Print step summary
        for i, step_result in enumerate(result["results"]):
            status = "OK" if step_result["success"] else "FAIL"
            print(f"  Step {i + 1} ({step_result['tool']}): {status} ({step_result['time_ms']}ms)")


class TestPlatformCompatibility:
    """Tests for platform-specific functionality."""

    def test_terminal_detection(self):
        """Test that terminal detection works on current platform."""
        from ai_gaming_agent.tools.workflow import _detect_terminal_command

        terminal = _detect_terminal_command()
        system = platform.system()

        print(f"Platform: {system}")
        print(f"Detected terminal: {terminal}")

        if system == "Linux":
            assert terminal is not None, "No terminal found on Linux"
            valid_terminals = [
                "gnome-terminal",
                "konsole",
                "xfce4-terminal",
                "mate-terminal",
                "tilix",
                "terminator",
                "xterm",
            ]
            assert terminal in valid_terminals, f"Unexpected terminal: {terminal}"
        elif system == "Darwin":
            assert terminal == "open -a Terminal"
        elif system == "Windows":
            assert terminal == "cmd"

    def test_close_hotkey_detection(self):
        """Test that close hotkey is correct for platform."""
        from ai_gaming_agent.tools.workflow import _get_close_terminal_keys

        keys = _get_close_terminal_keys()
        system = platform.system()

        print(f"Platform: {system}")
        print(f"Close keys: {keys}")

        if system == "Darwin":
            assert keys == ["cmd", "q"]
        else:
            assert keys == ["alt", "f4"]


class TestFullE2EWithHttpServer:
    """Full end-to-end tests using the HTTP server.

    These tests start the HTTP server, connect as a client,
    and exercise the full MCP flow.
    """

    def test_health_and_workflow(self, ensure_gui, http_server: dict[str, Any]):
        """Test complete flow: health check followed by workflow execution.

        This test validates:
        1. HTTP server is running and healthy
        2. Authentication works
        3. The server is ready to handle MCP requests
        """
        import httpx

        # Step 1: Verify health
        health_response = httpx.get(f"{http_server['base_url']}/health", timeout=5.0)
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert health_data["status"] == "ok"

        print(f"Server health OK: version {health_data['version']}")

        # Step 2: Verify auth works
        headers = {"Authorization": f"Bearer {http_server['password']}"}
        auth_response = httpx.get(
            f"{http_server['base_url']}/mcp",
            headers=headers,
            timeout=5.0,
        )
        # Should not be rejected for auth reasons
        assert auth_response.status_code not in [401, 403]

        print("Authentication accepted")

        # Step 3: Run workflow directly (since MCP SSE is complex to test)
        # This validates the workflow tools work in the context of the running server
        from ai_gaming_agent.tools.workflow import demo_terminal_workflow

        result = demo_terminal_workflow(text="echo e2e http test")

        assert result["success"] is True, f"Workflow failed: {result.get('error')}"

        print(f"Workflow completed: {result['total_time_ms']}ms")
        print(f"Steps: {', '.join(result['steps_completed'])}")

    def test_concurrent_requests(self, http_server: dict[str, Any]):
        """Test that server handles multiple concurrent health checks."""
        import concurrent.futures

        import httpx

        def make_health_request() -> dict:
            response = httpx.get(f"{http_server['base_url']}/health", timeout=5.0)
            return {"status_code": response.status_code, "data": response.json()}

        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_health_request) for _ in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        for result in results:
            assert result["status_code"] == 200
            assert result["data"]["status"] == "ok"

        print(f"All {len(results)} concurrent requests succeeded")
