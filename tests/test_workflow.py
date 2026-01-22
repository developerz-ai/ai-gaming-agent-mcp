"""Tests for workflow tools.

These tests use mocked tool functions to verify the run_workflow()
function logic without requiring actual GUI automation.
"""

from unittest.mock import MagicMock, patch

import pytest

from ai_gaming_agent.tools.workflow import run_workflow


@pytest.fixture
def mock_tool_handler():
    """Create a mock tool handler that returns success."""

    def _handler(**kwargs):
        return {"success": True, "result": "mock_result", **kwargs}

    return _handler


@pytest.fixture
def mock_failing_handler():
    """Create a mock tool handler that returns failure."""

    def _handler(**kwargs):
        return {"success": False, "error": "mock_error"}

    return _handler


def test_empty_steps():
    """Test workflow with no steps."""
    result = run_workflow([])

    assert result["success"] is False
    assert result["error"] == "No steps provided"
    assert result["total_steps"] == 0
    assert result["completed_steps"] == 0
    assert result["failed_step"] is None
    assert result["results"] == []


def test_invalid_steps_not_list():
    """Test workflow with invalid steps (not a list)."""
    result = run_workflow("not a list")  # type: ignore

    assert result["success"] is False
    assert result["error"] == "Steps must be a list"
    assert result["total_steps"] == 0


def test_invalid_step_not_dict():
    """Test workflow with a step that is not a dictionary.

    Note: Currently, the workflow code calls step.get() before checking if step is a dict,
    which causes an unhandled AttributeError. This test verifies that the exception is raised.
    This is a known limitation that should be fixed in the workflow implementation.
    """
    with pytest.raises(AttributeError, match="has no attribute 'get'"):
        run_workflow(["not a dict"])  # type: ignore


def test_step_missing_tool_field():
    """Test workflow with a step missing the 'tool' field."""
    result = run_workflow([{"args": {"x": 100}}])

    assert result["success"] is False
    assert result["completed_steps"] == 0
    assert result["failed_step"] == 0
    assert "missing 'tool' field" in result["results"][0]["error"]


def test_step_with_unknown_tool():
    """Test workflow with an unknown tool name."""
    with patch("ai_gaming_agent.tools.workflow._get_tool_handler", return_value=None):
        result = run_workflow([{"tool": "unknown_tool", "args": {}}])

        assert result["success"] is False
        assert result["completed_steps"] == 0
        assert result["failed_step"] == 0
        assert "Unknown tool" in result["results"][0]["error"]


def test_step_with_invalid_args():
    """Test workflow with invalid args (not a dict)."""
    with patch("ai_gaming_agent.tools.workflow._get_tool_handler") as mock_get:
        mock_get.return_value = MagicMock()
        result = run_workflow([{"tool": "click", "args": "not a dict"}])  # type: ignore

        assert result["success"] is False
        assert result["completed_steps"] == 0
        assert result["failed_step"] == 0
        assert "'args' must be a dictionary" in result["results"][0]["error"]


def test_successful_single_step(mock_tool_handler):
    """Test workflow with a single successful step."""
    with patch("ai_gaming_agent.tools.workflow._get_tool_handler", return_value=mock_tool_handler):
        result = run_workflow([{"tool": "click", "args": {"x": 100, "y": 200}}])

        assert result["success"] is True
        assert result["total_steps"] == 1
        assert result["completed_steps"] == 1
        assert result["failed_step"] is None
        assert len(result["results"]) == 1
        assert result["results"][0]["success"] is True
        assert result["results"][0]["tool"] == "click"
        assert result["results"][0]["result"]["x"] == 100
        assert result["results"][0]["result"]["y"] == 200


def test_successful_multiple_steps(mock_tool_handler):
    """Test workflow with multiple successful steps."""
    with patch("ai_gaming_agent.tools.workflow._get_tool_handler", return_value=mock_tool_handler):
        steps = [
            {"tool": "click", "args": {"x": 100, "y": 200}},
            {"tool": "type_text", "args": {"text": "hello"}},
            {"tool": "press_key", "args": {"key": "enter"}},
        ]
        result = run_workflow(steps)

        assert result["success"] is True
        assert result["total_steps"] == 3
        assert result["completed_steps"] == 3
        assert result["failed_step"] is None
        assert len(result["results"]) == 3

        # Verify each step was executed
        assert result["results"][0]["tool"] == "click"
        assert result["results"][1]["tool"] == "type_text"
        assert result["results"][2]["tool"] == "press_key"


def test_step_execution_order(mock_tool_handler):
    """Test that steps are executed in the correct order."""
    call_order = []

    def tracking_handler(**kwargs):
        call_order.append(kwargs.get("step_id"))
        return {"success": True}

    with patch("ai_gaming_agent.tools.workflow._get_tool_handler", return_value=tracking_handler):
        steps = [
            {"tool": "step1", "args": {"step_id": "first"}},
            {"tool": "step2", "args": {"step_id": "second"}},
            {"tool": "step3", "args": {"step_id": "third"}},
        ]
        result = run_workflow(steps)

        assert result["success"] is True
        assert call_order == ["first", "second", "third"]


def test_workflow_stops_on_failure(mock_tool_handler, mock_failing_handler):
    """Test that workflow stops when a step fails."""
    handlers = [mock_tool_handler, mock_failing_handler, mock_tool_handler]
    handler_index = 0

    def get_handler(tool_name):
        nonlocal handler_index
        handler = handlers[handler_index]
        handler_index += 1
        return handler

    with patch("ai_gaming_agent.tools.workflow._get_tool_handler", side_effect=get_handler):
        steps = [
            {"tool": "step1", "args": {}},
            {"tool": "step2", "args": {}},  # This will fail
            {"tool": "step3", "args": {}},  # This should not execute
        ]
        result = run_workflow(steps)

        assert result["success"] is False
        assert result["total_steps"] == 3
        assert result["completed_steps"] == 1  # Only first step succeeded
        assert result["failed_step"] == 1
        assert len(result["results"]) == 2  # Only first two steps executed
        assert result["error"] == "mock_error"


def test_continue_on_error(mock_tool_handler, mock_failing_handler):
    """Test that workflow continues when continue_on_error is True."""
    handlers = [mock_tool_handler, mock_failing_handler, mock_tool_handler]
    handler_index = 0

    def get_handler(tool_name):
        nonlocal handler_index
        handler = handlers[handler_index]
        handler_index += 1
        return handler

    with patch("ai_gaming_agent.tools.workflow._get_tool_handler", side_effect=get_handler):
        steps = [
            {"tool": "step1", "args": {}},
            {"tool": "step2", "args": {}, "continue_on_error": True},  # This will fail but continue
            {"tool": "step3", "args": {}},  # This should execute
        ]
        result = run_workflow(steps)

        assert result["success"] is True
        assert result["total_steps"] == 3
        assert result["completed_steps"] == 2  # First and third steps succeeded
        assert result["failed_step"] is None  # No failed step because we continued
        assert len(result["results"]) == 3  # All three steps executed


def test_wait_ms_delay(mock_tool_handler):
    """Test that wait_ms delay is applied between steps."""
    with patch("ai_gaming_agent.tools.workflow._get_tool_handler", return_value=mock_tool_handler):
        with patch("time.sleep") as mock_sleep:
            steps = [
                {"tool": "step1", "args": {}, "wait_ms": 1000},
                {"tool": "step2", "args": {}, "wait_ms": 500},
            ]
            result = run_workflow(steps)

            assert result["success"] is True
            # sleep should be called twice with the correct delays
            assert mock_sleep.call_count == 2
            mock_sleep.assert_any_call(1.0)  # 1000ms = 1.0s
            mock_sleep.assert_any_call(0.5)  # 500ms = 0.5s


def test_wait_ms_not_applied_on_failure(mock_tool_handler, mock_failing_handler):
    """Test that wait_ms is not applied when a step fails."""
    handlers = [mock_failing_handler]

    def get_handler(tool_name):
        return handlers[0]

    with patch("ai_gaming_agent.tools.workflow._get_tool_handler", side_effect=get_handler):
        with patch("time.sleep") as mock_sleep:
            steps = [{"tool": "step1", "args": {}, "wait_ms": 1000}]
            result = run_workflow(steps)

            assert result["success"] is False
            # sleep should NOT be called since step failed
            mock_sleep.assert_not_called()


def test_step_descriptions():
    """Test that step descriptions are captured in results."""
    with patch("ai_gaming_agent.tools.workflow._get_tool_handler", return_value=lambda **k: {"success": True}):
        steps = [
            {"tool": "click", "args": {}, "description": "Click the button"},
            {"tool": "type_text", "args": {}},  # No description
        ]
        result = run_workflow(steps)

        assert result["success"] is True
        assert result["results"][0]["description"] == "Click the button"
        assert result["results"][1]["description"] == "Step 2"  # Default description


def test_step_timing_recorded():
    """Test that execution time is recorded for each step."""
    with patch("ai_gaming_agent.tools.workflow._get_tool_handler", return_value=lambda **k: {"success": True}):
        steps = [{"tool": "click", "args": {}}]
        result = run_workflow(steps)

        assert result["success"] is True
        assert "time_ms" in result["results"][0]
        assert result["results"][0]["time_ms"] >= 0
        assert "total_time_ms" in result
        assert result["total_time_ms"] >= 0


def test_tool_exception_handling():
    """Test that exceptions in tool handlers are caught and recorded."""

    def exception_handler(**kwargs):
        raise ValueError("Test exception")

    with patch("ai_gaming_agent.tools.workflow._get_tool_handler", return_value=exception_handler):
        steps = [{"tool": "faulty_tool", "args": {}}]
        result = run_workflow(steps)

        assert result["success"] is False
        assert result["failed_step"] == 0
        assert "Test exception" in result["results"][0]["error"]


def test_tool_exception_with_continue_on_error():
    """Test that exceptions can be ignored with continue_on_error."""

    def exception_handler(**kwargs):
        raise ValueError("Test exception")

    def success_handler(**kwargs):
        return {"success": True}

    handlers = [exception_handler, success_handler]
    handler_index = 0

    def get_handler(tool_name):
        nonlocal handler_index
        handler = handlers[handler_index]
        handler_index += 1
        return handler

    with patch("ai_gaming_agent.tools.workflow._get_tool_handler", side_effect=get_handler):
        steps = [
            {"tool": "faulty_tool", "args": {}, "continue_on_error": True},
            {"tool": "good_tool", "args": {}},
        ]
        result = run_workflow(steps)

        assert result["success"] is True
        assert result["completed_steps"] == 1  # Only second step succeeded
        assert len(result["results"]) == 2  # Both steps executed


def test_step_index_recorded():
    """Test that step indices are correctly recorded."""
    with patch("ai_gaming_agent.tools.workflow._get_tool_handler", return_value=lambda **k: {"success": True}):
        steps = [
            {"tool": "step1", "args": {}},
            {"tool": "step2", "args": {}},
            {"tool": "step3", "args": {}},
        ]
        result = run_workflow(steps)

        assert result["success"] is True
        assert result["results"][0]["step_index"] == 0
        assert result["results"][1]["step_index"] == 1
        assert result["results"][2]["step_index"] == 2


def test_tool_result_without_success_field():
    """Test handling of tools that return non-dict results."""

    def simple_handler(**kwargs):
        return "simple string result"

    with patch("ai_gaming_agent.tools.workflow._get_tool_handler", return_value=simple_handler):
        steps = [{"tool": "simple_tool", "args": {}}]
        result = run_workflow(steps)

        assert result["success"] is True
        assert result["results"][0]["success"] is True  # Defaults to True for non-dict
        assert result["results"][0]["result"] == "simple string result"


def test_default_args_empty_dict():
    """Test that default args is an empty dict when not provided."""
    call_args = []

    def tracking_handler(**kwargs):
        call_args.append(kwargs)
        return {"success": True}

    with patch("ai_gaming_agent.tools.workflow._get_tool_handler", return_value=tracking_handler):
        steps = [{"tool": "test_tool"}]  # No args provided
        result = run_workflow(steps)

        assert result["success"] is True
        assert call_args == [{}]  # Should be called with empty dict


def test_integration_workflow_example():
    """Test a realistic workflow example with multiple tool types."""
    # Mock all the tools
    with patch("ai_gaming_agent.tools.workflow._get_tool_handler") as mock_get:
        # Create a mock handler that tracks calls
        calls = []

        def mock_handler(**kwargs):
            calls.append(kwargs)
            return {"success": True}

        mock_get.return_value = mock_handler

        # Realistic workflow: open terminal, type command, close
        steps = [
            {
                "tool": "execute_command",
                "args": {"command": "gnome-terminal"},
                "description": "Open terminal",
                "wait_ms": 1000,
            },
            {
                "tool": "type_text",
                "args": {"text": "echo hello world"},
                "description": "Type command",
                "wait_ms": 100,
            },
            {
                "tool": "press_key",
                "args": {"key": "enter"},
                "description": "Execute command",
                "wait_ms": 500,
            },
            {
                "tool": "hotkey",
                "args": {"keys": ["alt", "F4"]},
                "description": "Close terminal",
            },
        ]

        with patch("time.sleep"):
            result = run_workflow(steps)

        assert result["success"] is True
        assert result["total_steps"] == 4
        assert result["completed_steps"] == 4
        assert len(calls) == 4

        # Verify the calls were made with correct args
        assert calls[0] == {"command": "gnome-terminal"}
        assert calls[1] == {"text": "echo hello world"}
        assert calls[2] == {"key": "enter"}
        assert calls[3] == {"keys": ["alt", "F4"]}
