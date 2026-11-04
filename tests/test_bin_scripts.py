"""Contract tests for the repository lifecycle shell scripts.

The scripts form the repo's lifecycle contract, so the contract is pinned here
rather than left to prose: the exact commands each script runs, and the exit
code each failure means. The exit codes are the important half — a gate that
cannot run must say "the environment is unreachable" (75) instead of "the
change is red" (1), or correct work gets thrown away.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# The lint and unit-test commands the gate grades with. CI runs these two
# itself as separate steps — it never invokes bin/check.
GRADING_COMMANDS = (
    "run ruff check src tests",
    "run pytest tests/ --ignore=tests/integration -v",
)

# The exact environment preparation bin/check performs. It must match CI's
# `uv sync --extra dev` step — an `--inexact` variant would drift from CI.
SYNC_COMMAND = "sync --extra dev"


def _run_script(
    script: str,
    *,
    path: Path,
    home: Path,
    fake_uv_log: Path | None = None,
    sync_exit: int = 0,
    ruff_exit: int = 0,
    pytest_exit: int = 0,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a lifecycle script with isolated toolchain controls."""
    env = os.environ.copy()
    env["PATH"] = str(path)
    # Keep the shell and core utilities available while hiding the project tools.
    for system_bin in ("/bin", "/usr/bin"):
        if system_bin not in env["PATH"].split(os.pathsep):
            env["PATH"] += os.pathsep + system_bin
    home.mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(home)
    env["FAKE_UV_LOG"] = str(fake_uv_log) if fake_uv_log is not None else str(home / "uv.log")
    env["FAKE_UV_SYNC_EXIT"] = str(sync_exit)
    env["FAKE_UV_RUFF_EXIT"] = str(ruff_exit)
    env["FAKE_UV_PYTEST_EXIT"] = str(pytest_exit)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [str(REPO_ROOT / "bin" / script)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _make_fake_uv(tmp_path: Path) -> Path:
    """Create a fake uv which records arguments and honors exit-code controls."""
    fake_uv = tmp_path / "uv"
    fake_uv.write_text(
        """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "${FAKE_UV_LOG:?}"
case "$1 $2" in
  "sync --extra") exit "${FAKE_UV_SYNC_EXIT:-0}" ;;
  "run ruff") exit "${FAKE_UV_RUFF_EXIT:-0}" ;;
  "run pytest") exit "${FAKE_UV_PYTEST_EXIT:-0}" ;;
esac
exit 0
"""
    )
    fake_uv.chmod(0o755)
    return fake_uv


# The tools the lifecycle scripts shell out to. The sandbox links exactly these
# so the scripts' own "is it available?" branches are decided by what the test
# put there — not by whatever happens to be installed on the box.
_SANDBOX_TOOLS = (
    "bash",
    "sh",
    "cat",
    "cut",
    "date",
    "dirname",
    "env",
    "grep",
    "head",
    "id",
    "kill",
    "ls",
    "mktemp",
    "printf",
    "ps",
    "readlink",
    "rm",
    "sed",
    "seq",
    "sleep",
    "tail",
    "tr",
    "uname",
    "wc",
    "which",
)


def _sandbox_path(tmp_path: Path, *tools: str) -> Path:
    """A PATH holding only the named tools, so absent tools really are absent.

    The fake uv always goes in: every script under test needs it to be found,
    and without it the scripts would take their "uv is missing" branch. Any
    tool named in `tools` is linked from tmp_path first (a fake written by the
    test) and from the real PATH second.
    """
    sandbox = tmp_path / "sandbox-bin"
    sandbox.mkdir(exist_ok=True)
    for tool in _SANDBOX_TOOLS:
        source = shutil.which(tool)
        if source:
            (sandbox / tool).symlink_to(source)
    for tool in tools:
        local = tmp_path / tool
        source = str(local) if local.exists() else shutil.which(tool)
        if source is None:
            raise AssertionError(f"test needs {tool} on the box")
        (sandbox / tool).symlink_to(source)
    fake_uv = _make_fake_uv(tmp_path)
    (sandbox / "uv").symlink_to(fake_uv)
    return sandbox


# --- bin/check -------------------------------------------------------------


def test_check_without_uv_exits_75(tmp_path: Path) -> None:
    """An unavailable toolchain is an environment failure, not a red change."""
    sandbox = _sandbox_path(tmp_path)
    # Take the fake uv away again: this is the "no uv" case.
    (sandbox / "uv").unlink()
    result = _run_script(
        "check",
        path=sandbox,
        home=tmp_path / "home",
        extra_env={"PATH": str(sandbox)},
    )
    assert result.returncode == 75, result.stderr


def test_check_sync_failure_exits_75(tmp_path: Path) -> None:
    """Failure to prepare the environment prevents grading and exits 75."""
    sandbox = _sandbox_path(tmp_path)
    result = _run_script(
        "check",
        path=sandbox,
        home=tmp_path / "home",
        sync_exit=1,
        extra_env={"PATH": str(sandbox)},
    )
    assert result.returncode == 75, result.stderr


def test_check_ruff_failure_exits_1(tmp_path: Path) -> None:
    """Ruff errors mean the change is red."""
    sandbox = _sandbox_path(tmp_path)
    result = _run_script(
        "check",
        path=sandbox,
        home=tmp_path / "home",
        ruff_exit=1,
        extra_env={"PATH": str(sandbox)},
    )
    assert result.returncode == 1, result.stderr


def test_check_unit_test_failure_exits_1(tmp_path: Path) -> None:
    """Unit-test failures mean the change is red."""
    sandbox = _sandbox_path(tmp_path)
    result = _run_script(
        "check",
        path=sandbox,
        home=tmp_path / "home",
        pytest_exit=1,
        extra_env={"PATH": str(sandbox)},
    )
    assert result.returncode == 1, result.stderr


def test_check_runs_unit_suite_with_integration_excluded(tmp_path: Path) -> None:
    """The unit gate explicitly excludes the integration suite."""
    sandbox = _sandbox_path(tmp_path)
    log = tmp_path / "uv.log"
    result = _run_script(
        "check",
        path=sandbox,
        home=tmp_path / "home",
        fake_uv_log=log,
        extra_env={"PATH": str(sandbox)},
    )

    assert result.returncode == 0, result.stderr
    calls = log.read_text().splitlines()
    for command in GRADING_COMMANDS:
        assert command in calls


def test_check_syncs_with_the_exact_command_ci_uses(tmp_path: Path) -> None:
    """bin/check prepares the environment exactly as CI does.

    CI runs `uv sync --extra dev` as its own dependency step. A different
    invocation here would prepare a different tree than CI grades.
    """
    sandbox = _sandbox_path(tmp_path)
    log = tmp_path / "uv.log"
    result = _run_script(
        "check",
        path=sandbox,
        home=tmp_path / "home",
        fake_uv_log=log,
        extra_env={"PATH": str(sandbox)},
    )

    assert result.returncode == 0, result.stderr
    calls = log.read_text().splitlines()
    assert SYNC_COMMAND in calls
    # No `--inexact` variant: the sync must be the same one CI runs.
    assert not any("inexact" in call for call in calls)


def test_check_does_not_grade_when_the_environment_is_unreachable(tmp_path: Path) -> None:
    """A failed sync must stop the gate before lint or tests run."""
    sandbox = _sandbox_path(tmp_path)
    log = tmp_path / "uv.log"
    result = _run_script(
        "check",
        path=sandbox,
        home=tmp_path / "home",
        fake_uv_log=log,
        sync_exit=1,
        extra_env={"PATH": str(sandbox)},
    )

    assert result.returncode == 75, result.stderr
    calls = log.read_text().splitlines()
    for command in GRADING_COMMANDS:
        assert command not in calls


def test_check_does_not_claim_that_ci_invokes_it() -> None:
    """The gate's own header must not misdescribe where CI runs the checks.

    CI runs the lint and unit-test commands directly; it never invokes
    bin/check, so the header must not say it does.
    """
    header = (REPO_ROOT / "bin" / "check").read_text()
    assert "CI runs it" not in header
    assert "does NOT invoke this script" in header


# --- bin/setup -------------------------------------------------------------


def test_setup_without_uv_exits_75(tmp_path: Path) -> None:
    """A missing uv is an unreachable environment, not a red change.

    Exit 1 here would read as "the change is red" when nothing was graded.
    """
    sandbox = _sandbox_path(tmp_path)
    # Take the fake uv away again: this is the "no uv" case.
    (sandbox / "uv").unlink()
    result = _run_script(
        "setup",
        path=sandbox,
        home=tmp_path / "home",
        extra_env={"PATH": str(sandbox)},
    )
    assert result.returncode == 75, result.stderr


def test_setup_sync_failure_exits_75(tmp_path: Path) -> None:
    """The project environment is the part setup cannot do without."""
    _make_fake_uv(tmp_path)
    sandbox = _sandbox_path(tmp_path)
    result = _run_script(
        "setup",
        path=sandbox,
        home=tmp_path / "home",
        sync_exit=1,
        extra_env={"PATH": str(sandbox)},
    )
    assert result.returncode == 75, result.stderr


def test_setup_completes_and_syncs_the_dev_environment(tmp_path: Path) -> None:
    """A fresh checkout reaches a usable environment without error."""
    _make_fake_uv(tmp_path)
    log = tmp_path / "uv.log"
    sandbox = _sandbox_path(tmp_path)
    result = _run_script(
        "setup",
        path=sandbox,
        home=tmp_path / "home",
        fake_uv_log=log,
        extra_env={"PATH": str(sandbox)},
    )

    assert result.returncode == 0, result.stderr
    calls = log.read_text().splitlines()
    assert SYNC_COMMAND in calls


def test_setup_keeps_optional_system_package_failures_non_fatal(tmp_path: Path) -> None:
    """A missing system package must not abort setup.

    The GUI/OCR packages are only needed by the integration suite and the dev
    server, never by the dependency install.
    """
    # A dpkg-query that reports every package as absent, and an apt-get that
    # always fails: the worst case for the optional system packages.
    fake_dpkg = tmp_path / "dpkg-query"
    fake_dpkg.write_text(
        """#!/usr/bin/env bash
printf 'unknown ok not-installed\\n'
"""
    )
    fake_dpkg.chmod(0o755)
    fake_apt = tmp_path / "apt-get"
    fake_apt.write_text(
        """#!/usr/bin/env bash
exit 1
"""
    )
    fake_apt.chmod(0o755)

    sandbox = _sandbox_path(tmp_path, "dpkg-query", "apt-get")
    log = tmp_path / "uv.log"
    result = _run_script(
        "setup",
        path=sandbox,
        home=tmp_path / "home",
        fake_uv_log=log,
        extra_env={"PATH": str(sandbox)},
    )

    assert result.returncode == 0, result.stderr
    assert SYNC_COMMAND in log.read_text().splitlines()


def test_setup_skips_system_packages_when_apt_get_is_absent(tmp_path: Path) -> None:
    """A box without apt-get still reaches a usable environment."""
    fake_dpkg = tmp_path / "dpkg-query"
    fake_dpkg.write_text(
        """#!/usr/bin/env bash
printf 'unknown ok not-installed\\n'
"""
    )
    fake_dpkg.chmod(0o755)

    sandbox = _sandbox_path(tmp_path, "dpkg-query")
    log = tmp_path / "uv.log"
    result = _run_script(
        "setup",
        path=sandbox,
        home=tmp_path / "home",
        fake_uv_log=log,
        # The sandbox has no apt-get, so there is nothing to install with.
        extra_env={"PATH": str(sandbox)},
    )

    assert result.returncode == 0, result.stderr
    assert SYNC_COMMAND in log.read_text().splitlines()


# --- bin/dev ---------------------------------------------------------------


def test_dev_without_uv_exits_75(tmp_path: Path) -> None:
    """The dev launcher reports an unreachable environment distinctly."""
    sandbox = _sandbox_path(tmp_path)
    (sandbox / "uv").unlink()
    result = _run_script(
        "dev",
        path=sandbox,
        home=tmp_path / "home",
        extra_env={"PATH": str(sandbox)},
    )
    assert result.returncode == 75, result.stderr


def test_dev_starts_http_server_with_documented_address(tmp_path: Path) -> None:
    """The dev launcher starts the HTTP server on the documented address.

    The sandbox carries a real Xvfb so the launcher takes its virtual-display
    path — the one a headless checkout actually uses — and the fake uv stands
    in for the server so the launcher returns promptly.
    """
    sandbox = _sandbox_path(tmp_path, "Xvfb", "xauth", "mcookie")
    log = tmp_path / "uv.log"
    result = _run_script(
        "dev",
        path=sandbox,
        home=tmp_path / "home",
        fake_uv_log=log,
        extra_env={"DISPLAY": "", "PATH": str(sandbox)},
    )

    assert result.returncode == 0, result.stderr
    calls = log.read_text().splitlines()
    assert any(
        "run gaming-agent serve --transport http --host 127.0.0.1 --port 8765 --password onboarding-check"
        in call
        for call in calls
    )


def test_dev_without_a_display_exits_75(tmp_path: Path) -> None:
    """No display at all is an unreachable environment, not a red change."""
    # A sandbox with no X server: neither Xvfb nor xvfb-run can be found.
    sandbox = _sandbox_path(tmp_path)
    result = _run_script(
        "dev",
        path=sandbox,
        home=tmp_path / "home",
        extra_env={"DISPLAY": "", "PATH": str(sandbox)},
    )
    assert result.returncode == 75, result.stderr


def test_dev_falls_back_when_the_display_does_not_answer(tmp_path: Path) -> None:
    """A DISPLAY that is set but unreachable must not crash the launcher.

    The server imports pyautogui at start-up, so an unreachable DISPLAY would
    otherwise abort with a raw Xlib traceback and exit 1 — a code that reads as
    "the change is red". The launcher must treat the display as absent and
    fall back to a virtual one.
    """
    sandbox = _sandbox_path(tmp_path)
    log = tmp_path / "uv.log"
    result = _run_script(
        "dev",
        path=sandbox,
        home=tmp_path / "home",
        fake_uv_log=log,
        # A display number that cannot be in use: no X server answers on it,
        # and no X probe tool is on the sandbox PATH.
        extra_env={"DISPLAY": ":199", "PATH": str(sandbox)},
    )

    assert "DisplayConnectionError" not in result.stderr
    # No X server is reachable and none can be started, so this is an
    # unreachable environment (75), never "the change is red" (1).
    assert result.returncode == 75, result.stderr
