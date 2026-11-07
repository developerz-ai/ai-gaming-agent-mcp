"""Workflow automation tools.

This module provides composite tools that execute sequences of actions,
enabling single-command workflows like "open terminal, type command, close".
"""

from __future__ import annotations

import logging
import platform
import subprocess
import time
from typing import Any

logger = logging.getLogger(__name__)


def _detect_terminal_command() -> str | None:
    """Detect the appropriate terminal command for the current platform.

    Returns:
        Terminal command string, or None if no terminal found.
    """
    system = platform.system()

    if system == "Linux":
        # Try common Linux terminals in order of preference
        terminals = [
            "gnome-terminal",
            "konsole",
            "xfce4-terminal",
            "mate-terminal",
            "tilix",
            "terminator",
            "xterm",
        ]
        for term in terminals:
            try:
                result = subprocess.run(
                    ["which", term],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return term
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        return None

    elif system == "Darwin":
        # macOS - use Terminal.app
        return "open -a Terminal"

    elif system == "Windows":
        # Windows - use cmd
        return "cmd"

    return None


def _get_close_terminal_keys() -> list[str]:
    """Get the hotkey to close a terminal window for current platform.

    Returns:
        List of keys to press together to close terminal.
    """
    system = platform.system()
    if system == "Darwin":
        return ["cmd", "q"]
    else:
        # Linux and Windows both use Alt+F4
        return ["alt", "f4"]


def _get_tool_handler(tool_name: str) -> Any | None:
    """Get the handler function for a tool by name.

    Uses lazy import to avoid circular dependencies and loading
    GUI modules unnecessarily.

    Args:
        tool_name: Name of the tool to get handler for.

    Returns:
        The tool function, or None if not found.
    """
    # Map of tool names to their module paths
    tool_modules = {
        # Screen tools
        "screenshot": ("ai_gaming_agent.tools.screen", "screenshot"),
        "get_screen_size": ("ai_gaming_agent.tools.screen", "get_screen_size"),
        # Mouse tools
        "click": ("ai_gaming_agent.tools.mouse", "click"),
        "double_click": ("ai_gaming_agent.tools.mouse", "double_click"),
        "move_to": ("ai_gaming_agent.tools.mouse", "move_to"),
        "drag_to": ("ai_gaming_agent.tools.mouse", "drag_to"),
        "scroll": ("ai_gaming_agent.tools.mouse", "scroll"),
        "get_mouse_position": ("ai_gaming_agent.tools.mouse", "get_mouse_position"),
        # Keyboard tools
        "type_text": ("ai_gaming_agent.tools.keyboard", "type_text"),
        "press_key": ("ai_gaming_agent.tools.keyboard", "press_key"),
        "hotkey": ("ai_gaming_agent.tools.keyboard", "hotkey"),
        # File tools
        "read_file": ("ai_gaming_agent.tools.files", "read_file"),
        "write_file": ("ai_gaming_agent.tools.files", "write_file"),
        "list_files": ("ai_gaming_agent.tools.files", "list_files"),
        "upload_file": ("ai_gaming_agent.tools.files", "upload_file"),
        "download_file": ("ai_gaming_agent.tools.files", "download_file"),
        # System tools
        "execute_command": ("ai_gaming_agent.tools.system", "execute_command"),
        "get_system_info": ("ai_gaming_agent.tools.system", "get_system_info"),
        "list_windows": ("ai_gaming_agent.tools.system", "list_windows"),
        "focus_window": ("ai_gaming_agent.tools.system", "focus_window"),
    }

    if tool_name not in tool_modules:
        return None

    module_path, func_name = tool_modules[tool_name]

    try:
        import importlib

        module = importlib.import_module(module_path)
        return getattr(module, func_name)
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to import tool {tool_name}: {e}")
        return None


def run_workflow(steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Execute a sequence of tool actions as a single workflow.

    This function allows you to chain multiple tool calls together,
    executing them sequentially with optional delays between steps.
    It's useful for complex automation tasks that require multiple
    coordinated actions.

    Args:
        steps: List of step dictionaries, each containing:
            - tool (str): Name of the tool to call (required)
            - args (dict): Arguments to pass to the tool (optional, default: {})
            - wait_ms (int): Milliseconds to wait after this step (optional, default: 0)
            - description (str): Human-readable description of the step (optional)
            - continue_on_error (bool): Continue workflow if this step fails (optional, default: False)

    Returns:
        Dictionary containing:
            - success (bool): True if all steps succeeded (or continued on error)
            - total_steps (int): Number of steps in the workflow
            - completed_steps (int): Number of steps that completed
            - failed_step (int | None): Index of first failed step (if any)
            - results (list): List of results from each step
            - total_time_ms (int): Total execution time in milliseconds
            - error (str | None): Error message if workflow failed

    Example:
        >>> run_workflow([
        ...     {"tool": "execute_command", "args": {"command": "gnome-terminal"}, "wait_ms": 1000},
        ...     {"tool": "type_text", "args": {"text": "echo hello"}, "wait_ms": 100},
        ...     {"tool": "press_key", "args": {"key": "enter"}},
        ...     {"tool": "hotkey", "args": {"keys": ["alt", "F4"]}}
        ... ])
        {'success': True, 'total_steps': 4, 'completed_steps': 4, ...}
    """
    if not steps:
        return {
            "success": False,
            "error": "No steps provided",
            "total_steps": 0,
            "completed_steps": 0,
            "failed_step": None,
            "results": [],
            "total_time_ms": 0,
        }

    if not isinstance(steps, list):
        return {
            "success": False,
            "error": "Steps must be a list",
            "total_steps": 0,
            "completed_steps": 0,
            "failed_step": None,
            "results": [],
            "total_time_ms": 0,
        }

    results: list[dict[str, Any]] = []
    start_time = time.time()
    failed_step: int | None = None
    workflow_success = True

    for i, step in enumerate(steps):
        step_result: dict[str, Any] = {
            "step_index": i,
            "tool": None,
            "description": step.get("description", f"Step {i + 1}"),
            "success": False,
            "result": None,
            "error": None,
            "time_ms": 0,
        }

        step_start = time.time()

        try:
            # Validate step structure
            if not isinstance(step, dict):
                step_result["error"] = f"Step {i} must be a dictionary"
                step_result["time_ms"] = int((time.time() - step_start) * 1000)
                results.append(step_result)
                failed_step = i
                workflow_success = False
                break

            tool_name = step.get("tool")
            if not tool_name:
                step_result["error"] = f"Step {i} missing 'tool' field"
                results.append(step_result)
                if not step.get("continue_on_error", False):
                    failed_step = i
                    workflow_success = False
                    break
                continue

            step_result["tool"] = tool_name

            # Get tool handler
            handler = _get_tool_handler(tool_name)
            if handler is None:
                step_result["error"] = f"Unknown tool: {tool_name}"
                results.append(step_result)
                if not step.get("continue_on_error", False):
                    failed_step = i
                    workflow_success = False
                    break
                continue

            # Execute tool with args
            args = step.get("args", {})
            if not isinstance(args, dict):
                step_result["error"] = f"Step {i} 'args' must be a dictionary"
                results.append(step_result)
                if not step.get("continue_on_error", False):
                    failed_step = i
                    workflow_success = False
                    break
                continue

            logger.debug(f"Executing step {i}: {tool_name}({args})")
            result = handler(**args)

            step_result["result"] = result
            step_result["success"] = result.get("success", False) if isinstance(result, dict) else True

            # Check if tool reported failure
            if isinstance(result, dict) and not result.get("success", True):
                if not step.get("continue_on_error", False):
                    step_result["error"] = result.get("error", "Tool returned failure")
                    failed_step = i
                    workflow_success = False
                    step_result["time_ms"] = int((time.time() - step_start) * 1000)
                    results.append(step_result)
                    break

        except Exception as e:
            step_result["error"] = str(e)
            logger.exception(f"Step {i} ({step.get('tool', 'unknown')}) failed with exception")
            if not step.get("continue_on_error", False):
                failed_step = i
                workflow_success = False
                step_result["time_ms"] = int((time.time() - step_start) * 1000)
                results.append(step_result)
                break

        step_result["time_ms"] = int((time.time() - step_start) * 1000)
        results.append(step_result)

        # Apply wait_ms delay after successful step
        wait_ms = step.get("wait_ms", 0)
        if wait_ms > 0 and step_result["success"]:
            time.sleep(wait_ms / 1000.0)

    total_time_ms = int((time.time() - start_time) * 1000)
    completed_steps = sum(1 for r in results if r.get("success", False))

    return {
        "success": workflow_success,
        "total_steps": len(steps),
        "completed_steps": completed_steps,
        "failed_step": failed_step,
        "results": results,
        "total_time_ms": total_time_ms,
        "error": results[failed_step]["error"] if failed_step is not None else None,
    }


def demo_terminal_workflow(
    text: str = "echo hello world",
    terminal_wait_ms: int = 2000,
    post_type_wait_ms: int = 500,
    post_enter_wait_ms: int = 1000,
    capture_screenshot: bool = True,
    close_terminal: bool = True,
) -> dict[str, Any]:
    """Execute a complete terminal workflow: open, type, execute, screenshot, close.

    This is a convenience function that demonstrates the full automation capability
    by performing a complete terminal workflow in a single call. It:
    1. Detects the appropriate terminal application for the platform
    2. Opens the terminal
    3. Waits for it to fully load
    4. Types the provided text (command)
    5. Presses Enter to execute the command
    6. Waits for command output
    7. Optionally captures a screenshot for verification
    8. Optionally closes the terminal window

    Args:
        text: The text/command to type in the terminal. Defaults to "echo hello world".
        terminal_wait_ms: Milliseconds to wait for terminal to open. Defaults to 2000.
        post_type_wait_ms: Milliseconds to wait after typing. Defaults to 500.
        post_enter_wait_ms: Milliseconds to wait after pressing Enter. Defaults to 1000.
        capture_screenshot: Whether to take a screenshot after command execution.
                           Defaults to True.
        close_terminal: Whether to close the terminal at the end. Defaults to True.

    Returns:
        Dictionary containing:
            - success (bool): True if all steps completed successfully
            - terminal_command (str): The terminal application used
            - platform (str): The operating system
            - text_typed (str): The text that was typed
            - screenshot (dict | None): Screenshot result if captured, else None
            - steps_completed (list[str]): List of completed step names
            - total_time_ms (int): Total execution time in milliseconds
            - error (str | None): Error message if any step failed

    Example:
        >>> demo_terminal_workflow("echo hello world")
        {
            'success': True,
            'terminal_command': 'gnome-terminal',
            'platform': 'Linux',
            'text_typed': 'echo hello world',
            'screenshot': {'success': True, 'image': '...', ...},
            'steps_completed': ['detect_terminal', 'open_terminal', 'wait_for_terminal',
                               'type_text', 'press_enter', 'capture_screenshot',
                               'close_terminal'],
            'total_time_ms': 4523,
            'error': None
        }

        >>> demo_terminal_workflow("ls -la", close_terminal=False)
        {
            'success': True,
            ...
            'steps_completed': ['detect_terminal', 'open_terminal', 'wait_for_terminal',
                               'type_text', 'press_enter', 'capture_screenshot'],
            ...
        }
    """
    start_time = time.time()
    steps_completed: list[str] = []
    screenshot_result: dict[str, Any] | None = None
    current_platform = platform.system()

    result: dict[str, Any] = {
        "success": False,
        "terminal_command": None,
        "platform": current_platform,
        "text_typed": text,
        "screenshot": None,
        "steps_completed": steps_completed,
        "total_time_ms": 0,
        "error": None,
    }

    try:
        # Step 1: Detect terminal command
        terminal_cmd = _detect_terminal_command()
        if not terminal_cmd:
            result["error"] = f"No supported terminal found for platform: {current_platform}"
            result["total_time_ms"] = int((time.time() - start_time) * 1000)
            return result

        result["terminal_command"] = terminal_cmd
        steps_completed.append("detect_terminal")
        logger.debug(f"Detected terminal: {terminal_cmd}")

        # Step 2: Open terminal
        try:
            if current_platform == "Linux":
                subprocess.Popen([terminal_cmd])
            else:
                subprocess.Popen(terminal_cmd, shell=True)
            steps_completed.append("open_terminal")
            logger.debug("Terminal process started")
        except Exception as e:
            result["error"] = f"Failed to open terminal: {e}"
            result["total_time_ms"] = int((time.time() - start_time) * 1000)
            return result

        # Step 3: Wait for terminal to fully load
        time.sleep(terminal_wait_ms / 1000.0)
        steps_completed.append("wait_for_terminal")
        logger.debug(f"Waited {terminal_wait_ms}ms for terminal")

        # Step 4: Type the text
        # Import lazily to avoid GUI dependency issues in CI
        type_text_handler = _get_tool_handler("type_text")
        if type_text_handler is None:
            result["error"] = "Failed to load type_text tool"
            result["total_time_ms"] = int((time.time() - start_time) * 1000)
            return result

        type_result = type_text_handler(text=text, interval=0.02)
        if not type_result.get("success", False):
            result["error"] = f"Failed to type text: {type_result.get('error', 'Unknown error')}"
            result["total_time_ms"] = int((time.time() - start_time) * 1000)
            return result

        steps_completed.append("type_text")
        logger.debug(f"Typed text: {text}")

        # Wait after typing
        time.sleep(post_type_wait_ms / 1000.0)

        # Step 5: Press Enter to execute the command
        press_key_handler = _get_tool_handler("press_key")
        if press_key_handler is None:
            result["error"] = "Failed to load press_key tool"
            result["total_time_ms"] = int((time.time() - start_time) * 1000)
            return result

        enter_result = press_key_handler(key="enter")
        if not enter_result.get("success", False):
            result["error"] = f"Failed to press Enter: {enter_result.get('error', 'Unknown error')}"
            result["total_time_ms"] = int((time.time() - start_time) * 1000)
            return result

        steps_completed.append("press_enter")
        logger.debug("Pressed Enter")

        # Wait for command to execute
        time.sleep(post_enter_wait_ms / 1000.0)

        # Step 6: Capture screenshot if requested
        if capture_screenshot:
            screenshot_handler = _get_tool_handler("screenshot")
            if screenshot_handler is not None:
                screenshot_result = screenshot_handler()
                result["screenshot"] = screenshot_result
                if screenshot_result.get("success", False):
                    steps_completed.append("capture_screenshot")
                    logger.debug(
                        f"Screenshot captured: {screenshot_result.get('width')}x{screenshot_result.get('height')}"
                    )
                else:
                    logger.warning(f"Screenshot failed: {screenshot_result.get('error', 'Unknown error')}")
            else:
                logger.warning("Screenshot tool not available")

        # Step 7: Close terminal if requested
        if close_terminal:
            hotkey_handler = _get_tool_handler("hotkey")
            if hotkey_handler is not None:
                close_keys = _get_close_terminal_keys()
                close_result = hotkey_handler(keys=close_keys)
                if close_result.get("success", False):
                    steps_completed.append("close_terminal")
                    logger.debug(f"Terminal closed with hotkey: {close_keys}")
                else:
                    logger.warning(f"Failed to close terminal: {close_result.get('error', 'Unknown error')}")
            else:
                logger.warning("Hotkey tool not available")

        # Success!
        result["success"] = True
        result["total_time_ms"] = int((time.time() - start_time) * 1000)
        logger.info(f"Terminal workflow completed successfully in {result['total_time_ms']}ms")
        return result

    except Exception as e:
        result["error"] = str(e)
        result["total_time_ms"] = int((time.time() - start_time) * 1000)
        logger.exception("Terminal workflow failed with exception")

        # Try to close terminal on error if we opened it
        if "open_terminal" in steps_completed and close_terminal:
            try:
                hotkey_handler = _get_tool_handler("hotkey")
                if hotkey_handler is not None:
                    close_keys = _get_close_terminal_keys()
                    hotkey_handler(keys=close_keys)
                    logger.debug("Closed terminal after error")
            except Exception:
                pass

        return result
