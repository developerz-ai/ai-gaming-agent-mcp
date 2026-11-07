"""File operation tools."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from ai_gaming_agent.config import get_config


def _is_path_allowed(path: Path) -> bool:
    """Check if path is in allowed directories."""
    config = get_config()
    if not config.security.allowed_paths:
        return True  # No restrictions if empty

    resolved = path.resolve()
    for allowed in config.security.allowed_paths:
        allowed_path = Path(allowed).resolve()
        try:
            resolved.relative_to(allowed_path)
            return True
        except ValueError:
            continue
    return False


def read_file(path: str) -> dict[str, Any]:
    """Read file contents.

    Args:
        path: File path to read.

    Returns:
        File contents (text or base64 for binary).
    """
    try:
        file_path = Path(path)
        if not _is_path_allowed(file_path):
            return {"success": False, "error": f"Path not allowed: {path}"}

        if not file_path.exists():
            return {"success": False, "error": f"File not found: {path}"}

        # Try text first, fall back to binary
        try:
            content = file_path.read_text()
            return {"success": True, "content": content, "binary": False}
        except UnicodeDecodeError:
            content = base64.b64encode(file_path.read_bytes()).decode()
            return {"success": True, "content": content, "binary": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def write_file(path: str, content: str, binary: bool = False) -> dict[str, Any]:
    """Write content to file.

    Args:
        path: File path to write.
        content: Content to write.
        binary: If True, content is base64 encoded binary.

    Returns:
        Success status.
    """
    try:
        file_path = Path(path)
        if not _is_path_allowed(file_path):
            return {"success": False, "error": f"Path not allowed: {path}"}

        file_path.parent.mkdir(parents=True, exist_ok=True)

        if binary:
            file_path.write_bytes(base64.b64decode(content))
        else:
            file_path.write_text(content)

        return {"success": True, "path": str(file_path)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_files(path: str) -> dict[str, Any]:
    """List directory contents.

    Args:
        path: Directory path.

    Returns:
        List of files and directories.
    """
    try:
        dir_path = Path(path)
        if not _is_path_allowed(dir_path):
            return {"success": False, "error": f"Path not allowed: {path}"}

        if not dir_path.exists():
            return {"success": False, "error": f"Directory not found: {path}"}

        if not dir_path.is_dir():
            return {"success": False, "error": f"Not a directory: {path}"}

        items = []
        for item in dir_path.iterdir():
            items.append(
                {
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0,
                }
            )

        return {"success": True, "items": items}
    except Exception as e:
        return {"success": False, "error": str(e)}


def upload_file(path: str, content: str, binary: bool = False) -> dict[str, Any]:
    """Upload file to the PC (alias for write_file).

    Args:
        path: Destination path.
        content: File content.
        binary: If True, content is base64 encoded.

    Returns:
        Success status.
    """
    return write_file(path, content, binary)


def download_file(path: str) -> dict[str, Any]:
    """Download file from PC (returns base64 content).

    Args:
        path: File path to download.

    Returns:
        Base64 encoded file content.
    """
    try:
        file_path = Path(path)
        if not _is_path_allowed(file_path):
            return {"success": False, "error": f"Path not allowed: {path}"}

        if not file_path.exists():
            return {"success": False, "error": f"File not found: {path}"}

        content = base64.b64encode(file_path.read_bytes()).decode()
        return {
            "success": True,
            "content": content,
            "filename": file_path.name,
            "size": file_path.stat().st_size,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
