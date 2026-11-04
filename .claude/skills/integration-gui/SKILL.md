---
description: Run real-display GUI and OCR integration tests. Use for pyautogui, screenshot, OCR, terminal workflow.
applies: [python]
---

> House skill — established by dz-runner setup mode from this repo's own evidence, then owned by its maintainers. Correct it in place; setup never overwrites a skill that exists.

1. Install integration prerequisites with `cd apps/ai-gaming-agent-mcp && uv sync --extra integration`.
2. On Linux, install `python3-tk python3-dev scrot` and, for OCR cases, `tesseract-ocr`.
3. Ensure a graphical display exists; for a virtual display, run the test command under `xvfb-run -a`.
4. Run `cd apps/ai-gaming-agent-mcp && uv run pytest tests/integration -v`.
5. If OCR-only tests skip, verify the `tesseract` binary is available and rerun the affected file.
6. If GUI tests skip on Linux, confirm `DISPLAY` is set and pyautogui imports successfully.
7. Stop before any test that moves the pointer or types into an active desktop unless the display is isolated.
