"""Headless tests for tool modules and feature-switch boundaries."""

import asyncio
import base64
import builtins
import importlib
import json
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest

from ai_gaming_agent.config import Config


@pytest.fixture(autouse=True)
def tool_config():
    """Isolate every tool call from user configuration and environment overrides."""
    config = Config.model_construct()
    with patch.object(Config, "load", return_value=config):
        yield config


@pytest.fixture
def backends(monkeypatch):
    gui, clipboard, monitors = MagicMock(), MagicMock(), MagicMock()
    gui.position.return_value = SimpleNamespace(x=10, y=20)
    image = gui.screenshot.return_value
    image.width, image.height = 640, 480
    image.save.side_effect = lambda buffer, format: buffer.write(b"png")
    clipboard.paste.return_value = "original"
    monitors.get_monitors.return_value = [SimpleNamespace(x=0, y=0, width=640, height=480, is_primary=True)]
    for name, backend in {"pyautogui": gui, "pyperclip": clipboard, "screeninfo": monitors}.items():
        monkeypatch.setitem(sys.modules, name, backend)
    return gui, clipboard, monitors


def test_write_and_read_file(tmp_path):
    from ai_gaming_agent.tools.files import read_file, write_file

    path = str(tmp_path / "test.txt")
    assert write_file(path, "Hello, World!")["success"] is True
    result = read_file(path)
    assert result == {"success": True, "content": "Hello, World!", "binary": False}


def test_list_files(tmp_path):
    from ai_gaming_agent.tools.files import list_files

    (tmp_path / "file1.txt").write_text("content1")
    (tmp_path / "file2.txt").write_text("content2")
    (tmp_path / "subdir").mkdir()
    result = list_files(str(tmp_path))
    assert result["success"] is True
    assert len(result["items"]) == 3
    assert {item["name"] for item in result["items"]} == {"file1.txt", "file2.txt", "subdir"}


def test_read_nonexistent_file(tmp_path):
    from ai_gaming_agent.tools.files import read_file

    result = read_file(str(tmp_path / "missing"))
    assert result["success"] is False
    assert "not found" in result["error"].lower()


GUI_CASES = [
    ("screen", "screenshot", "screenshot", {}, call.screenshot()),
    ("screen", "screenshot", "screenshot", {"monitor": 0}, call.screenshot(region=(0, 0, 640, 480))),
    ("screen", "screenshot", "get_screen_size", {}, None),
    ("screen", "screenshot", "get_screen_size", {"monitor": 0}, None),
    ("mouse", "mouse_control", "click", {"x": 10, "y": 20}, call.click(x=10, y=20, button="left")),
    ("mouse", "mouse_control", "double_click", {"x": 10, "y": 20}, call.doubleClick(x=10, y=20)),
    ("mouse", "mouse_control", "move_to", {"x": 10, "y": 20}, call.moveTo(x=10, y=20, duration=0.0)),
    ("mouse", "mouse_control", "drag_to", {"x": 10, "y": 20}, call.dragTo(x=10, y=20, duration=0.5)),
    ("mouse", "mouse_control", "scroll", {"clicks": 3}, call.scroll(3, x=None, y=None)),
    ("mouse", "mouse_control", "get_mouse_position", {}, call.position()),
    ("keyboard", "keyboard_control", "type_text", {"text": "test"}, call.write("test", interval=0.0)),
    ("keyboard", "keyboard_control", "type_text", {"text": "test", "use_paste": True}, call.hotkey("ctrl", "v")),
    ("keyboard", "keyboard_control", "press_key", {"key": "enter"}, call.press("enter")),
    ("keyboard", "keyboard_control", "press_key", {"key": "enter", "modifiers": ["ctrl"]}, call.press("enter")),
    ("keyboard", "keyboard_control", "hotkey", {"keys": ["ctrl", "c"]}, call.hotkey("ctrl", "c")),
]


PYAUTOGUI_CASES = [case for case in GUI_CASES if case[2] != "get_screen_size"]


@pytest.fixture
def missing_tk_backend(tmp_path, monkeypatch):
    """Simulate pyautogui -> mouseinfo -> missing tkinter without a desktop."""
    (tmp_path / "pyautogui.py").write_text("import mouseinfo\n")
    (tmp_path / "mouseinfo.py").write_text(
        "import sys\ntry:\n    import tkinter\nexcept ImportError:\n    sys.exit(EXIT_CODE)\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    for name in ("pyautogui", "mouseinfo"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.setitem(sys.modules, "tkinter", None)
    return tmp_path


@pytest.mark.parametrize("exit_code", [1, 0, None])
@pytest.mark.parametrize("module,feature,name,args,backend_call", PYAUTOGUI_CASES)
def test_missing_tk_returns_error(module, feature, name, args, backend_call, exit_code, missing_tk_backend):
    handler = getattr(importlib.import_module(f"ai_gaming_agent.tools.{module}"), name)
    with (
        patch.object(builtins, "EXIT_CODE", exit_code, create=True),
        patch.dict(sys.modules, {"pyperclip": MagicMock()}) as modules,
    ):
        result = handler(**args)
        assert modules["pyperclip"].mock_calls == []
    assert result["success"] is False
    for guidance in ("tkinter", "python3-tk", "Debian", "Ubuntu"):
        assert guidance in result["error"]


@pytest.mark.parametrize("missing", ["tkinter", "_tkinter"])
@pytest.mark.parametrize("module,feature,name,args,backend_call", PYAUTOGUI_CASES)
def test_tk_import_error_guidance(module, feature, name, args, backend_call, missing):
    handler = getattr(importlib.import_module(f"ai_gaming_agent.tools.{module}"), name)
    original_import = builtins.__import__

    def failed_import(name, *args, **kwargs):
        if name == "pyautogui":
            raise ImportError(f"No module named '{missing}'", name=missing)
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=failed_import):
        result = handler(**args)
    assert result["success"] is False
    assert "tkinter" in result["error"]
    assert "python3-tk" in result["error"]


@pytest.mark.parametrize("error", [ImportError("unrelated backend dependency", name="Xlib"), KeyError("DISPLAY")])
def test_unrelated_import_diagnostics_preserved(error):
    from ai_gaming_agent.tools.mouse import click

    original_import = builtins.__import__

    def failed_import(name, *args, **kwargs):
        if name == "pyautogui":
            raise error
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=failed_import):
        assert click(1, 2) == {"success": False, "error": str(error)}


@pytest.mark.parametrize("module,feature,name,args,backend_call", PYAUTOGUI_CASES)
def test_import_keyboard_interrupt_propagates(module, feature, name, args, backend_call):
    handler = getattr(importlib.import_module(f"ai_gaming_agent.tools.{module}"), name)
    original_import = builtins.__import__

    def interrupted_import(name, *args, **kwargs):
        if name == "pyautogui":
            raise KeyboardInterrupt
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=interrupted_import), pytest.raises(KeyboardInterrupt):
        handler(**args)


@pytest.mark.parametrize("signal", [SystemExit, KeyboardInterrupt])
@pytest.mark.parametrize("module,feature,name,args,backend_call", PYAUTOGUI_CASES)
def test_runtime_signals_propagate(module, feature, name, args, backend_call, signal, backends):
    handler = getattr(importlib.import_module(f"ai_gaming_agent.tools.{module}"), name)
    getattr(backends[0], backend_call[0]).side_effect = signal
    with pytest.raises(signal):
        handler(**args)


def test_screen_size_does_not_import_pyautogui(backends, missing_tk_backend):
    from ai_gaming_agent.tools.screen import get_screen_size

    assert get_screen_size() == {"success": True, "width": 640, "height": 480, "monitors": 1}
    assert "pyautogui" not in sys.modules


@pytest.mark.parametrize("exit_code", [0, None])
async def test_stdio_survives_gui_import_exit(exit_code, missing_tk_backend):
    """Use real stdio dispatch and sequential requests in one bounded child process."""
    source = missing_tk_backend / "safe.txt"
    source.write_text("server still alive")
    startup = (
        "import asyncio, builtins, sys\n"
        "from ai_gaming_agent.config import Config\n"
        "from ai_gaming_agent.server import run_server\n"
        "Config.load = classmethod(lambda cls: Config.model_construct())\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "sys.modules['tkinter'] = None\n"
        f"builtins.EXIT_CODE = {exit_code!r}\n"
        "asyncio.run(run_server())\n"
    )
    with (missing_tk_backend / "stderr.log").open("wb") as stderr:
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-u", "-c", startup, str(missing_tk_backend),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=stderr,
        )

        async def send(message: dict) -> None:
            process.stdin.write((json.dumps({"jsonrpc": "2.0", **message}) + "\n").encode())
            await asyncio.wait_for(process.stdin.drain(), timeout=10)

        async def request(identifier: int, method: str, params: dict) -> dict:
            await send({"id": identifier, "method": method, "params": params})
            line = await asyncio.wait_for(process.stdout.readline(), timeout=10)
            assert line, "stdio server exited before replying"
            response = json.loads(line)
            assert response["id"] == identifier
            assert "error" not in response
            return response["result"]

        try:
            initialized = await request(1, "initialize", {
                "protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "gui-regression[bot]", "version": "1"},
            })
            assert initialized["serverInfo"]["name"] == "ai-gaming-agent"
            await send({"method": "notifications/initialized"})
            failed = await request(2, "tools/call", {"name": "click", "arguments": {"x": 1, "y": 2}})
            result = json.loads(failed["content"][0]["text"])
            assert result["success"] is False
            assert "tkinter" in result["error"] and "python3-tk" in result["error"]
            safe = await request(3, "tools/call", {"name": "read_file", "arguments": {"path": str(source)}})
            assert json.loads(safe["content"][0]["text"]) == {
                "success": True, "content": "server still alive", "binary": False,
            }
            assert process.returncode is None
        finally:
            process.stdin.close()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except TimeoutError:
                process.kill()
                await asyncio.wait_for(process.wait(), timeout=5)


@pytest.mark.parametrize("module,feature,name,args,backend_call", GUI_CASES)
def test_gui_feature_switches(module, feature, name, args, backend_call, backends, tool_config):
    gui, clipboard, monitors = backends
    tool_module = importlib.reload(importlib.import_module(f"ai_gaming_agent.tools.{module}"))
    handler = getattr(tool_module, name)
    assert getattr(tool_config.features, feature) is True
    with patch("platform.system", return_value="Linux"):
        for enabled in (True, False, True):
            setattr(tool_config.features, feature, enabled)
            for backend in backends:
                backend.reset_mock()
            result = handler(**args)
            assert result["success"] is enabled
            if not enabled:
                assert "disabled" in result["error"].lower()
                for backend in backends:
                    assert backend.mock_calls == []
                continue
            if backend_call is not None:
                assert backend_call in gui.mock_calls
            if module == "screen":
                assert (result["width"], result["height"]) == (640, 480)
                if name == "get_screen_size" or "monitor" in args:
                    monitors.get_monitors.assert_called_once_with()
                else:
                    monitors.get_monitors.assert_not_called()
                if name == "screenshot":
                    assert result["image"] == base64.b64encode(b"png").decode()
                    assert result["format"] == "png"
            if module == "mouse":
                assert gui.FAILSAFE is False
            if name == "get_mouse_position":
                assert result == {"success": True, "x": 10, "y": 20}
            if name == "type_text":
                assert result["text"] == "test"
                assert result["method"] == ("paste" if args.get("use_paste") else "type")
            if args.get("use_paste"):
                assert clipboard.copy.call_args_list == [call("test"), call("original")]
            else:
                assert clipboard.mock_calls == []
            if args.get("modifiers"):
                gui.hold.assert_called_once_with(["ctrl"])
                gui.hold.return_value.__enter__.assert_called_once_with()
                gui.hold.return_value.__exit__.assert_called_once()


@pytest.mark.parametrize("module,feature,name,args,backend_call", GUI_CASES)
def test_disabled_gui_never_imports_backends(module, feature, name, args, backend_call, tool_config):
    setattr(tool_config.features, feature, False)
    original_import = builtins.__import__
    attempts = []

    def guarded_import(name, *args, **kwargs):
        if name.split(".")[0] in {"pyautogui", "pyperclip", "screeninfo", "PIL"}:
            attempts.append(name)
            raise ImportError("Desktop dependency unavailable")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=guarded_import):
        tool_module = importlib.reload(importlib.import_module(f"ai_gaming_agent.tools.{module}"))
        result = getattr(tool_module, name)(**args)
    assert attempts == []
    assert result["success"] is False
    assert "disabled" in result["error"].lower()


@pytest.mark.parametrize("name", ["screenshot", "get_screen_size"])
@pytest.mark.parametrize("monitor", [-1, 1])
def test_monitor_validation(name, monitor, backends, tool_config):
    screen = importlib.reload(importlib.import_module("ai_gaming_agent.tools.screen"))
    result = getattr(screen, name)(monitor=monitor)
    assert result == {"success": False, "error": f"Invalid monitor index: {monitor}"}
    backends[0].screenshot.assert_not_called()
    tool_config.features.screenshot = False
    backends[2].reset_mock()
    result = getattr(screen, name)(monitor=monitor)
    assert "disabled" in result["error"].lower()
    backends[2].get_monitors.assert_not_called()


@pytest.mark.parametrize("name", ["read_file", "write_file", "list_files", "upload_file", "download_file"])
@pytest.mark.parametrize("binary", [False, True])
def test_file_feature_switches(name, binary, tmp_path, tool_config):
    from ai_gaming_agent.tools import files

    source = tmp_path / "source"
    data = b"\xff\x00" if binary else b"test"
    source.write_bytes(data)
    target = tmp_path / "new" / "target"
    writing = name in {"write_file", "upload_file"}
    path = target if writing else tmp_path if name == "list_files" else source
    args = {"path": str(path)}
    if writing:
        args.update(content=base64.b64encode(data).decode() if binary else "test", binary=binary)
    assert tool_config.features.file_access is True
    for enabled in (True, False, True):
        tool_config.features.file_access = enabled
        if target.exists():
            target.unlink()
            target.parent.rmdir()
        with (
            patch.object(files, "Path", wraps=files.Path) as path_factory,
            patch.object(files, "_is_path_allowed", wraps=files._is_path_allowed) as allowed,
        ):
            result = getattr(files, name)(**args)
        assert result["success"] is enabled
        if not enabled:
            assert "disabled" in result["error"].lower()
            path_factory.assert_not_called()
            allowed.assert_not_called()
            assert not target.parent.exists()
            assert source.read_bytes() == data
        else:
            path_factory.assert_called_once_with(str(path))
            allowed.assert_called_once()
            if writing:
                assert target.read_bytes() == data
            elif name == "list_files":
                assert result["items"] == [{"name": "source", "is_dir": False, "size": len(data)}]
            elif name == "download_file":
                assert base64.b64decode(result["content"]) == data
                assert result["filename"] == "source"
                assert result["size"] == len(data)
            else:
                assert result["binary"] is binary
                assert result["content"] == (base64.b64encode(data).decode() if binary else "test")


@pytest.mark.parametrize("name", ["read_file", "write_file", "list_files", "upload_file", "download_file"])
def test_file_allowed_paths_still_enforced(name, tmp_path, tool_config):
    from ai_gaming_agent.tools import files

    tool_config.security.allowed_paths = [str(tmp_path / "allowed")]
    args = {"path": str(tmp_path / "outside")}
    if name in {"write_file", "upload_file"}:
        args["content"] = "test"
    result = getattr(files, name)(**args)
    assert result["success"] is False
    assert "Path not allowed" in result["error"]
    assert not (tmp_path / "outside").exists()


class TestTypeTextPasteMocked:
    """Exercise paste behavior without a display or real clipboard."""

    @pytest.mark.parametrize("system,key", [("Linux", "ctrl"), ("Windows", "ctrl"), ("Darwin", "command")])
    @pytest.mark.parametrize("original", ["original content", ""])
    def test_paste_and_restore(self, backends, system, key, original):
        from ai_gaming_agent.tools.keyboard import type_text

        gui, clipboard, _ = backends
        clipboard.paste.return_value = original
        with patch("platform.system", return_value=system):
            result = type_text("hello world", use_paste=True)
        assert isinstance(result, dict)
        assert result == {"success": True, "method": "paste", "text": "hello world"}
        clipboard.copy.assert_any_call("hello world")
        assert clipboard.copy.call_args_list == [call("hello world"), call(original)]
        gui.hotkey.assert_called_once_with(key, "v")

    @pytest.mark.parametrize("failure", ["read", "restore", "copy", "hotkey"])
    def test_paste_errors(self, backends, failure):
        from ai_gaming_agent.tools.keyboard import type_text

        gui, clipboard, _ = backends
        if failure == "read":
            clipboard.paste.side_effect = Exception("Clipboard unavailable")
        elif failure == "restore":
            clipboard.copy.side_effect = [None, Exception("Restore failed")]
        elif failure == "copy":
            clipboard.copy.side_effect = Exception("Copy failed")
        else:
            gui.hotkey.side_effect = Exception("Hotkey failed")
        result = type_text("test", use_paste=True)
        assert result["success"] is (failure in {"read", "restore"})
        if failure == "read":
            clipboard.copy.assert_called_once_with("test")
        if failure in {"copy", "hotkey"}:
            assert f"{failure.capitalize()} failed" in result["error"]

    @pytest.mark.parametrize("args,interval", [({}, 0.0), ({"use_paste": False}, 0.0), ({"interval": 0.1}, 0.1)])
    def test_normal_typing(self, backends, args, interval):
        from ai_gaming_agent.tools.keyboard import type_text

        result = type_text("test", **args)
        assert result == {"success": True, "method": "type", "text": "test"}
        backends[0].write.assert_called_once_with("test", interval=interval)
        assert backends[1].mock_calls == []
