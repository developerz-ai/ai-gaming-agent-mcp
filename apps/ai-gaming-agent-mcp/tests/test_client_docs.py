"""Tests that pin the client-connection docs to what the clients accept.

``claude_desktop_config.json`` only takes stdio ``command`` entries, so a
``"transport": "sse"`` entry there is invalid, and Claude Desktop's Linux beta
path is deliberately not asserted. Remote access goes through the ``mcp-remote``
bridge (Desktop) or ``claude mcp add --transport sse`` (Claude Code).
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

_JSON_FENCE = re.compile(r"```json\n(.*?)```", re.DOTALL)
_SSE_TRANSPORT_ENTRY = re.compile(r'"transport"\s*:\s*"sse"')
_LINUX_DESKTOP_PATH = "~/.config/claude/claude_desktop_config.json"


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


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
