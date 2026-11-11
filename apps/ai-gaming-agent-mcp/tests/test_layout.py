"""Tests that pin the repository layout around the ai-gaming-agent MCP app.

The app lives in ``apps/ai-gaming-agent-mcp/`` and is its own uv workspace
root: its ``pyproject.toml`` declares ``[tool.uv.workspace]`` with no members,
so uv resolves, locks and installs there and the lockfile stays at
``apps/ai-gaming-agent-mcp/uv.lock``. The repository root ``pyproject.toml``
is only a manifest that registers the app as a member of the repository
workspace.

Delete either table and uv silently hoists the lockfile to the repository
root - no build, test or CI step notices. These tests make that failure loud.
"""

import re
import shlex
import tomllib
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
APP_MEMBER = "apps/ai-gaming-agent-mcp"
INSTALL_GUIDES = ("README.md", "docs/installation.txt")
GIT_REQUIREMENT = "git+https://github.com/developerz-ai/ai-gaming-agent-mcp.git#subdirectory=apps/ai-gaming-agent-mcp"
VLM_REQUIREMENT = f"ai-gaming-agent[vlm] @ {GIT_REQUIREMENT}"

# Documentation a reader copies commands from. Every `cd ... && ...` in them
# has to survive being pasted line by line into one shell.
DOC_COMMAND_FILES = (
    "README.md",
    "CLAUDE.md",
    "docs/integration-testing.md",
    "docs/testing.md",
    ".claude/skills/integration-gui/SKILL.md",
    "apps/ai-gaming-agent-mcp/examples/README.md",
    ".claude/agents/http-transport.md",
)

_CD_CHAIN = re.compile(r"cd\s+\S+\s*&&")
_PLACEHOLDER_INSTALLER_PIPE = re.compile(
    r"https?://(?:your-)?domain\.com/[^\s|`'\"]+\s*\|\s*(?:bash|sh|iex)\b",
    flags=re.IGNORECASE,
)


def _command_units(text: str) -> list[str]:
    """Return the commands a reader can paste: fenced shell blocks and inline code."""
    units: list[str] = []
    for block in re.findall(r"```(?:bash|sh|shell)\n(.*?)```", text, flags=re.DOTALL):
        units.extend(block.splitlines())
    units.extend(re.findall(r"`([^`\n]+)`", text))
    return units


def _load_toml(path: Path) -> dict:
    """Parse a TOML file into a plain dict."""
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _uv_workspace(data: dict, label: str) -> dict:
    """Return the ``[tool.uv.workspace]`` table of a parsed pyproject.toml."""
    workspace = data.get("tool", {}).get("uv", {}).get("workspace")
    assert workspace is not None, f"{label} must declare a [tool.uv.workspace] table"
    return workspace


def test_root_manifest_registers_the_app_as_workspace_member():
    """The repo root registers the app directory as a uv workspace member."""
    root_pyproject = REPO_ROOT / "pyproject.toml"
    assert root_pyproject.is_file(), f"missing repository root manifest: {root_pyproject}"

    workspace = _uv_workspace(_load_toml(root_pyproject), "the repository root pyproject.toml")
    members = workspace.get("members")
    assert members, "the repository root workspace must list at least one member"
    assert APP_MEMBER in members, f"the repository root workspace must register {APP_MEMBER}, got {members}"

    for member in members:
        member_path = (REPO_ROOT / member).resolve()
        assert member_path.is_dir(), f"workspace member {member} does not exist in the repository"
        assert (member_path / "pyproject.toml").is_file(), f"workspace member {member} has no pyproject.toml"
    assert (REPO_ROOT / APP_MEMBER).resolve() == APP_DIR.resolve()


def test_root_manifest_is_not_a_buildable_project():
    """The repo root is a workspace manifest only - it must not be a second project."""
    root_pyproject = REPO_ROOT / "pyproject.toml"
    assert root_pyproject.is_file(), f"missing repository root manifest: {root_pyproject}"

    data = _load_toml(root_pyproject)
    assert "project" not in data, "the repository root pyproject.toml must not declare a [project] table"
    assert "build-system" not in data, "the repository root pyproject.toml must not be a buildable project"


def test_app_is_its_own_workspace_root():
    """The app declares an empty workspace so uv keeps its lockfile in the app dir."""
    app_pyproject = APP_DIR / "pyproject.toml"
    assert app_pyproject.is_file(), f"missing app manifest: {app_pyproject}"

    workspace = _uv_workspace(_load_toml(app_pyproject), "the app pyproject.toml")
    assert "members" in workspace, "the app workspace table must declare members"
    assert workspace["members"] == [], "the app must be its own uv workspace root (members = [])"


def test_lockfile_stays_in_the_app_directory():
    """uv must lock the app in its own directory, never at the repository root."""
    assert (APP_DIR / "uv.lock").is_file(), f"missing app lockfile: {APP_DIR / 'uv.lock'}"
    assert not (REPO_ROOT / "uv.lock").exists(), "uv hoisted the lockfile to the repository root"


def test_app_metadata_readme_does_not_point_at_a_missing_file():
    """The readme key must not name a file that the move took away."""
    app_pyproject = APP_DIR / "pyproject.toml"
    data = _load_toml(app_pyproject)

    readme = data.get("project", {}).get("readme")
    assert readme is not None, "the app pyproject.toml must declare a readme"

    if isinstance(readme, str):
        assert (APP_DIR / readme).is_file(), f"readme file {readme} does not exist in the app directory"
        return

    if "file" in readme:
        assert (APP_DIR / readme["file"]).is_file(), f"readme file {readme['file']} does not exist in the app directory"
    else:
        assert readme.get("text"), "an inline readme must carry its text"
        assert readme.get("content-type") == "text/markdown"


def test_app_sources_and_tests_live_in_the_app_directory():
    """The app's sources moved; only empty directories and bytecode may remain."""
    app_pyproject = APP_DIR / "pyproject.toml"
    data = _load_toml(app_pyproject)

    packages = (
        data.get("tool", {}).get("hatch", {}).get("build", {}).get("targets", {}).get("wheel", {}).get("packages")
    )
    assert packages, "the app pyproject.toml must declare the hatch wheel packages"
    for package in packages:
        assert (APP_DIR / package).is_dir(), f"wheel package path {package} does not exist in the app directory"

    assert (APP_DIR / "src" / "ai_gaming_agent").is_dir(), "the importable package must live in the app directory"
    assert (APP_DIR / "tests").is_dir(), "the app test suite must live in the app directory"
    leftovers: list[str] = []
    for legacy in ("src", "tests"):
        for path in (REPO_ROOT / legacy).rglob("*"):
            if path.is_dir():
                continue
            if path.parent.name == "__pycache__" and path.suffix in {".pyc", ".pyo"}:
                continue
            leftovers.append(path.relative_to(REPO_ROOT).as_posix())
    assert not leftovers, "substantive files must not stay at the repository root: " + ", ".join(sorted(leftovers))


@pytest.mark.parametrize("legacy", ["src", "tests"])
@pytest.mark.parametrize("leftovers", ["absent", "empty", "cache"])
def test_layout_allows_generated_leftovers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, legacy: str, leftovers: str
) -> None:
    """Empty directories and bytecode caches do not undo the app migration."""
    if leftovers != "absent":
        cache = tmp_path / legacy / "nested" / "__pycache__"
        cache.mkdir(parents=True)
        if leftovers == "cache":
            for suffix in (".pyc", ".pyo"):
                (cache / f"old_module.cpython-312{suffix}").write_bytes(b"cached bytecode")
    monkeypatch.setitem(globals(), "REPO_ROOT", tmp_path)

    test_app_sources_and_tests_live_in_the_app_directory()


@pytest.mark.parametrize("legacy", ["src", "tests"])
@pytest.mark.parametrize(
    "relative",
    [
        "module.py",
        "nested/test_old.py",
        "data.txt",
        "module.pyc",
        "module.pyo",
        "__pycache__/hidden.py",
        "__pycache__/data.txt",
    ],
)
def test_layout_rejects_substantive_leftovers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, legacy: str, relative: str
) -> None:
    """The migration guard must name every substantive leftover, even in caches."""
    paths = [Path(legacy) / relative, Path(legacy) / "other.py"]
    for relative_path in paths:
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("leftover", encoding="utf-8")
    monkeypatch.setitem(globals(), "REPO_ROOT", tmp_path)

    with pytest.raises(AssertionError) as error:
        test_app_sources_and_tests_live_in_the_app_directory()
    for relative_path in paths:
        assert relative_path.as_posix() in str(error.value)


def test_documented_commands_do_not_change_the_callers_working_directory():
    """A documented `cd ... && ...` must run inside a subshell.

    The development blocks are pasted line by line into one shell. A bare
    `cd apps/ai-gaming-agent-mcp && uv sync --extra dev` leaves that shell inside
    the app directory, so the next line's `cd apps/ai-gaming-agent-mcp` fails with
    "No such file or directory" and the lint and test commands never run. A
    subshell keeps the caller's directory untouched.
    """
    violations: list[str] = []

    for relative in DOC_COMMAND_FILES:
        path = REPO_ROOT / relative
        assert path.is_file(), f"missing documentation file: {path}"

        for unit in _command_units(path.read_text(encoding="utf-8")):
            match = _CD_CHAIN.search(unit)
            if match is None:
                continue
            if not unit[: match.start()].rstrip().endswith("("):
                violations.append(f"{relative}: {unit.strip()}")
            elif ")" not in unit[match.end() :]:
                violations.append(f"{relative}: {unit.strip()}")

    assert not violations, "documented commands must run in a subshell: " + "; ".join(violations)


def test_repository_has_no_placeholder_domain_installer_pipes():
    """Placeholder domains must not advertise executable one-line installers."""
    violations: list[str] = []

    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or path.suffix in {".pyc", ".pyo"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in _PLACEHOLDER_INSTALLER_PIPE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            violations.append(f"{path.relative_to(REPO_ROOT)}:{line}: {match.group(0)}")

    assert not violations, "placeholder domains must not be piped into installers: " + "; ".join(violations)


def _install_commands(relative: str) -> list[str]:
    """Extract shell command lines from either fenced Markdown or the plain guide."""
    text = (REPO_ROOT / relative).read_text(encoding="utf-8")
    lines = _command_units(text) if relative.endswith(".md") else text.splitlines()
    return [line.strip() for line in lines if re.match(r"\s*(?:pip\d* |python3 |source |uvx |gaming-agent |sudo )", line)]


@pytest.mark.parametrize("relative", INSTALL_GUIDES)
def test_install_guides_use_git_before_editable_checkout(relative: str) -> None:
    """The default install and isolated runner must target the monorepo app."""
    commands = _install_commands(relative)
    tokens = [shlex.split(command, comments=True) for command in commands]
    install = tokens.index(["pip", "install", GIT_REQUIREMENT])
    runner = tokens.index(["uvx", "--from", GIT_REQUIREMENT, "gaming-agent", "--help"])
    editable = tokens.index(["pip", "install", "-e", "."])
    assert install < editable and runner < editable
    for index in (install, runner):
        assert any(f"{quote}{GIT_REQUIREMENT}{quote}" in commands[index] for quote in ('"', "'"))
    create = next(i for i, args in enumerate(tokens) if args[:3] == ["python3", "-m", "venv"])
    venv = tokens[create][3]
    activate = tokens.index(["source", f"{venv}/bin/activate"])
    assert create < activate < install
    assert ["gaming-agent", "--help"] in tokens[install + 1 :]


@pytest.mark.parametrize("relative", INSTALL_GUIDES)
def test_install_guides_quote_git_extra_and_avoid_pypi(relative: str) -> None:
    """Every active app install, including upgrades and extras, must use source."""
    commands = _install_commands(relative)
    tokens = [shlex.split(command, comments=True) for command in commands]
    extra = tokens.index(["pip", "install", VLM_REQUIREMENT])
    assert any(f"{quote}{VLM_REQUIREMENT}{quote}" in commands[extra] for quote in ('"', "'"))
    for args in tokens:
        if len(args) < 2 or args[0] not in {"pip", "pip3"} or args[1] != "install":
            continue
        for arg in args[2:]:
            if re.match(r"ai[-_]gaming[-_]agent(?:$|\[|[<>=!~])", arg):
                assert arg == VLM_REQUIREMENT, f"{relative} recommends a bare PyPI requirement: {arg}"
    if relative == "docs/installation.txt":
        assert ["pip", "install", "--upgrade", GIT_REQUIREMENT] in tokens


@pytest.mark.parametrize("relative", INSTALL_GUIDES)
def test_install_guides_include_debian_prerequisites(relative: str) -> None:
    """A clean Debian/Ubuntu host needs Python, Git, TLS and GUI dependencies."""
    tokens = [shlex.split(command, comments=True) for command in _install_commands(relative)]
    required = {"git", "ca-certificates", "python3", "python3-venv", "python3-tk", "scrot", "xclip", "wmctrl"}
    assert any(args[:3] == ["sudo", "apt", "install"] and required <= set(args[3:]) for args in tokens)


@pytest.mark.parametrize("relative", INSTALL_GUIDES)
def test_install_guides_distinguish_headless_help_from_desktop_automation(relative: str) -> None:
    """Installing and asking for help need no display; automation needs a desktop."""
    text = (REPO_ROOT / relative).read_text(encoding="utf-8")
    text = " ".join(text.replace("`", "").replace("*", "").split())
    assert re.search(r"logged-in graphical (?:desktop )?session", text)
    assert "X11" in text and "DISPLAY set" in text and "target desktop" in text
    assert re.search(r"gaming-agent --help work headlessly.*?(?:without|no) DISPLAY", text)
    assert re.search(r"root container, omit sudo", text)
    assert "logged-in desktop user, not root" in text


@pytest.mark.parametrize("relative", INSTALL_GUIDES)
def test_install_guides_include_fedora_and_arch_equivalents(relative: str) -> None:
    """Non-Debian users need matching Python, Tk, venv and build prerequisites."""
    text = (REPO_ROOT / relative).read_text(encoding="utf-8").replace("`", "")
    fedora_start = text.index("Fedora equivalents:")
    arch_start = text.index("Arch", fedora_start)
    fedora = text[fedora_start:arch_start]
    arch = text[arch_start:].split("macOS/Windows", 1)[0]
    for package in ("python3", "python3-pip", "python3-tkinter", "python3-devel", "gcc"):
        assert re.search(rf"\b{re.escape(package)}\b", fedora), f"{relative}: missing Fedora {package}"
    for package in ("python", "python-pip", "tk", "base-devel", "git", "ca-certificates", "scrot", "xclip", "wmctrl"):
        assert re.search(rf"\b{re.escape(package)}\b", arch), f"{relative}: missing Arch {package}"
