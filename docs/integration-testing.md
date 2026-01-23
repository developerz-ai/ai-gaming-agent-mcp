# Integration Testing Guide

## Overview

This guide explains how to run integration tests for the AI Gaming Agent project. Integration tests validate the full system including GUI automation, screenshot capture, and workflow execution.

## System Requirements

Integration tests require a graphical environment and several system dependencies. They will automatically skip in CI or headless environments.

### Required System Packages

```bash
# Install required system dependencies
sudo apt-get update
sudo apt-get install -y python3-tk python3-dev gnome-screenshot
```

**Dependencies explained:**
- `python3-tk`: Required for pyautogui's GUI automation
- `python3-dev`: Python development headers
- `gnome-screenshot`: Screenshot capture utility

### Optional Dependencies

```bash
# For OCR tests (optional)
sudo apt-get install -y tesseract-ocr
```

## Running Integration Tests

### All Integration Tests

```bash
# Run all integration tests
uv run pytest tests/integration -v

# Expected output: 30 passed, 4 skipped (without tesseract)
# With tesseract: 34 passed
```

### Specific Test Files

```bash
# Test full workflow (HTTP server + GUI automation)
uv run pytest tests/integration/test_full_workflow.py -v

# Test demo workflow
uv run pytest tests/integration/test_demo_workflow.py -v

# Test GUI automation primitives
uv run pytest tests/integration/test_gui_automation.py -v
```

### Test Coverage

**test_full_workflow.py (14 tests):**
- HTTP server health checks
- Authentication validation
- Direct workflow execution
- Terminal automation workflow
- OCR verification (skipped without tesseract)
- Edge cases and error handling
- Batch GUI operations
- Platform compatibility
- Full E2E with HTTP server
- Concurrent requests

**test_demo_workflow.py (8 tests):**
- Basic terminal workflow
- Workflow without closing terminal
- Workflow without screenshots
- Custom timing configuration
- Screenshot verification
- OCR verification (skipped without tesseract)
- Platform detection
- Close terminal hotkeys

**test_gui_automation.py (12 tests):**
- Screenshot capture
- Screen size detection
- OCR content verification (skipped without tesseract)
- Mouse position and movement
- Mouse clicks
- Text typing
- Key presses
- Hotkey combinations
- Terminal automation
- Batch operations

## Test Environment Detection

Integration tests automatically skip when:
- Running in CI (`CI` or `GITHUB_ACTIONS` environment variable set)
- No DISPLAY available on Linux
- pyautogui cannot be imported

## Troubleshooting

### Tests are skipping

Check the skip reason:
```bash
uv run pytest tests/integration -v
# Look for skip reason in output
```

Common causes:
1. No DISPLAY: Run in a graphical environment or use Xvfb
2. Missing dependencies: Install system packages listed above
3. pyautogui import error: Check python3-tk is installed

### Permission Errors

Some tests may move the mouse or type text. Ensure:
- You're not actively using the keyboard/mouse during tests
- The window manager allows programmatic input

### OCR Tests Skipping

OCR tests require tesseract-ocr:
```bash
sudo apt-get install -y tesseract-ocr
```

## CI/CD

Integration tests are **NOT** run in GitHub Actions by default because they require:
- Graphical display (X11/Wayland)
- Interactive window manager
- Physical or virtual display

Unit tests run in CI, integration tests run locally before release.

## Test Isolation

Each test:
- Uses fresh fixtures
- Cleans up windows/processes
- Captures screenshots to `/tmp`
- Uses random ports for HTTP servers
- Runs independently (order doesn't matter)

## Performance

Full integration test suite takes approximately **50-60 seconds** to run locally with all dependencies installed.

Individual test classes:
- HTTP server tests: ~5-10s
- Direct workflow tests: ~5-10s
- GUI automation tests: ~15-20s
- Demo workflow tests: ~10-15s
