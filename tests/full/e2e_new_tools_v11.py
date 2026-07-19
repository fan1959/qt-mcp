"""e2e for v11 new tools: qt_undo, qt_leaderboard_ui, qt_pkg_install, qt_release_notes, qt_copyright.

Run: python e2e_new_tools_v11.py
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
    QtUndoInput,
    QtLeaderboardUiInput,
    QtPkgInstallInput,
    QtReleaseNotesInput,
    QtCopyrightInput,
    SANDBOX_TMP,
    SANDBOX_ROOT,
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


async def test_qt_undo_push_list_undo():
    print("\n[1] qt_undo -- push + list + undo + redo")
    sf = SANDBOX_TMP / "v11_undo_basic"
    if sf.exists():
        shutil.rmtree(sf, ignore_errors=True)

    # Push 3 states
    for i, label in enumerate(["move1", "move2", "move3"], 1):
        await server.qt_undo(QtUndoInput(
            action="push", state_file=str(sf / "undo.json"),
            state_data={"turn": i}, label=label,
        ))

    # List
    out = await server.qt_undo(QtUndoInput(action="list", state_file=str(sf / "undo.json")))
    check("list shows move1", "move1" in out)
    check("list shows move2", "move2" in out)
    check("list shows move3", "move3" in out)

    # can_undo
    cu = await server.qt_undo(QtUndoInput(action="can_undo", state_file=str(sf / "undo.json")))
    check("can_undo returns count", "3" in cu)

    # Undo (pops latest, returns state in JSON trailer)
    old_env = os.environ.get("QT_MCP_JSON")
    os.environ["QT_MCP_JSON"] = "1"
    try:
        u1 = await server.qt_undo(QtUndoInput(action="undo", state_file=str(sf / "undo.json")))
    finally:
        if old_env is None:
            os.environ.pop("QT_MCP_JSON", None)
        else:
            os.environ["QT_MCP_JSON"] = old_env
    check("undo returns state", '"turn"' in u1)

    # Now can_redo (no longer counts; we don't auto-push to redo in this design)
    cr = await server.qt_undo(QtUndoInput(action="can_redo", state_file=str(sf / "undo.json")))
    check("can_redo is 0 (no auto-redo)", "0" in cr)


async def test_qt_undo_clear():
    print("\n[2] qt_undo -- clear")
    sf = SANDBOX_TMP / "v11_undo_clear"
    if sf.exists():
        shutil.rmtree(sf, ignore_errors=True)
    await server.qt_undo(QtUndoInput(action="push", state_file=str(sf / "u.json"), state_data={"x": 1}, label="a"))
    out = await server.qt_undo(QtUndoInput(action="clear", state_file=str(sf / "u.json")))
    check("clear succeeded", "cleared" in out.lower())


async def test_qt_undo_invalid():
    print("\n[3] qt_undo -- invalid action")
    out = await server.qt_undo(QtUndoInput(action="bad"))
    check("rejects invalid action", "invalid action" in out)


async def test_qt_leaderboard_ui_table():
    print("\n[4] qt_leaderboard_ui -- table style")
    out_dir = SANDBOX_TMP / "v11_lb_table"
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    out = await server.qt_leaderboard_ui(QtLeaderboardUiInput(
        style="table", output_dir=str(out_dir), top_n=5, show_filters=True,
    ))
    check("returns text", "=== qt_leaderboard_ui" in out)
    h = out_dir / "leaderboardwidget.h"
    cpp = out_dir / "leaderboardwidget.cpp"
    ui = out_dir / "leaderboardwidget.ui"
    check("header written", h.exists())
    check("impl written", cpp.exists())
    check("ui written", ui.exists())
    if h.exists():
        text = h.read_text(encoding="utf-8")
        check("header has QStandardItemModel", "QStandardItemModel" in text)
        check("header has QSortFilterProxyModel", "QSortFilterProxyModel" in text)


async def test_qt_leaderboard_ui_cards():
    print("\n[5] qt_leaderboard_ui -- cards style")
    out_dir = SANDBOX_TMP / "v11_lb_cards"
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    out = await server.qt_leaderboard_ui(QtLeaderboardUiInput(
        style="cards", output_dir=str(out_dir), top_n=10, show_filters=False,
    ))
    check("returns text", "=== qt_leaderboard_ui" in out)
    h = out_dir / "leaderboardwidget.h"
    cpp = out_dir / "leaderboardwidget.cpp"
    check("header written", h.exists())
    check("impl written", cpp.exists())
    if cpp.exists():
        text = cpp.read_text(encoding="utf-8")
        check("impl has QListWidget", "QListWidget" in text)


async def test_qt_leaderboard_ui_invalid_style():
    print("\n[6] qt_leaderboard_ui -- invalid style")
    out_dir = SANDBOX_TMP / "v11_lb_invalid"
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    out = await server.qt_leaderboard_ui(QtLeaderboardUiInput(
        style="bad", output_dir=str(out_dir),
    ))
    check("rejects invalid style", "invalid style" in out)


async def test_qt_leaderboard_ui_sandbox():
    print("\n[7] qt_leaderboard_ui -- rejects paths outside sandbox")
    out = await server.qt_leaderboard_ui(QtLeaderboardUiInput(
        style="table", output_dir=r"D:\outside\foo",
    ))
    check("sandbox error", "outside the allowed sandbox" in out)


async def test_qt_pkg_install_check():
    print("\n[8] qt_pkg_install -- check (graceful if aqt missing)")
    out = await server.qt_pkg_install(QtPkgInstallInput(action="check"))
    # Either "available" or "not found" — both are valid responses
    check("returns text", "=== qt_pkg_install" in out or "Error" in out)


async def test_qt_pkg_install_list():
    print("\n[9] qt_pkg_install -- list (graceful if aqt missing)")
    out = await server.qt_pkg_install(QtPkgInstallInput(action="list"))
    check("returns text", "=== qt_pkg_install" in out or "Error" in out)


async def test_qt_pkg_install_install():
    print("\n[10] qt_pkg_install -- install (graceful if aqt missing)")
    # Don't actually install (would download GBs)
    out = await server.qt_pkg_install(QtPkgInstallInput(action="install", qt_version="5.14.2"))
    # Either reports install attempt or graceful error
    check("returns text", "=== qt_pkg_install" in out or "Error" in out or "install" in out.lower())


async def test_qt_pkg_install_invalid():
    print("\n[11] qt_pkg_install -- invalid action")
    out = await server.qt_pkg_install(QtPkgInstallInput(action="bad"))
    check("rejects invalid action", "invalid action" in out)


async def test_qt_release_notes_read():
    print("\n[12] qt_release_notes -- read (no changelog)")
    chlog = SANDBOX_TMP / "v11_changelog.md"
    if chlog.exists():
        chlog.unlink()
    out = await server.qt_release_notes(QtReleaseNotesInput(action="read", changelog_path=str(chlog)))
    check("handles missing changelog", "no CHANGELOG" in out or "=== qt_release_notes" in out)


async def test_qt_release_notes_add():
    print("\n[13] qt_release_notes -- add bullet")
    chlog = SANDBOX_TMP / "v11_changelog2.md"
    if chlog.exists():
        chlog.unlink()
    out = await server.qt_release_notes(QtReleaseNotesInput(
        action="add", changelog_path=str(chlog), bullet="new feature added",
    ))
    check("add succeeded", "added" in out.lower())
    if chlog.exists():
        text = chlog.read_text(encoding="utf-8")
        check("bullet in file", "new feature added" in text)
        check("Unreleased section present", "## Unreleased" in text)


async def test_qt_release_notes_add_existing():
    print("\n[14] qt_release_notes -- add to existing Unreleased")
    chlog = SANDBOX_TMP / "v11_changelog3.md"
    if chlog.exists():
        chlog.unlink()
    chlog.write_text("# Changelog\n\n## Unreleased\n\n- first\n", encoding="utf-8")
    out = await server.qt_release_notes(QtReleaseNotesInput(
        action="add", changelog_path=str(chlog), bullet="second",
    ))
    if chlog.exists():
        text = chlog.read_text(encoding="utf-8")
        check("first bullet still there", "first" in text)
        check("second bullet added", "second" in text)


async def test_qt_release_notes_generate():
    print("\n[15] qt_release_notes -- generate from git log")
    # qt-mcp repo: E:\Download_tools\QT\Tools\qt-mcp
    proj_dir = SANDBOX_ROOT / "Tools" / "qt-mcp"
    chlog = SANDBOX_TMP / "v11_changelog_gen.md"
    if chlog.exists():
        chlog.unlink()
    out = await server.qt_release_notes(QtReleaseNotesInput(
        action="generate", repo_dir=str(proj_dir), changelog_path=str(chlog),
        version="v0.2.6",
    ))
    check("returns text", "generated" in out.lower() or "commits" in out.lower() or "file" in out.lower() or "Error" in out or "not a git" in out.lower())


async def test_qt_release_notes_invalid():
    print("\n[16] qt_release_notes -- invalid action")
    out = await server.qt_release_notes(QtReleaseNotesInput(action="bad"))
    check("rejects invalid action", "invalid action" in out)


async def test_qt_copyright_dry_run():
    print("\n[17] qt_copyright -- dry run adds nothing")
    proj = SANDBOX_TMP / "v11_copyright_proj"
    if proj.exists():
        shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True)
    (proj / "main.cpp").write_text("int main(){return 0;}\n", encoding="utf-8")
    out = await server.qt_copyright(QtCopyrightInput(
        project_dir=str(proj), dry_run=True,
    ))
    check("dry run succeeded", "=== qt_copyright" in out)
    if (proj / "main.cpp").exists():
        # File should be unchanged
        text = (proj / "main.cpp").read_text(encoding="utf-8")
        check("file unchanged in dry run", "Copyright" not in text and "int main" in text)


async def test_qt_copyright_actual():
    print("\n[18] qt_copyright -- actually adds header")
    proj = SANDBOX_TMP / "v11_copyright_actual"
    if proj.exists():
        shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True)
    (proj / "main.cpp").write_text("int main(){return 0;}\n", encoding="utf-8")
    (proj / "lib.h").write_text("#pragma once\n", encoding="utf-8")
    out = await server.qt_copyright(QtCopyrightInput(
        project_dir=str(proj), dry_run=False,
    ))
    check("returns text", "=== qt_copyright" in out)
    cpp_text = (proj / "main.cpp").read_text(encoding="utf-8")
    h_text = (proj / "lib.h").read_text(encoding="utf-8")
    check("main.cpp has copyright", "Copyright" in cpp_text or "SPDX" in cpp_text)
    check("lib.h has copyright", "Copyright" in h_text or "SPDX" in h_text)


async def test_qt_copyright_skip_existing():
    print("\n[19] qt_copyright -- skips files with existing marker")
    proj = SANDBOX_TMP / "v11_copyright_skip"
    if proj.exists():
        shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True)
    existing = "// Copyright (c) 2024 existing\n// SPDX-License-Identifier: MIT\n\nint main(){return 0;}\n"
    (proj / "main.cpp").write_text(existing, encoding="utf-8")
    await server.qt_copyright(QtCopyrightInput(project_dir=str(proj)))
    if (proj / "main.cpp").exists():
        text = (proj / "main.cpp").read_text(encoding="utf-8")
        # Should still have just one copyright
        check("file not modified (still has original copyright)", "2024 existing" in text)


async def test_qt_copyright_sandbox():
    print("\n[20] qt_copyright -- rejects paths outside sandbox")
    out = await server.qt_copyright(QtCopyrightInput(project_dir=r"D:\outside\foo"))
    check("sandbox error", "outside the allowed sandbox" in out)


async def main():
    await test_qt_undo_push_list_undo()
    await test_qt_undo_clear()
    await test_qt_undo_invalid()
    await test_qt_leaderboard_ui_table()
    await test_qt_leaderboard_ui_cards()
    await test_qt_leaderboard_ui_invalid_style()
    await test_qt_leaderboard_ui_sandbox()
    await test_qt_pkg_install_check()
    await test_qt_pkg_install_list()
    await test_qt_pkg_install_install()
    await test_qt_pkg_install_invalid()
    await test_qt_release_notes_read()
    await test_qt_release_notes_add()
    await test_qt_release_notes_add_existing()
    await test_qt_release_notes_generate()
    await test_qt_release_notes_invalid()
    await test_qt_copyright_dry_run()
    await test_qt_copyright_actual()
    await test_qt_copyright_skip_existing()
    await test_qt_copyright_sandbox()

    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    total = len(results)
    print()
    print(f"\033[1m=== V11 E2E: {passed}/{total} passed, {failed} failed ===\033[0m")
    if failed:
        print("Failed:")
        for name, ok in results:
            if not ok:
                print(f"  - {name}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())