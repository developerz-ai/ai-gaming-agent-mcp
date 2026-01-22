"""Workflow automation tools.

This module provides composite tools that execute sequences of actions,
enabling single-command workflows like "open terminal, type command, close".
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


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
