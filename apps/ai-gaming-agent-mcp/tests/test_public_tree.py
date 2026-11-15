"""The public tree names no internal service, no internal identifier and no internal machinery.

This repository is public. Its tracked MCP configuration once named an internal service endpoint
of the organisation and wired an MCP server to our error tracker's credentials; its agent, skill
and command files described the internal execution environment they were drafted for; its
onboarding scorecard carried an internal run identifier. None of that is something a user of this
tool can run or needs to read.

Each rule is a function, and each is proven to fire on a fixture before it is trusted on the tree,
so a rule that cannot fail cannot pass. Every forbidden value is assembled from parts, so this file
never spells out what it forbids and does not trip over itself. The scan reads git's own index; its
scope is pinned by a sentinel (this file must be in it) and by git's top level, and it counts what
it read, so a wrong root or an unreadable tree fails instead of passing over nothing.

`.dz/` is the platform's own directory: the platform rewrites those files wholesale, the same
reason the sibling repositories' guards leave it out.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SELF = "apps/ai-gaming-agent-mcp/tests/test_public_tree.py"
EXCLUDED_PREFIXES = (".dz/",)

DOMAIN = ".".join(["developerz", "ai"])
PUBLIC_HOSTS = {DOMAIN, f"www.{DOMAIN}"}
HOST = re.compile(r"\b(?:[a-z0-9-]+\.)+" + re.escape(DOMAIN) + r"\b", re.IGNORECASE)
ID_PREFIXES = ["tsk", "run", "rvo", "pex", "rtk"]
INTERNAL_ID = re.compile(r"\b(?:" + "|".join(ID_PREFIXES) + r")_[0-9a-f]{12,}\b")
MACHINERY = "-".join(["dz", "runner"])
PUBLIC_MCP_SERVERS = {"codegraph"}


def internal_hosts(text: str) -> list[str]:
    """Hosts on our domain other than the public site, case-insensitively (DNS names are)."""
    return sorted({m.group(0).lower() for m in HOST.finditer(text)} - PUBLIC_HOSTS)


def internal_ids(text: str) -> list[str]:
    """Platform identifiers: a task, run, review, plan or runner-token id."""
    return sorted({m.group(0) for m in INTERNAL_ID.finditer(text)})


def names_machinery(text: str) -> bool:
    """Whether the text names the internal machinery that drafted the repository's files."""
    return MACHINERY in text.lower()


def non_public_mcp_servers(config_text: str) -> list[str]:
    """MCP servers a user of this repository cannot run: anything outside the public tools."""
    servers = json.loads(config_text).get("mcpServers", {})
    return sorted(set(servers) - PUBLIC_MCP_SERVERS)


def tracked_files() -> list[str]:
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, capture_output=True, text=True)
    assert top.returncode == 0, f"git rev-parse --show-toplevel failed: {top.stderr.strip()}"
    assert Path(top.stdout.strip()).resolve() == ROOT, "git's top level is not this repository's root"
    listed = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True)
    assert listed.returncode == 0, f"git ls-files failed: {listed.stderr.strip()}"
    files = [p for p in listed.stdout.split("\0") if p]
    assert SELF in files, "the scan does not see this file, so its scope is wrong"
    return [p for p in files if not p.startswith(EXCLUDED_PREFIXES)]


def scanned_texts() -> list[tuple[str, str]]:
    texts = []
    for path in tracked_files():
        try:
            texts.append((path, (ROOT / path).read_text(encoding="utf-8")))
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            continue
    assert texts, "the scan read no file at all"
    return texts


# The rules, proven to fire before they are trusted on the tree.


def test_internal_hosts_rule_fires_and_lets_the_public_site_through() -> None:
    assert internal_hosts(f"url: https://mcp.{DOMAIN}/v1/mcp") == [f"mcp.{DOMAIN}"]
    assert internal_hosts(f"MCP.{DOMAIN.upper()}") == [f"mcp.{DOMAIN}"]
    assert internal_hosts(f"see https://{DOMAIN} and https://www.{DOMAIN}/review") == []


def test_internal_ids_rule_fires_and_lets_ordinary_words_through() -> None:
    assert internal_ids(f"- Run: `run_{'a' * 32}`") == [f"run_{'a' * 32}"]
    assert internal_ids(f"task tsk_{'0' * 32}") == [f"tsk_{'0' * 32}"]
    assert internal_ids("run_tests, a tsk_ prefix, run_abc") == []


def test_machinery_rule_fires() -> None:
    assert names_machinery(f"> drafted by {MACHINERY.upper()} setup mode")
    assert not names_machinery("owned by this repository's maintainers")


def test_mcp_rule_fires_on_a_server_outside_the_public_tools() -> None:
    config = json.dumps({"mcpServers": {"codegraph": {}, "internal": {"url": f"https://mcp.{DOMAIN}"}}})
    assert non_public_mcp_servers(config) == ["internal"]
    assert non_public_mcp_servers(json.dumps({"mcpServers": {"codegraph": {}}})) == []


# The tree.


def test_no_tracked_file_names_an_internal_host() -> None:
    offenders = [path for path, text in scanned_texts() if internal_hosts(text)]
    assert offenders == [], f"a tracked file names a host on our domain other than the public site: {offenders}"


def test_no_tracked_file_carries_an_internal_identifier() -> None:
    offenders = [path for path, text in scanned_texts() if internal_ids(text)]
    assert offenders == [], f"a tracked file carries a platform identifier: {offenders}"


def test_no_tracked_file_names_the_internal_machinery() -> None:
    offenders = [path for path, text in scanned_texts() if names_machinery(text)]
    assert offenders == [], f"a tracked file names the internal machinery; name the maintainers: {offenders}"


def test_the_tracked_mcp_config_names_only_public_tools() -> None:
    assert ".mcp.json" in tracked_files(), "the MCP config this rule guards is not tracked"
    servers = non_public_mcp_servers((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    assert servers == [], f"the tracked .mcp.json names servers a user cannot run: {servers}"
