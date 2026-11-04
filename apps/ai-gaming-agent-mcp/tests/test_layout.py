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

import tomllib
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
APP_MEMBER = "apps/ai-gaming-agent-mcp"


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
    """The app's sources moved into the app directory; nothing is left at the root."""
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
    assert not (REPO_ROOT / "src").exists(), "the app sources must not stay at the repository root"
    assert not (REPO_ROOT / "tests").exists(), "the app tests must not stay at the repository root"
