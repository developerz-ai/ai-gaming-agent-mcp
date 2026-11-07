# AI-first scorecard

> Written by the developerz.ai maintainer agent — established by dz-runner setup mode. Each onboarding run rewrites this file whole; the latest run wins, and the same card is stored on the platform.

- Run: `run_0a54ee114b854648942e8a2ac96f8640`
- Computed: 2026-11-03T15:59:15.598Z
- Proof: **proved** — every command ran green at head.
- Score: 13 of 15 items ok

## `policy` — ok

- .dz/maintainer/maintainer.yml established
- .dz/maintainer/reviewer.md established

## `brain` — ok

- CLAUDE.md already present, left alone

## `roster` — ok

- .claude/agents/mcp-tools.md established
- .claude/agents/http-transport.md established
- .claude/agents/workflow-automation.md established
- .claude/agents/gui-integration.md established

## `skills` — ok

- .claude/skills/verify-change/SKILL.md established
- .claude/skills/integration-gui/SKILL.md established

## `scripts` — ok

- bin/setup established
- bin/dev established
- bin/check established
- bin/stop established
- down: ./bin/stop (bin)
- ./bin/setup exited 0 at head (0.3s)

## `wiring` — ok

- .mcp.json established

## `commands` — ok

- .claude/commands/planx.md established
- .claude/commands/feature.md established

## `access` — gap

- landed 0 of 1 asked
- still missing: OLLAMA_ENDPOINT

## `layout` — gap

- migration to the house layout filed as tasks
- apps/ai-gaming-agent-mcp: 6 move(s) planned as one task

## `smoke_test` — ok

- apps/ai-gaming-agent-mcp/tests/test_workflow.py in the repository
- run by ./bin/check exited 0 at head (4.2s)

## `env_example` — ok

- .env.example established

## `agents_md` — ok

- AGENTS.md established

## `per_workspace_brains` — ok

- single-package repository: 0 workspaces
- CLAUDE.md already present, left alone

## `docs_readme` — ok

- docs/README.md established

## `gate_proved` — ok

- ./bin/check exited 0 at head (4.2s)
