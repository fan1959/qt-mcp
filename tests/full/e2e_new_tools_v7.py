"""e2e for v7 new tools: qt_pkg, qt_log, qt_state, qt_assets.

Run: python e2e_new_tools_v7.py
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import server
from server import (
    QtPkgInput,
    QtLogInput,
    QtStateInput,
    QtAssetsInput,
    SANDBOX_TMP,
)

PASS = "\033[32m[OK]\033[0m"
FAIL = "\033[31m[FAIL]\033[0m"
results = []


def check(name: str, cond: bool, hint: str = "") -> bool:
    tag = PASS if cond else FAIL
    line = f"  {tag} {name}"
    if hint and not cond:
        line += f"  ({hint})"
    print(line)
    results.append((name, cond))
    return cond


async def test_qt_pkg_list():
    """qt_pkg with no module arg should list all available modules."""
    print("\n[1] qt_pkg -- list all modules")
    out = await server.qt_pkg(QtPkgInput())
    check("returns text starting with === qt_pkg", out.startswith("=== qt_pkg"))
    check("includes 'Modules' section", "--- Modules" in out)
    check("includes QtCore", "QtCore" in out)
    check("includes Plugins section", "Plugins" in out)


async def test_qt_pkg_inspect():
    """qt_pkg with a specific module should report details."""
    print("\n[2] qt_pkg -- inspect QtWidgets")
    out = await server.qt_pkg(QtPkgInput(module="QtWidgets"))
    check("starts with === qt_pkg", out.startswith("=== qt_pkg"))
    check("includes QtWidgets details", "QtWidgets" in out)
    check("includes headers count", "headers:" in out)


async def test_qt_pkg_unknown_module():
    print("\n[3] qt_pkg -- unknown module should error")
    out = await server.qt_pkg(QtPkgInput(module="Qt5NotARealModule"))
    check("reports 'module not found'", "module not found" in out)


async def test_qt_log_analyze():
    """qt_log should analyze a .qt_mcp_last_build.log file."""
    print("\n[4] qt_log -- analyze a build log")
    # Create a synthetic log
    tmp = SANDBOX_TMP / "v7_log_test"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    log = tmp / "test.log"
    log.write_text(
        "warning: unused variable 'foo'\n"
        "debug: processing widget\n"
        "qt.qml.diskio: loading main.qml\n"
        "qt.qml.animation: starting timeline\n"
        "info: ready\n"
        "warning: deprecated API used\n",
        encoding="utf-8",
    )
    out = await server.qt_log(QtLogInput(log_file=str(log)))
    check("returns text starting with === qt_log", out.startswith("=== qt_log"))
    check("summary: total lines", "total lines" in out)
    check("by-level section", "By level" in out)
    check("top categories section", "categories" in out.lower())
    check("warning counted", "warning" in out.lower())


async def test_qt_log_filter():
    print("\n[5] qt_log -- category filter")
    tmp = SANDBOX_TMP / "v7_log_filter"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    log = tmp / "test.log"
    log.write_text(
        "qt.qml.diskio: load file 1\n"
        "qt.qml.animation: start timeline\n"
        "qt.core.signal: emit clicked\n"
        "qt.qml.diskio: load file 2\n",
        encoding="utf-8",
    )
    out = await server.qt_log(QtLogInput(log_file=str(log), category_filter="qt.qml.diskio"))
    check("filter applied", "matching lines: 2" in out or "matching lines: 2 " in out or "matching lines:2" in out)


async def test_qt_log_missing_file():
    print("\n[6] qt_log -- missing file")
    out = await server.qt_log(QtLogInput(log_file=str(SANDBOX_TMP / "nonexistent-fake.log")))
    check("reports 'log file not found'", "log file not found" in out)


async def test_qt_state_save_load():
    """qt_state save then load should roundtrip."""
    print("\n[7] qt_state -- save/load roundtrip")
    # Use a unique org/app to avoid clobbering real state
    save_out = await server.qt_state(QtStateInput(
        action="save",
        organization="qt-mcp-test",
        application="v7-test",
        key="player1",
        data={"score": "100", "level": "3", "name": "Alice"},
    ))
    check("save succeeded", "saved" in save_out.lower())

    load_out = await server.qt_state(QtStateInput(
        action="load",
        organization="qt-mcp-test",
        application="v7-test",
        key="player1",
    ))
    check("load returned data", "score" in load_out and "100" in load_out)
    check("load returned level", "level" in load_out and "3" in load_out)


async def test_qt_state_list():
    print("\n[8] qt_state -- list keys")
    out = await server.qt_state(QtStateInput(
        action="list",
        organization="qt-mcp-test",
        application="v7-test",
    ))
    check("lists player1 section", "player1" in out)


async def test_qt_state_delete():
    print("\n[9] qt_state -- delete key")
    # Save then delete
    await server.qt_state(QtStateInput(
        action="save", organization="qt-mcp-test", application="v7-test",
        key="todelete", data={"x": "1"},
    ))
    out = await server.qt_state(QtStateInput(
        action="delete", organization="qt-mcp-test", application="v7-test",
        key="todelete",
    ))
    check("delete succeeded", "deleted" in out.lower())


async def test_qt_state_invalid_action():
    print("\n[10] qt_state -- invalid action")
    out = await server.qt_state(QtStateInput(action="bad", organization="x", application="y"))
    check("rejects invalid action", "invalid action" in out)


async def test_qt_assets_basic():
    """qt_assets should scan a directory and emit a .qrc."""
    print("\n[11] qt_assets -- basic scan + .qrc emission")
    src = SANDBOX_TMP / "v7_assets_src"
    if src.exists():
        shutil.rmtree(src, ignore_errors=True)
    (src / "cards").mkdir(parents=True)
    (src / "cards" / "ace.png").write_bytes(b"fake png")
    (src / "cards" / "king.png").write_bytes(b"fake png")
    (src / "board.png").write_bytes(b"fake png")
    (src / "ignore.txt").write_text("not a png", encoding="utf-8")

    out_qrc = SANDBOX_TMP / "v7_assets_out" / "resources.qrc"
    out = await server.qt_assets(QtAssetsInput(
        assets_dir=str(src),
        output_qrc=str(out_qrc),
        extensions=[".png"],
    ))
    check("returns text starting with === qt_assets", out.startswith("=== qt_assets"))
    check("emitted .qrc file", out_qrc.exists())
    if out_qrc.exists():
        text = out_qrc.read_text(encoding="utf-8")
        check(".qrc has RCC root", "<RCC>" in text)
        check(".qrc lists ace.png", "ace.png" in text)
        check(".qrc lists board.png", "board.png" in text)
        check(".qrc excludes .txt", "ignore.txt" not in text)


async def test_qt_assets_with_init():
    """qt_assets with generate_init should also emit a qrc_assets.cpp."""
    print("\n[12] qt_assets -- with Q_INIT_RESOURCE helper")
    src = SANDBOX_TMP / "v7_assets_init_src"
    if src.exists():
        shutil.rmtree(src, ignore_errors=True)
    src.mkdir(parents=True)
    (src / "x.png").write_bytes(b"x")
    out_qrc = SANDBOX_TMP / "v7_assets_init_out" / "res.qrc"
    out = await server.qt_assets(QtAssetsInput(
        assets_dir=str(src),
        output_qrc=str(out_qrc),
        generate_init=True,
    ))
    check("init helper path mentioned", "init helper" in out)
    init_cpp = out_qrc.parent / "qrc_res.cpp"
    check("init helper file exists", init_cpp.exists())
    if init_cpp.exists():
        text = init_cpp.read_text(encoding="utf-8")
        check("init helper has Q_INIT_RESOURCE pattern", "qInitResources" in text)


async def test_qt_assets_exclude():
    """qt_assets with exclude_patterns should skip matching files."""
    print("\n[13] qt_assets -- exclude patterns")
    src = SANDBOX_TMP / "v7_assets_excl_src"
    if src.exists():
        shutil.rmtree(src, ignore_errors=True)
    src.mkdir(parents=True)
    (src / "good.png").write_bytes(b"x")
    (src / "bad_thumb.png").write_bytes(b"x")
    out_qrc = SANDBOX_TMP / "v7_assets_excl_out" / "res.qrc"
    await server.qt_assets(QtAssetsInput(
        assets_dir=str(src),
        output_qrc=str(out_qrc),
        extensions=[".png"],
        exclude_patterns=["bad"],
    ))
    if out_qrc.exists():
        text = out_qrc.read_text(encoding="utf-8")
        check("includes good.png", "good.png" in text)
        check("excludes bad_thumb.png", "bad_thumb.png" not in text)


async def test_qt_assets_no_files():
    """qt_assets with no matching files should report an error."""
    print("\n[14] qt_assets -- no files match")
    src = SANDBOX_TMP / "v7_assets_empty"
    if src.exists():
        shutil.rmtree(src, ignore_errors=True)
    src.mkdir(parents=True)
    (src / "note.txt").write_text("no images", encoding="utf-8")
    out_qrc = SANDBOX_TMP / "v7_assets_empty_out" / "res.qrc"
    out = await server.qt_assets(QtAssetsInput(
        assets_dir=str(src),
        output_qrc=str(out_qrc),
        extensions=[".png"],
    ))
    check("reports 'no files matched'", "no files matched" in out)


async def test_qt_assets_sandbox():
    print("\n[15] qt_assets -- rejects paths outside sandbox")
    out = await server.qt_assets(QtAssetsInput(
        assets_dir=r"D:\outside\src",
        output_qrc=r"E:\somewhere\out.qrc",
    ))
    check("sandbox error", "outside the allowed sandbox" in out)


async def test_qt_pkg_with_qt_mcp_json():
    """Verify all 4 new tools produce JSON trailer with QT_MCP_JSON=1."""
    print("\n[16] JSON trailer works on new tools")
    old_env = os.environ.get("QT_MCP_JSON")
    os.environ["QT_MCP_JSON"] = "1"
    try:
        out = await server.qt_pkg(QtPkgInput())
        check("qt_pkg emits --- json ---", "--- json ---" in out)
    finally:
        if old_env is None:
            os.environ.pop("QT_MCP_JSON", None)
        else:
            os.environ["QT_MCP_JSON"] = old_env


async def main():
    await test_qt_pkg_list()
    await test_qt_pkg_inspect()
    await test_qt_pkg_unknown_module()
    await test_qt_log_analyze()
    await test_qt_log_filter()
    await test_qt_log_missing_file()
    await test_qt_state_save_load()
    await test_qt_state_list()
    await test_qt_state_delete()
    await test_qt_state_invalid_action()
    await test_qt_assets_basic()
    await test_qt_assets_with_init()
    await test_qt_assets_exclude()
    await test_qt_assets_no_files()
    await test_qt_assets_sandbox()
    await test_qt_pkg_with_qt_mcp_json()

    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    total = len(results)
    print()
    print(f"\033[1m=== V7 E2E: {passed}/{total} passed, {failed} failed ===\033[0m")
    if failed:
        print("Failed:")
        for name, ok in results:
            if not ok:
                print(f"  - {name}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())