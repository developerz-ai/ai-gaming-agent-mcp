"""Hermetic subprocess contracts for runnable uv discovery in setup/check."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SYNC = "sync --extra dev"
GRADING = ["run ruff check src tests", "run pytest tests/ --ignore=tests/integration -v"]
FALLBACKS = [".local/share/mise/shims", ".local/bin", ".cargo/bin"]


class Sandbox:
    def __init__(self, root: Path, script: str) -> None:
        self.root = root
        self.script = script
        self.home = root / "home"
        self.tools = root / "tools"
        self.system = root / "system-bin"
        self.app = root / "apps/ai-gaming-agent-mcp"
        self.log = root / "calls.log"
        for directory in (self.home, self.tools, self.system, self.app, root / "bin"):
            directory.mkdir(parents=True)
        for tool in ("bash", "dirname"):
            executable = shutil.which(tool)
            assert executable is not None, f"test requires {tool}"
            (self.tools / tool).symlink_to(executable)
        source = (REPO_ROOT / "bin" / script).read_text()
        # [bot] Redirect only the fixed system fallback; never run the host's uv.
        assert '"/usr/local/bin"' in source
        self.launcher = root / "bin" / script
        self.launcher.write_text(source.replace('"/usr/local/bin"', '"$TEST_SYSTEM_BIN"'))
        self.launcher.chmod(0o755)
        self.executable(
            self.tools / "mise",
            'printf "mise %s\\n" "$*" >> "$TEST_LOG"\nexit 1\n',
        )

    @staticmethod
    def executable(path: Path, body: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/usr/bin/env bash\n" + body)
        path.chmod(0o755)

    def uv(self, directory: Path, name: str, *, broken: bool = False) -> Path:
        body = f'printf "{name}|%s|%s\\n" "$*" "$PWD" >> "$TEST_LOG"\n'
        if broken:
            body += 'echo "mise: uv version is not installed" >&2\nexit 127\n'
        else:
            body += """case "$*" in
  --version) printf 'uv 0.test\n' ;;
  'sync --extra dev') echo 'sync output'; exit "${SYNC_EXIT:-0}" ;;
  'run ruff check src tests') echo 'ruff output'; exit "${RUFF_EXIT:-0}" ;;
  'run pytest tests/ --ignore=tests/integration -v') echo 'pytest output'; exit "${PYTEST_EXIT:-0}" ;;
  *) exit 99 ;;
esac
"""
        self.executable(directory / "uv", body)
        return directory

    def run(self, *paths: Path, **controls: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.launcher)],
            cwd=self.root,
            env={
                "HOME": str(self.home),
                "PATH": os.pathsep.join(str(path) for path in (*paths, self.tools)),
                "TEST_LOG": str(self.log),
                "TEST_SYSTEM_BIN": str(self.system),
                **controls,
            },
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def calls(self, name: str) -> list[str]:
        lines = self.log.read_text().splitlines() if self.log.exists() else []
        assert not any(line.startswith("mise ") for line in lines), "discovery must not install toolchains"
        calls = []
        for line in lines:
            executable, args, cwd = line.split("|")
            if executable == name:
                if args != "--version":
                    assert cwd == str(self.app)
                calls.append(args)
        return calls

    def expected(self) -> list[str]:
        return ["--version", SYNC, *(GRADING if self.script == "check" else [])]


@pytest.fixture(params=["setup", "check"])
def sandbox(tmp_path: Path, request: pytest.FixtureRequest) -> Sandbox:
    return Sandbox(tmp_path, request.param)


def test_toolchain_working_path_uv_wins(sandbox: Sandbox) -> None:
    first = sandbox.uv(sandbox.root / "first bin", "first")
    second = sandbox.uv(sandbox.root / "second", "second")
    sandbox.uv(sandbox.home / FALLBACKS[0], "home")
    result = sandbox.run(first, second)
    assert result.returncode == 0, result.stderr
    assert sandbox.calls("first") == sandbox.expected()
    assert sandbox.calls("second") == []
    assert sandbox.calls("home") == []


def test_toolchain_skips_broken_path_shim(sandbox: Sandbox) -> None:
    shim = sandbox.uv(sandbox.root / "mise-shims", "broken", broken=True)
    working = sandbox.uv(sandbox.root / "working bin", "working")
    sandbox.uv(sandbox.home / FALLBACKS[0], "home")
    result = sandbox.run(shim, working)
    assert result.returncode == 0, result.stderr
    assert sandbox.calls("broken") == ["--version"]
    assert sandbox.calls("working") == sandbox.expected()
    assert sandbox.calls("home") == []


@pytest.mark.parametrize("fallback", [*FALLBACKS, "system"])
def test_toolchain_uses_existing_fallback(sandbox: Sandbox, fallback: str) -> None:
    shim = sandbox.uv(sandbox.root / "mise-shims", "broken", broken=True)
    for directory in FALLBACKS:
        sandbox.uv(sandbox.home / directory, "broken-home", broken=True)
    target = sandbox.system if fallback == "system" else sandbox.home / fallback
    sandbox.uv(target, "fallback")
    result = sandbox.run(shim)
    assert result.returncode == 0, result.stderr
    assert sandbox.calls("broken") == ["--version"]
    assert all(call == "--version" for call in sandbox.calls("broken-home"))
    assert sandbox.calls("fallback") == sandbox.expected()


@pytest.mark.parametrize("broken", [False, True])
def test_toolchain_unavailable_refuses_to_grade(sandbox: Sandbox, broken: bool) -> None:
    if broken:
        sandbox.uv(sandbox.tools, "broken", broken=True)
        for directory in FALLBACKS:
            sandbox.uv(sandbox.home / directory, "broken", broken=True)
        sandbox.uv(sandbox.system, "broken", broken=True)
    result = sandbox.run()
    assert result.returncode == 75, result.stderr
    assert "uv" in result.stderr
    assert "https://docs.astral.sh/uv/" in result.stderr
    assert all(call == "--version" for call in sandbox.calls("broken"))
    assert "linting" not in result.stdout
    assert "unit tests" not in result.stdout


def test_toolchain_failed_sync_never_retries_or_grades(sandbox: Sandbox) -> None:
    shim = sandbox.uv(sandbox.root / "mise-shims", "broken", broken=True)
    working = sandbox.uv(sandbox.root / "working", "working")
    sandbox.uv(sandbox.home / FALLBACKS[0], "alternate")
    result = sandbox.run(shim, working, SYNC_EXIT="23")
    assert result.returncode == 75, result.stderr
    assert "sync output" in result.stdout
    assert "uv sync --extra dev failed" in result.stderr
    assert sandbox.calls("working") == ["--version", SYNC]
    assert sandbox.calls("alternate") == []
    assert sandbox.calls("broken") == ["--version"]


@pytest.mark.parametrize("stage", ["RUFF", "PYTEST"])
def test_toolchain_grading_failure_stays_red(tmp_path: Path, stage: str) -> None:
    sandbox = Sandbox(tmp_path, "check")
    shim = sandbox.uv(sandbox.root / "mise-shims", "broken", broken=True)
    working = sandbox.uv(sandbox.root / "working", "working")
    sandbox.uv(sandbox.home / FALLBACKS[0], "alternate")
    result = sandbox.run(shim, working, **{f"{stage}_EXIT": "2"})
    assert result.returncode == 1, result.stderr
    assert f"{stage.lower()} output" in result.stdout
    assert ("ruff reported lint errors" if stage == "RUFF" else "unit test suite failed") in result.stderr
    expected = ["--version", SYNC, *GRADING[: 1 if stage == "RUFF" else 2]]
    assert sandbox.calls("working") == expected
    assert sandbox.calls("alternate") == []
    assert sandbox.calls("broken") == ["--version"]
