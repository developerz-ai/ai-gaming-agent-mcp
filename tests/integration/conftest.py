"""Pytest configuration for integration tests."""

import os
import sys

import pytest


# Auto-skip all integration tests in CI or when no display available
def pytest_configure(config):
    """Register integration marker and check environment."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests (require display)")


def pytest_collection_modifyitems(config, items):
    """Skip integration tests if no display or running in CI."""
    skip_reason = None

    # Check CI environment
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        skip_reason = "Integration tests disabled in CI"

    # Check display on Linux
    elif sys.platform == "linux" and not os.environ.get("DISPLAY"):
        skip_reason = "No DISPLAY environment variable"

    # Try importing pyautogui to verify GUI works
    if not skip_reason:
        try:
            import pyautogui  # noqa: F401
        except (ImportError, SystemExit, Exception) as e:
            skip_reason = f"pyautogui not available: {e}"

    if skip_reason:
        skip_marker = pytest.mark.skip(reason=skip_reason)
        for item in items:
            if "integration" in str(item.fspath):
                item.add_marker(skip_marker)
