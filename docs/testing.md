# Testing Guide

This document explains the testing strategy for AI Gaming Agent.

## Test Categories

### Unit Tests (CI)

**Location:** `tests/` (excluding `tests/integration/`)

Unit tests verify individual components without requiring a display:
- Configuration loading/saving
- File operations
- Tool interfaces

**Run locally:**
```bash
uv run pytest tests/ --ignore=tests/integration -v
```

**Runs in CI:** Yes (GitHub Actions)

### Integration Tests (Local Only)

**Location:** `tests/integration/`

Integration tests perform **real GUI automation** on your desktop:
- Actual mouse movements and clicks
- Real keyboard input
- Terminal/application launching
- OCR screen verification

**Run locally:**
```bash
uv run pytest tests/integration -v
```

**Runs in CI:** No - requires real display

## Why Integration Tests Can't Run in CI

1. **Real Display Required**: Tests need X11, Wayland, Windows, or macOS desktop
2. **Actual User Input**: Mouse/keyboard events need display server
3. **Application Interaction**: Opening terminals requires window manager
4. **OCR Verification**: Tesseract needs real screen content
5. **Side Effects**: GUI actions could interfere with CI environment

## Integration Test Requirements

### System Dependencies

**Linux:**
```bash
sudo apt install tesseract-ocr python3-tk scrot
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
- Download tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
- Add to PATH

### Python Dependencies

```bash
uv sync --extra integration
```

This installs:
- `pytest` - Test framework
- `pytesseract` - Python wrapper for tesseract OCR

## Integration Test Details

### Screen Capture Tests

| Test | What it does |
|------|--------------|
| `test_screenshot_returns_image` | Takes real screenshot, verifies base64 PNG |
| `test_get_screen_size` | Gets actual display resolution |
| `test_ocr_screen_content` | Takes screenshot, runs OCR, finds text |

### Mouse Control Tests

| Test | What it does |
|------|--------------|
| `test_mouse_position` | Gets current cursor coordinates |
| `test_mouse_move` | Moves cursor to (100, 100), verifies position |
| `test_mouse_click` | Clicks in screen center |

### Keyboard Control Tests

| Test | What it does |
|------|--------------|
| `test_type_text` | Types "test" string |
| `test_press_key` | Presses Escape key |
| `test_hotkey` | Presses Ctrl+A |

### Terminal Workflow Tests

| Test | What it does |
|------|--------------|
| `test_terminal_workflow` | Opens terminal, types command, takes screenshot, closes |
| `test_terminal_with_ocr_verification` | Full E2E: open terminal, type echo, verify output via OCR, close |

### Batch Operations Test

`test_batch_gui_operations` runs these in sequence:
1. Get screen size
2. Take screenshot
3. Move mouse to center
4. Click
5. Type text
6. Press Escape
7. Take final screenshot

## Platform Support

### Linux
- Terminals: gnome-terminal, konsole, xterm, xfce4-terminal
- Display: X11 or Wayland (XWayland)
- Close: Alt+F4

### Windows
- Terminal: cmd
- Close: Alt+F4

### macOS
- Terminal: Terminal.app
- Close: Cmd+Q

## CI/CD Configuration

### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  CI: true  # Auto-skips integration tests

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv python install 3.12
      - run: |
          sudo apt-get update
          sudo apt-get install -y xvfb scrot python3-tk python3-dev
      - run: uv sync --extra dev
      - run: uv run ruff check src tests
      - run: uv run pytest tests/ --ignore=tests/integration -v
```

### Key Points

1. **Single Python version**: 3.12 (latest stable)
2. **Package manager**: uv (fast, deterministic)
3. **Linting**: ruff (fast, comprehensive)
4. **Integration tests excluded**: `--ignore=tests/integration`
5. **CI environment variable**: `CI=true` signals test skipping

## Writing New Tests

### Unit Tests

Place in `tests/test_*.py`:
```python
def test_my_feature():
    from ai_gaming_agent.tools.files import read_file
    result = read_file("/tmp/test.txt")
    assert result["success"] is True
```

### Integration Tests

Place in `tests/integration/test_*.py`:
```python
import pytest

pytestmark = pytest.mark.integration

class TestMyFeature:
    def test_gui_action(self, ensure_gui):
        from ai_gaming_agent.tools.mouse import click
        result = click(100, 100)
        assert result["success"] is True
```

Use the `ensure_gui` fixture to verify pyautogui is available.

## Debugging Integration Tests

### Run single test with output:
```bash
uv run pytest tests/integration/test_gui_automation.py::TestTerminalAutomation::test_terminal_workflow -v -s
```

### Check why tests are skipped:
```bash
uv run pytest tests/integration -v --collect-only
```

### Run with warnings:
```bash
uv run pytest tests/integration -v -W default
```
