# Reviewer instructions — developerz-ai/ai-gaming-agent-mcp

> Read by the developerz.ai reviewer at EVERY review of this repository, at the reviewed
> commit, as this repo's own layer of the reviewer's prompt — established by dz-runner setup mode.
> It refines the platform rules (a finding is cited or withheld; the bot always discloses)
> and never overrides them. Edit freely; keep it under 12,000 characters — past that it is cut.

## Stack

Python 3.12 + uv. The gate is `bin/check`, which prepares the environment (`uv sync --extra dev`) and then grades with `uv run ruff check src tests` and `uv run pytest tests/ --ignore=tests/integration -v`: a change that does not pass it is not proven, whatever its description says. Read its exit code before blaming a change — 0 means the change passes, 75 means the environment was unreachable and the change was never graded (blame the environment, never the change), 1 means the change is red. CI does not invoke `bin/check`; `.github/workflows/ci.yml` runs the same two commands itself as separate steps, so CI reports pass/fail only and never exercises the exit-75 path.

## Review conventions

- TODO(setup): the conventions a reviewer must hold this repo to (from CLAUDE.md / CONTRIBUTING), each as a rule.

## Gates that matter

- TODO(setup): which checks decide a change here, and what "proven" means for a pull request.

## Never flag

- TODO(setup): what never to flag — generated or vendored files, style a formatter owns, conventions this repo chose on purpose.
