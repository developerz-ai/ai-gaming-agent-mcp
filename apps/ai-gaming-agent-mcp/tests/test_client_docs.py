"""Tests that pin the docs to what the server and the clients actually do.

``claude_desktop_config.json`` only takes stdio ``command`` entries, so a
``"transport": "sse"`` entry there is invalid, and Claude Desktop's Linux beta
path is deliberately not asserted. Remote access goes through the ``mcp-remote``
bridge (Desktop) or ``claude mcp add --transport sse`` (Claude Code).

The second pinned doc is ``docs/tools.txt``: it must not advertise MCP resource
URIs while ``create_server`` registers no resource handler. Each rule is proven
to fire on a fixture before it is trusted on the tree, so a rule that cannot
fail cannot pass.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

CLIENT_DOCS = (
    "README.md",
    "docs/configuration.md",
    "docs/configuration.txt",
    "apps/ai-gaming-agent-mcp/idea.md",
)
CLAUDE_CODE_AND_BRIDGE_DOCS = ("README.md", "docs/configuration.md")

TOOLS_DOC = "docs/tools.txt"
SERVER_SOURCE = "apps/ai-gaming-agent-mcp/src/ai_gaming_agent/server.py"

_JSON_FENCE = re.compile(r"```json\n(.*?)```", re.DOTALL)
_SSE_TRANSPORT_ENTRY = re.compile(r'"transport"\s*:\s*"sse"')
_LINUX_DESKTOP_PATH = "~/.config/claude/claude_desktop_config.json"

# A scheme URI, e.g. ``screen://current``. Plain web URLs are not resource URIs,
# so a doc may still show ``http://localhost:8765/health``.
_SCHEME_URI = re.compile(r"\b([a-z][a-z0-9+.-]*)://", re.IGNORECASE)
_WEB_SCHEMES = {"http", "https"}
# The keyword arguments ``create_server`` would carry if it registered a resource handler.
_RESOURCE_REGISTRATION_MARKERS = ("on_list_resources=", "on_read_resource=")


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def resource_uris(text: str) -> list[str]:
    """Scheme URIs in the text that are not plain web URLs."""
    return sorted({m.group(0) for m in _SCHEME_URI.finditer(text) if m.group(1).lower() not in _WEB_SCHEMES})


def registers_resources(server_source: str) -> bool:
    """Whether the server source registers an MCP resource handler."""
    return any(marker in server_source for marker in _RESOURCE_REGISTRATION_MARKERS)


def _config_snippets(relative: str) -> list[str]:
    """Return the JSON config snippets of a doc.

    Markdown docs contribute their fenced ``json`` blocks (prose may name the
    invalid shape to warn against it); plain-text docs have no fences, so the
    whole text counts.
    """
    text = _read(relative)
    if relative.endswith(".md"):
        return _JSON_FENCE.findall(text)
    return [text]


@pytest.mark.parametrize("relative", CLIENT_DOCS)
def test_no_linux_claude_desktop_config_path(relative: str) -> None:
    assert _LINUX_DESKTOP_PATH not in _read(relative)


@pytest.mark.parametrize("relative", CLIENT_DOCS)
def test_no_sse_transport_entry_in_desktop_config(relative: str) -> None:
    for snippet in _config_snippets(relative):
        assert not _SSE_TRANSPORT_ENTRY.search(snippet), (
            f'{relative} shows a "transport": "sse" entry; Claude Desktop '
            "config accepts stdio command entries only"
        )


@pytest.mark.parametrize("relative", CLAUDE_CODE_AND_BRIDGE_DOCS)
def test_docs_show_claude_code_command_and_mcp_remote_bridge(relative: str) -> None:
    text = _read(relative)
    assert "claude mcp add --transport sse" in text
    assert "mcp-remote" in text


@pytest.mark.parametrize("relative", CLAUDE_CODE_AND_BRIDGE_DOCS)
def test_desktop_bridge_entry_is_stdio_command(relative: str) -> None:
    snippets = [s for s in _config_snippets(relative) if "mcp-remote" in s]
    assert snippets, f"{relative} has no mcp-remote config snippet"
    for snippet in snippets:
        assert '"command": "npx"' in snippet
        assert '"sse-only"' in snippet


# The rules, proven to fire before they are trusted on the tree.


def test_resource_uri_rule_fires_and_lets_web_urls_through() -> None:
    assert resource_uris("  screen://current   - Live screenshot") == ["screen://"]
    assert resource_uris("  file:///{path}     - File system access") == ["file://"]
    assert resource_uris("GET http://localhost:8765/health") == []
    assert resource_uris("no uri here") == []


def test_resource_registration_rule_fires() -> None:
    assert registers_resources("Server(..., on_list_resources=_list_resources)")
    assert registers_resources("Server(..., on_read_resource=_read_resource)")
    assert not registers_resources("Server(..., on_list_tools=_list_tools, on_call_tool=_call_tool)")
    assert not registers_resources("# on_list_resources is not registered")
    assert not registers_resources('"on_read_resource is not registered"')


# The tree.


def test_tools_doc_advertises_no_resource_uri_while_none_is_registered() -> None:
    """``docs/tools.txt`` documents tools only, unless a resource handler exists."""
    text = _read(TOOLS_DOC)
    if registers_resources(_read(SERVER_SOURCE)):
        assert "no MCP resources" not in text, (
            f"{SERVER_SOURCE} registers a resource handler, but {TOOLS_DOC} still states it registers none"
        )
        return
    assert resource_uris(text) == [], (
        f"{TOOLS_DOC} advertises a resource URI, but {SERVER_SOURCE} registers no resource handler"
    )
    assert "no MCP resources" in text, f"{TOOLS_DOC} must state that the server registers no MCP resources"


def test_readme_records_live_client_configuration_validation() -> None:
    """Keep live-validation evidence with the documented client configs."""
    text = _read("README.md")
    assert "## Client configuration validation" in text
    assert "Claude Code 2.1.306" in text
    assert "`mcp-remote` 0.16.6" in text
    assert "Status: ✔ Connected" in text
    assert "Proxy established successfully" in text
