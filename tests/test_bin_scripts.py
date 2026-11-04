"""Contract tests for the repository lifecycle shell scripts.

The scripts form the repo's lifecycle contract, so the contract is pinned here
rather than left to prose: the exact commands each script runs, and the exit
code each failure means. The exit codes are the important half — a gate that
cannot run must say "the environment is unreachable" (75) instead of "the
change is red" (1), or correct work gets thrown away.

Everything the scripts reach for is faked here — the toolchain, the X server
and the X tools. The unit gate must pass on a checkout that has no GUI
package installed at all.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
    fake_uv_env_log: Path | None = None,
    sync_exit: int = 0,
    ruff_exit: int = 0,
    pytest_exit: int = 0,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a lifecycle script with isolated toolchain controls."""
    env = os.environ.copy()
    # Only the sandbox is on PATH: the scripts' own "is it available?"
    # branches are decided by what the test put there, never by what the
    # box happens to have installed.
    env["PATH"] = str(path)
    home.mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(home)
    env["FAKE_UV_LOG"] = str(fake_uv_log) if fake_uv_log is not None else str(home / "uv.log")
    env["FAKE_UV_ENV_LOG"] = str(fake_uv_env_log) if fake_uv_env_log is not None else str(home / "uv-env.log")
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
    """Create a fake uv which records arguments and honors exit-code controls.

    The one call that talks to a display is the X probe (the launcher opens
    an X connection through python-xlib to check that a display accepts us);
    it is the one call whose success the fake has to answer for.
    """
    fake_uv = tmp_path / "uv"
    fake_uv.write_text(
        """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "${FAKE_UV_LOG:?}"
case "$*" in
  *Xlib.display*) exit "${FAKE_X_PROBE_EXIT:-0}" ;;
esac
case "$*" in
  *"gaming-agent serve"*)
    if [ -n "${FAKE_UV_ENV_LOG:-}" ]; then
      printf 'DISPLAY=%s XAUTHORITY=%s\\n' "${DISPLAY:-}" "${XAUTHORITY:-}" >> "$FAKE_UV_ENV_LOG"
      if [ -n "${XAUTHORITY:-}" ] && [ -f "$XAUTHORITY" ]; then
        printf 'AUTHORITY_CONTENT=%s\\n' "$(cat "$XAUTHORITY")" >> "$FAKE_UV_ENV_LOG"
      fi
    fi
    ;;
esac
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
    "od",
    "printf",
    "readlink",
    "rm",
    "sed",
    "seq",
    "setsid",
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
            _link(sandbox / tool, source)
    for tool in tools:
        local = tmp_path / tool
        source = str(local) if local.exists() else shutil.which(tool)
        if source is None:
            raise AssertionError(f"test needs {tool} on the box")
        _link(sandbox / tool, source)
    fake_uv = _make_fake_uv(tmp_path)
    _link(sandbox / "uv", fake_uv)
    return sandbox


def _link(link: Path, target: str | Path) -> None:
    """Point a sandbox entry at its target, replacing an earlier link."""
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(target)


def _write_fake(tmp_path: Path, name: str, body: str) -> Path:
    """Write an executable fake tool into tmp_path.

    A fake written here decides the branch the script takes, and keeps the
    unit gate free of packages the box may not have (Xvfb, xauth, mcookie).
    """
    path = tmp_path / name
    path.write_text(body)
    path.chmod(0o755)
    return path


# --- fakes for the X tooling ----------------------------------------------

# The cookie the fake mcookie hands out. A fixed value keeps the test
# deterministic and proves the launcher used the generated cookie rather
# than something of its own.
FAKE_COOKIE = "cafebabe0f1e2d3c4b5a69788796a5b"

FAKE_MCOOKIE = """#!/usr/bin/env bash
printf '%s\\n' "${FAKE_MCOOKIE_VALUE:-""" + FAKE_COOKIE + """}"
"""

FAKE_XAUTH = """#!/usr/bin/env bash
# Fake xauth: keep the commands it was given and write them into the
# authority file, so the test can see the cookie really land there.
input="$(cat)"
printf '%s\\n' "$input" >> "${FAKE_XAUTH_LOG:-/dev/null}"
if [ -n "${XAUTHORITY:-}" ]; then
  printf '%s\\n' "$input" >> "$XAUTHORITY"
fi
exit 0
"""

FAKE_XVFB = """#!/usr/bin/env bash
# Fake Xvfb: record how the launcher called it, copy the authority file it was
# given, then idle until the launcher kills it.
printf '%s\\n' "$@" >> "${FAKE_XVFB_LOG:-/dev/null}"
copy=""
next=""
for arg in "$@"; do
  if [ "$next" = "copy" ]; then
    copy="$arg"
    next=""
  elif [ "$arg" = "-auth" ]; then
    next="copy"
  fi
done
if [ -n "$copy" ] && [ -n "${FAKE_XVFB_AUTH_LOG:-}" ]; then
  cat "$copy" > "$FAKE_XVFB_AUTH_LOG" 2>/dev/null || true
fi
while true; do sleep 1; done
"""

FAKE_XVFB_DEAD = """#!/usr/bin/env bash
# Fake Xvfb that refuses to start, like a real one that cannot open its
# display.
printf '%s\\n' "$@" >> "${FAKE_XVFB_LOG:-/dev/null}"
echo "Xvfb: cannot open display" >&2
exit 1
"""


def _dev_sandbox(tmp_path: Path, *, xvfb_body: str = FAKE_XVFB, with_xauth: bool = True) -> Path:
    """A sandbox with fakes for the X tools bin/dev needs.

    Nothing here comes from the box: the unit gate must pass on a checkout
    that has no GUI package installed at all.
    """
    _write_fake(tmp_path, "Xvfb", xvfb_body)
    _write_fake(tmp_path, "mcookie", FAKE_MCOOKIE)
    tools = ["Xvfb", "mcookie"]
    if with_xauth:
        _write_fake(tmp_path, "xauth", FAKE_XAUTH)
        tools.append("xauth")
    return _sandbox_path(tmp_path, *tools)


def _package_version() -> str:
    """The version the launcher reads out of the package source."""
    source = (REPO_ROOT / "src" / "ai_gaming_agent" / "__init__.py").read_text()
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', source, re.MULTILINE)
    assert match is not None, "the package source must declare __version__"
    return match.group(1)


@contextlib.contextmanager
def _serving_health(payload: bytes):
    """Serve one fixed /health payload on a free localhost port."""
    body = payload

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - the name http.server requires
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # noqa: D102 - keep the test output clean
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


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


def test_dev_sandbox_uses_fakes_not_the_boxes_x_tools(tmp_path: Path) -> None:
    """The unit gate must not depend on GUI packages being installed.

    The X tools are fakes written by the test, so the sandbox never reaches
    for the ones the box may or may not have.
    """
    sandbox = _dev_sandbox(tmp_path)
    for tool in ("Xvfb", "xauth", "mcookie"):
        resolved = shutil.which(tool, path=str(sandbox))
        assert resolved is not None, tool
        assert Path(resolved).resolve() == (tmp_path / tool).resolve(), tool


def test_dev_starts_http_server_with_documented_address(tmp_path: Path) -> None:
    """The dev launcher starts the HTTP server on the documented address.

    The sandbox carries a fake Xvfb so the launcher takes its virtual-display
    path — the one a headless checkout actually uses — and the fake uv stands
    in for the server so the launcher returns promptly.
    """
    sandbox = _dev_sandbox(tmp_path)
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


def test_dev_xvfb_runs_with_an_authority_cookie_and_without_access_control_bypass(tmp_path: Path) -> None:
    """The virtual display must be authenticated, not open to every local user.

    Xvfb started with -ac disables client authentication: any user on the box
    could capture the virtual desktop and inject input into the automation.
    """
    sandbox = _dev_sandbox(tmp_path)
    xvfb_log = tmp_path / "xvfb.log"
    result = _run_script(
        "dev",
        path=sandbox,
        home=tmp_path / "home",
        fake_uv_log=tmp_path / "uv.log",
        extra_env={
            "DISPLAY": "",
            "PATH": str(sandbox),
            "FAKE_XVFB_LOG": str(xvfb_log),
        },
    )

    assert result.returncode == 0, result.stderr
    args = xvfb_log.read_text().split()
    assert "-ac" not in args, "Xvfb must not run with access control disabled"
    assert "-auth" in args, "Xvfb must be given the authority file"
    assert any(re.fullmatch(r":\d+", arg) for arg in args), args


def test_dev_gives_the_server_the_same_authority_cookie_as_the_virtual_display(tmp_path: Path) -> None:
    """The cookie the X server accepts must also reach the X clients.

    Xlib refuses a display it holds no cookie for, so the generated cookie
    has to be in the file Xvfb is given *and* in the file the server is
    started with.
    """
    sandbox = _dev_sandbox(tmp_path)
    xvfb_log = tmp_path / "xvfb.log"
    env_log = tmp_path / "uv-env.log"
    result = _run_script(
        "dev",
        path=sandbox,
        home=tmp_path / "home",
        fake_uv_log=tmp_path / "uv.log",
        fake_uv_env_log=env_log,
        extra_env={
            "DISPLAY": "",
            "PATH": str(sandbox),
            "FAKE_XVFB_LOG": str(xvfb_log),
            "FAKE_MCOOKIE_VALUE": FAKE_COOKIE,
        },
    )

    assert result.returncode == 0, result.stderr
    args = xvfb_log.read_text().split()
    server_auth_file = args[args.index("-auth") + 1]
    env_lines = env_log.read_text().splitlines()
    assert any(f"XAUTHORITY={server_auth_file}" in line for line in env_lines), env_lines
    assert any(FAKE_COOKIE in line for line in env_lines), env_lines


def test_dev_refuses_to_start_a_virtual_display_without_xauth(tmp_path: Path) -> None:
    """Without xauth there is no cookie, so no virtual display is started.

    Starting one anyway would mean running Xvfb open to every local user.
    """
    sandbox = _dev_sandbox(tmp_path, with_xauth=False)
    xvfb_log = tmp_path / "xvfb.log"
    result = _run_script(
        "dev",
        path=sandbox,
        home=tmp_path / "home",
        fake_uv_log=tmp_path / "uv.log",
        extra_env={
            "DISPLAY": "",
            "PATH": str(sandbox),
            "FAKE_XVFB_LOG": str(xvfb_log),
        },
    )

    assert result.returncode == 75, result.stderr
    assert not xvfb_log.exists(), "Xvfb must not be started without an authority cookie"
    assert "xauth" in result.stderr


def test_dev_uses_a_display_that_accepts_an_authenticated_connection(tmp_path: Path) -> None:
    """A display we can open an authenticated connection to is used as it is."""
    sandbox = _dev_sandbox(tmp_path)
    env_log = tmp_path / "uv-env.log"
    result = _run_script(
        "dev",
        path=sandbox,
        home=tmp_path / "home",
        fake_uv_log=tmp_path / "uv.log",
        fake_uv_env_log=env_log,
        extra_env={
            "DISPLAY": ":199",
            "PATH": str(sandbox),
            "FAKE_X_PROBE_EXIT": "0",
        },
    )

    assert result.returncode == 0, result.stderr
    assert "DISPLAY=:199" in env_log.read_text()
    assert "virtual display" not in result.stdout


def test_dev_falls_back_when_the_display_refuses_the_connection(tmp_path: Path) -> None:
    """A display that refuses an authenticated connection must not be used.

    The server imports pyautogui at start-up, so an unusable DISPLAY would
    otherwise abort with a raw Xlib traceback and exit 1 — a code that reads as
    "the change is red". The launcher must treat the display as absent and
    fall back to a virtual one.
    """
    sandbox = _dev_sandbox(tmp_path)
    log = tmp_path / "uv.log"
    result = _run_script(
        "dev",
        path=sandbox,
        home=tmp_path / "home",
        fake_uv_log=log,
        extra_env={
            "DISPLAY": ":199",
            "PATH": str(sandbox),
            "FAKE_X_PROBE_EXIT": "1",
        },
    )

    assert "DisplayConnectionError" not in result.stderr
    assert "falling back to a virtual display" in result.stderr
    # The refused display was never handed to the server.
    assert "gaming-agent serve" not in log.read_text()
    # No X server is reachable and none can be started, so this is an
    # unreachable environment (75), never "the change is red" (1).
    assert result.returncode == 75, result.stderr


def test_dev_reports_an_unreachable_environment_when_the_virtual_display_fails(tmp_path: Path) -> None:
    """An Xvfb that cannot start is an unreachable environment, not a red change."""
    sandbox = _dev_sandbox(tmp_path, xvfb_body=FAKE_XVFB_DEAD)
    result = _run_script(
        "dev",
        path=sandbox,
        home=tmp_path / "home",
        fake_uv_log=tmp_path / "uv.log",
        extra_env={
            "DISPLAY": "",
            "PATH": str(sandbox),
            "FAKE_XVFB_LOG": str(tmp_path / "xvfb.log"),
        },
    )

    assert result.returncode == 75, result.stderr
    assert "Xvfb failed to start" in result.stderr


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


def test_dev_recognises_its_own_health_payload(tmp_path: Path) -> None:
    """Our own server on the port means the dev stack is already up."""
    version = _package_version()
    payload = f'{{"status":"ok","version":"{version}"}}'.encode()
    with _serving_health(payload) as port:
        sandbox = _dev_sandbox(tmp_path)
        result = _run_script(
            "dev",
            path=sandbox,
            home=tmp_path / "home",
            fake_uv_log=tmp_path / "uv.log",
            extra_env={"PORT": str(port), "PATH": str(sandbox)},
        )

    assert result.returncode == 0, result.stderr
    assert "already serving" in result.stdout


def test_dev_does_not_mistake_a_foreign_service_for_its_own_server(tmp_path: Path) -> None:
    """A foreign service on the port must not be taken for our own server.

    Both a service reporting itself as unhealthy and one carrying another
    version's number answer on /health — neither is this checkout's server,
    so the launcher must not report the dev stack as already up.
    """
    for payload in (
        b'{"status":"down","version":"1"}',
        b'{"status":"ok","version":"9.9.9"}',
    ):
        with _serving_health(payload) as port:
            sandbox = _dev_sandbox(tmp_path)
            log = tmp_path / "uv.log"
            result = _run_script(
                "dev",
                path=sandbox,
                home=tmp_path / "home",
                fake_uv_log=log,
                extra_env={"PORT": str(port), "PATH": str(sandbox)},
            )

        assert result.returncode == 75, result.stderr
        assert "already serving" not in result.stdout
        # The server was never started: the launcher stopped at the preflight.
        assert not log.exists() or "gaming-agent serve" not in log.read_text()
