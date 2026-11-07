---
description: Prove a change in developerz-ai/ai-gaming-agent-mcp before committing or opening a pull request — the repo's own install, run and check commands. Use before every commit.
applies: [python]
---

# Verify a change in developerz-ai/ai-gaming-agent-mcp

> House skill — established by dz-runner setup mode from this repo’s own
> detected commands. Correct it in place; setup never overwrites a skill that exists.

## The one gate

`bin/check` is the local gate. The pre-commit hook (`.githooks/pre-commit`) runs it.
CI does **not** invoke `bin/check` — `.github/workflows/ci.yml` runs the same two
commands itself as separate steps, so a change that passes `bin/check` locally passes
CI's lint and unit tests. One consequence: CI never exercises `bin/check`'s exit-75
"environment unreachable" path, because CI runs the commands directly.

| Step | Command | What it is |
|------|---------|------------|
| install | `bin/setup` | checks xvfb, xauth, scrot, python3-tk, python3-dev and tesseract-ocr with dpkg-query, installs only the absent ones — skipping any it cannot install instead of aborting — and always ends with `uv sync --extra dev`, failing with exit 75 if that sync cannot complete |
| run | `bin/dev` | starts `uv run gaming-agent serve --transport http --host 127.0.0.1 --port 8765 --password onboarding-check` in the foreground — it preflights the port (exit 0 only when /health answers with this checkout's own healthy payload, exit 75 when anything else holds the port), then takes a display: a DISPLAY that accepts an authenticated X connection, else xvfb-run, else a hand-rolled Xvfb on a free :90–:120 with a generated authority cookie (exit 75 when no display is available). It tears down the server, the virtual display and its temp files when it exits — on developerz.ai runs, start it with code_bash_background when you need a running stack |
| prove | `bin/check` | prepares the environment (`uv sync --extra dev`), then grades with `uv run ruff check src tests` and `uv run pytest tests/ --ignore=tests/integration -v` — it exits 75 when the environment is unreachable and 1 when the change is red (see the exit codes below) |
| stop | `bin/stop` | true — on developerz.ai runs, the platform runs this when your session ends — do not stop the stack yourself. `bin/dev` cleans up its own server and virtual display when it exits, so `bin/stop` has nothing left to stop |

## Rules

- Run every command from the repo root — the scripts `cd` there themselves.
- `bin/check` red is not a pull request. Fix the cause, never silence the gate.

## Exit codes `bin/check` must use

A coding box runs this gate before it commits, and it has to tell a FAILING change
from a gate it could not run — otherwise correct work is thrown away as if it were
red. Exit 1 cannot carry that difference, so one code is reserved:

| Exit | Means | What the platform does |
|------|-------|------------------------|
| 0 | the change passes | commit it |
| 75 | a resource the gate NEEDS is unreachable (uv, the project environment, a database, a service, a credential) — it refused to grade | refuse the commit, and blame the environment, never the change |
| any other non-zero | the gate ran and the change is red | refuse the commit, and blame the change |

- Guard preconditions FIRST and `exit 75` when one is unmet. `exit 1` there tells the
  platform your change is broken when it is your environment that is. `bin/check`
  reserves 75 for exactly two cases: uv is not installed, and `uv sync --extra dev`
  could not prepare the project environment.
- These exit codes are a `bin/check` contract. CI runs the lint and unit-test
  commands directly, so CI reports only pass/fail — it has no exit-75 channel.
- Changed a dependency? Re-run `bin/setup` before `bin/check`, or you are proving a stale tree.
- Add the test that fails first, then the fix — a green run that never went red proves nothing.
