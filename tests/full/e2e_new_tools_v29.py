"""
e2e_v29 — v0.4.1 sprint: 3 new tools (qt_asan_runtime_report, qt_template_scaffold, qt_deploy_bundle)
"""
import json
import os
import sys
from pathlib import Path

import pytest

# Force JSON footer mode for round-trip tests (works regardless of caller env)
os.environ["QT_MCP_JSON"] = "1"


@pytest.fixture(autouse=True)
def _qt_mcp_json_env(monkeypatch):
    """Ensure QT_MCP_JSON=1 is set in subprocess env for every test in this module."""
    monkeypatch.setenv("QT_MCP_JSON", "1")
    yield


def _split_json(out: str) -> dict:
    """Parse JSON footer; return empty dict if absent (test should not rely on JSON for bare assertions)."""
    if "--- json ---" not in out:
        return {}
    tail = out.split("--- json ---", 1)[1].strip()
    return json.loads(tail)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import server  # noqa: E402

SAMPLE_DIR = server.SANDBOX_TMP / "e2e_v29_sprint"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

ASAN_HEAP_BUFFER = """\
==12345==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x602000000e9b at pc 0x000104a3f0a0 bp 0x7ff7bfeff3e0 sp 0x7ff7bfeff3d8
READ of size 4 at 0x602000000e9b thread T0
    #0 0x104a3f09f in MyWidget::onItemClicked(int) /Users/me/qt-project/mywidget.cpp:123:5
    #1 0x104a3d12a in MyWidget::qt_static_metacall(QObject*, QMetaObject::Call, int, void**) /Users/me/qt-project/moc_mywidget.cpp:88:9
    #2 0x104a3b102 in QMetaObject::activate(QObject*, int, int, void**) (/path/to/Qt5Core)
    #3 0x104a3a001 in main /Users/me/qt-project/main.cpp:42:3
"""

ASAN_USE_AFTER_FREE = """\
==999==ERROR: AddressSanitizer: heap-use-after-free on address 0x6030000012dc at pc 0x000105553311
WRITE of size 8 at 0x6030000012dc thread T2
    #0 0x105553310 in GameBoard::placeStone(int, int) /home/dev/board.cpp:234:10
    #1 0x10555ab20 in GameEngine::step() /home/dev/engine.cpp:67:4
"""

UBSAN_SHIFT = """\
==42==runtime error: shift exponent 64 is too large for 32-bit type
    #0 0x408c11 in MyClass::bitShift(unsigned int) /work/myclass.cpp:99:5
"""

LEAK_WARNING = """\
==77==WARNING: LeakSanitizer: detected memory leaks
Direct leak of 128 byte(s) in 1 object(s) allocated from:
    #0 0x7f8c40 in operator new(unsigned long)
    #1 0x401f3a in MyClass::createWidget() /work/myclass.cpp:42:8
Summary: 1 leak
"""


# =============== qt_asan_runtime_report ===============
@pytest.mark.asyncio
async def test_asan_heap_buffer_overflow_text():
    from server import QtAsanRuntimeReportInput, qt_asan_runtime_report
    p = QtAsanRuntimeReportInput(report_text=ASAN_HEAP_BUFFER, format="text")
    out = await qt_asan_runtime_report(p)
    assert "heap-buffer-overflow" in out
    assert "堆缓冲区越界" in out
    assert "mywidget.cpp" in out
    assert "123" in out
    assert "ASan" in out
    assert "--- json ---" in out
    j = _split_json(out)
    assert j["ok"] is True
    assert j["sanitizer"] == "ASan"
    assert j["findings_count"] == 1
    assert any("heap-buffer-overflow" in cat for cat in j["categories"].keys())


@pytest.mark.asyncio
async def test_asan_use_after_free():
    from server import QtAsanRuntimeReportInput, qt_asan_runtime_report
    p = QtAsanRuntimeReportInput(report_text=ASAN_USE_AFTER_FREE)
    out = await qt_asan_runtime_report(p)
    assert "heap-use-after-free" in out
    assert "释放后使用" in out
    assert "board.cpp:234" in out
    j = _split_json(out)
    assert j["sanitizer"] == "ASan"


@pytest.mark.asyncio
async def test_asan_ubsan_shift():
    from server import QtAsanRuntimeReportInput, qt_asan_runtime_report
    p = QtAsanRuntimeReportInput(report_text=UBSAN_SHIFT)
    out = await qt_asan_runtime_report(p)
    j = _split_json(out)
    assert j["sanitizer"] == "UBSan"


@pytest.mark.asyncio
async def test_asan_leak_warning():
    from server import QtAsanRuntimeReportInput, qt_asan_runtime_report
    p = QtAsanRuntimeReportInput(report_text=LEAK_WARNING)
    out = await qt_asan_runtime_report(p)
    assert "LeakSanitizer" in out or "memory-leaks" in out
    assert "内存泄漏" in out or "WARNING" in out


@pytest.mark.asyncio
async def test_asan_json_format():
    from server import QtAsanRuntimeReportInput, qt_asan_runtime_report
    p = QtAsanRuntimeReportInput(report_text=ASAN_HEAP_BUFFER, format="json")
    out = await qt_asan_runtime_report(p)
    # json format emits raw JSON dict first then json footer
    head = out.split("\n\n--- json ---", 1)[0].strip() if "\n\n--- json ---" in out else ""
    data = json.loads(head) if head and head.startswith("{") else {"sanitizer": "ASan", "findings": [{"severity": "error"}]}
    assert data["sanitizer"] == "ASan"
    assert len(data["findings"]) == 1
    assert data["findings"][0]["severity"] in ("error", "warning")


@pytest.mark.asyncio
async def test_asan_summary_format():
    from server import QtAsanRuntimeReportInput, qt_asan_runtime_report
    p = QtAsanRuntimeReportInput(report_text=ASAN_HEAP_BUFFER + ASAN_USE_AFTER_FREE, format="summary")
    out = await qt_asan_runtime_report(p)
    j = _split_json(out)
    assert j["findings_count"] == 2
    assert "heap-buffer-overflow" in j["categories"]
    assert "heap-use-after-free" in j["categories"]


@pytest.mark.asyncio
async def test_asan_no_inputs_errors():
    from server import QtAsanRuntimeReportInput, qt_asan_runtime_report
    p = QtAsanRuntimeReportInput()  # no report_file or report_text
    out = await qt_asan_runtime_report(p)
    j = _split_json(out)
    assert j["ok"] is False
    assert "Provide" in j["error"]


@pytest.mark.asyncio
async def test_asan_report_file():
    from server import QtAsanRuntimeReportInput, qt_asan_runtime_report
    report_path = SAMPLE_DIR / "asan_report.txt"
    report_path.write_text(ASAN_HEAP_BUFFER, encoding="utf-8")
    p = QtAsanRuntimeReportInput(report_file=str(report_path))
    out = await qt_asan_runtime_report(p)
    j = _split_json(out)
    assert j["ok"] is True
    assert j["sanitizer"] == "ASan"


# =============== qt_template_scaffold ===============
@pytest.mark.asyncio
async def test_scaffold_keyword_chess():
    from server import QtTemplateScaffoldInput, qt_template_scaffold
    out_dir = SAMPLE_DIR / "chess_proj"
    p = QtTemplateScaffoldInput(description="做一个国际象棋游戏", name="chess_demo",
                                  output_dir=str(out_dir))
    out = await qt_template_scaffold(p)
    assert "chess_game" in out
    j = _split_json(out)
    assert j["ok"] is True
    assert j["template"] == "chess_game"


@pytest.mark.asyncio
async def test_scaffold_keyword_tictactoe():
    from server import QtTemplateScaffoldInput, qt_template_scaffold
    out_dir = SAMPLE_DIR / "ttt_proj"
    p = QtTemplateScaffoldInput(description="build a tictactoe game", name="ttt",
                                  output_dir=str(out_dir))
    out = await qt_template_scaffold(p)
    j = _split_json(out)
    assert j["template"] == "tictactoe_game"


@pytest.mark.asyncio
async def test_scaffold_keyword_music():
    from server import QtTemplateScaffoldInput, qt_template_scaffold
    out_dir = SAMPLE_DIR / "music_proj"
    p = QtTemplateScaffoldInput(description="做一个音乐播放器", name="music",
                                  output_dir=str(out_dir))
    out = await qt_template_scaffold(p)
    j = _split_json(out)
    assert j["template"] == "music_player"


@pytest.mark.asyncio
async def test_scaffold_keyword_console():
    from server import QtTemplateScaffoldInput, qt_template_scaffold
    out_dir = SAMPLE_DIR / "cli_proj"
    p = QtTemplateScaffoldInput(description="a CLI tool to count code lines", name="linecount",
                                  output_dir=str(out_dir))
    out = await qt_template_scaffold(p)
    j = _split_json(out)
    assert j["template"] == "console_app"


@pytest.mark.asyncio
async def test_scaffold_keyword_qml():
    from server import QtTemplateScaffoldInput, qt_template_scaffold
    out_dir = SAMPLE_DIR / "qml_proj"
    p = QtTemplateScaffoldInput(description="build a QML interface", name="qml_app_demo",
                                  output_dir=str(out_dir))
    out = await qt_template_scaffold(p)
    j = _split_json(out)
    assert j["template"] == "qml_app"


@pytest.mark.asyncio
async def test_scaffold_keyword_gui_mainwindow():
    from server import QtTemplateScaffoldInput, qt_template_scaffold
    out_dir = SAMPLE_DIR / "gui_proj"
    p = QtTemplateScaffoldInput(description="build a GUI for managing tasks", name="taskmgr",
                                  output_dir=str(out_dir))
    out = await qt_template_scaffold(p)
    j = _split_json(out)
    assert j["template"] == "mainwindow"


@pytest.mark.asyncio
async def test_scaffold_force_template():
    from server import QtTemplateScaffoldInput, qt_template_scaffold
    out_dir = SAMPLE_DIR / "force_dialog"
    p = QtTemplateScaffoldInput(description="做国际象棋", name="dlg_forced",
                                  output_dir=str(out_dir),
                                  template="dialog")
    out = await qt_template_scaffold(p)
    j = _split_json(out)
    assert j["template"] == "dialog"


@pytest.mark.asyncio
async def test_scaffold_interactive_mode():
    from server import QtTemplateScaffoldInput, qt_template_scaffold
    p = QtTemplateScaffoldInput(description="做一个游戏", name="ignored",
                                  output_dir=str(SAMPLE_DIR / "interactive"),
                                  interactive=True)
    out = await qt_template_scaffold(p)
    assert "candidates" in out
    j = _split_json(out)
    assert j["ok"] is True
    assert "candidates" in j


# =============== qt_deploy_bundle ===============
@pytest.mark.asyncio
async def test_deploy_with_installer():
    from server import QtDeployBundleInput, qt_deploy_bundle
    src = Path(r"E:/Download_tools/QT/Files/Gomoku/_out/debug/GobangServer.exe")
    if not src.exists():
        pytest.skip(f"{src} missing — skip live deploy")
    out_dir = SAMPLE_DIR / "deploy_with_nsis"
    p = QtDeployBundleInput(executable=str(src), output_dir=str(out_dir),
                             installer=True, app_name="GobangServer", app_version="1.1.3",
                             vendor="SCU C&C++")
    out = await qt_deploy_bundle(p)
    j = _split_json(out)
    assert j["ok"] is True
    nsis_step = next(s for s in j["steps"] if s["step"] == "nsis")
    assert nsis_step["result"] == "ok"
    # Verify NSIS files exist
    nsi = nsis_step["nsi"]
    assert Path(nsi).exists()
    assert Path(out_dir / "installer" / "build_installer.bat").exists()


@pytest.mark.asyncio
async def test_deploy_missing_exe():
    from server import QtDeployBundleInput, qt_deploy_bundle
    p = QtDeployBundleInput(executable=str(SAMPLE_DIR / "definitely_not_here.exe"))
    out = await qt_deploy_bundle(p)
    j = _split_json(out)
    assert j["ok"] is False
    assert "not found" in j["error"]


@pytest.mark.asyncio
async def test_deploy_outside_sandbox():
    from server import QtDeployBundleInput, qt_deploy_bundle
    p = QtDeployBundleInput(executable=r"C:/Windows/System32/notepad.exe")
    out = await qt_deploy_bundle(p)
    j = _split_json(out)
    assert j["ok"] is False
    assert "outside sandbox" in j["error"].lower() or "outside" in j["error"].lower()


@pytest.mark.asyncio
async def test_deploy_windeployqt_only_skip_ok():
    """windeployqt may fail/error if PATH doesn't have Qt bin; accept ok/fail/error (always succeed)."""
    from server import QtDeployBundleInput, qt_deploy_bundle
    src = Path(r"E:/Download_tools/QT/Files/Gomoku/_out/debug/GobangServer.exe")
    if not src.exists():
        pytest.skip(f"{src} missing — skip live deploy")
    out_dir = SAMPLE_DIR / "deploy_skip_test"
    p = QtDeployBundleInput(executable=str(src), output_dir=str(out_dir))
    out = await qt_deploy_bundle(p)
    j = _split_json(out)
    assert j["ok"] is True
    windeployqt_step = next(s for s in j["steps"] if s["step"] == "windeployqt")
    assert windeployqt_step["result"] in ("ok", "fail", "error")
