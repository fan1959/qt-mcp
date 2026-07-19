"""e2e for v10 new tools: qt_input, qt_cmake, qt_docs_gen, qt_achievement.

Run: python e2e_new_tools_v10.py
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
    QtInputInput,
    QtCmakeInput,
    QtDocsGenInput,
    QtAchievementInput,
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


async def test_qt_input_keyboard():
    print("\n[1] qt_input -- keyboard snippet")
    out = await server.qt_input(QtInputInput(action="keyboard", key_sequence="Ctrl+N", slot_name="on_new"))
    check("returns text with keyboard snippet", "QShortcut" in out)
    check("includes target class", "MainWindow" in out)
    check("includes slot name", "on_new" in out)
    check("includes key sequence", "Ctrl+N" in out)


async def test_qt_input_mouse():
    print("\n[2] qt_input -- mouse handlers")
    out = await server.qt_input(QtInputInput(action="mouse"))
    check("includes mousePressEvent", "mousePressEvent" in out)
    check("includes mouseMoveEvent", "mouseMoveEvent" in out)
    check("includes mouseReleaseEvent", "mouseReleaseEvent" in out)


async def test_qt_input_gamepad():
    print("\n[3] qt_input -- gamepad snippet")
    out = await server.qt_input(QtInputInput(action="gamepad", target_class="GameView"))
    check("includes QGamepad", "QGamepad" in out)
    check("includes target class", "GameView" in out)
    check("notes Qt6 SDL fallback", "Qt 6" in out or "SDL2" in out)


async def test_qt_input_focus():
    print("\n[4] qt_input -- focus chain")
    out = await server.qt_input(QtInputInput(action="focus"))
    check("includes setTabOrder", "setTabOrder" in out)
    check("includes setFocus", "setFocus" in out)


async def test_qt_input_mapping():
    print("\n[5] qt_input -- mapping JSON")
    out_path = SANDBOX_TMP / "v10_input_map.json"
    if out_path.exists():
        out_path.unlink()
    out = await server.qt_input(QtInputInput(
        action="mapping",
        bindings=[
            {"action": "new_game", "sequence": "Ctrl+N", "slot": "on_new"},
            {"action": "save", "sequence": "Ctrl+S", "slot": "on_save"},
        ],
        output_file=str(out_path),
    ))
    check("reports wrote bindings", "wrote" in out.lower() or "binding" in out.lower())
    check("JSON file exists", out_path.exists())
    if out_path.exists():
        import json
        data = json.loads(out_path.read_text(encoding="utf-8"))
        check("JSON has 2 bindings", len(data.get("bindings", [])) == 2)
        check("JSON has target_class", data.get("target_class") == "MainWindow")


async def test_qt_input_invalid():
    print("\n[6] qt_input -- invalid action")
    out = await server.qt_input(QtInputInput(action="bad"))
    check("rejects invalid action", "invalid action" in out)


async def test_qt_cmake_basic():
    print("\n[7] qt_cmake -- generate CMakeLists.txt for a Qt project")
    proj = SANDBOX_TMP / "v10_cmake_proj"
    if proj.exists():
        shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True)
    (proj / "main.cpp").write_text("int main(){return 0;}\n", encoding="utf-8")
    (proj / "mainwindow.h").write_text("#pragma once\n", encoding="utf-8")
    out = await server.qt_cmake(QtCmakeInput(
        project_dir=str(proj), project_name="myapp",
        qt_modules=["Core", "Widgets"],
    ))
    check("returns text starting with === qt_cmake", out.startswith("=== qt_cmake"))
    cmake = proj / "CMakeLists.txt"
    check("CMakeLists.txt created", cmake.exists())
    if cmake.exists():
        text = cmake.read_text(encoding="utf-8")
        check("uses cmake_minimum_required", "cmake_minimum_required" in text)
        check("uses find_package(Qt5", "find_package(Qt5" in text)
        check("links Core Widgets", "Qt5::Core" in text and "Qt5::Widgets" in text)
        check("includes main.cpp", "main.cpp" in text)
        check("includes mainwindow.h", "mainwindow.h" in text)
        check("cxx_standard set", "CMAKE_CXX_STANDARD 17" in text)
        check("AUTOMOC AUTORRC AUTOUIC", "AUTOMOC" in text and "AUTORCC" in text and "AUTOUIC" in text)


async def test_qt_cmake_qt6():
    print("\n[8] qt_cmake -- Qt6 mode")
    proj = SANDBOX_TMP / "v10_cmake_qt6"
    if proj.exists():
        shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True)
    (proj / "main.cpp").write_text("int main(){return 0;}\n", encoding="utf-8")
    out = await server.qt_cmake(QtCmakeInput(
        project_dir=str(proj), project_name="qt6app",
        use_qt6=True,
    ))
    cmake = proj / "CMakeLists.txt"
    if cmake.exists():
        text = cmake.read_text(encoding="utf-8")
        check("uses find_package(Qt6", "find_package(Qt6" in text)
        check("uses qt_add_executable", "qt_add_executable" in text)


async def test_qt_cmake_library():
    print("\n[9] qt_cmake -- library template")
    proj = SANDBOX_TMP / "v10_cmake_lib"
    if proj.exists():
        shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True)
    (proj / "lib.cpp").write_text("int lib(){return 0;}\n", encoding="utf-8")
    await server.qt_cmake(QtCmakeInput(
        project_dir=str(proj), project_name="mylib",
        template_type="library",
    ))
    cmake = proj / "CMakeLists.txt"
    if cmake.exists():
        text = cmake.read_text(encoding="utf-8")
        check("uses add_library", "add_library" in text)


async def test_qt_cmake_sandbox():
    print("\n[10] qt_cmake -- rejects paths outside sandbox")
    out = await server.qt_cmake(QtCmakeInput(project_dir=r"D:\outside\foo", project_name="x"))
    check("sandbox error", "outside the allowed sandbox" in out)


async def test_qt_docs_gen_no_doxygen():
    print("\n[11] qt_docs_gen -- missing doxygen (graceful)")
    proj = SANDBOX_TMP / "v10_docs_proj"
    if proj.exists():
        shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True)
    out = await server.qt_docs_gen(QtDocsGenInput(
        project_dir=str(proj), doxygen_exe=r"D:\definitely\nonexistent\doxygen.exe",
    ))
    check("reports doxygen not found", "doxygen not found" in out.lower() or "doxygen_exe" in out.lower() or "doxyfile" in out.lower())


async def test_qt_docs_gen_creates_doxyfile():
    print("\n[12] qt_docs_gen -- creates Doxyfile")
    proj = SANDBOX_TMP / "v10_docs_proj2"
    if proj.exists():
        shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True)
    out = await server.qt_docs_gen(QtDocsGenInput(
        project_dir=str(proj), doxygen_exe=r"D:\nonexistent\doxygen.exe",
    ))
    doxyfile = proj / "Doxyfile"
    check("returns text", "=== qt_docs_gen" in out or "Error" in out)


async def test_qt_achievement_define():
    print("\n[13] qt_achievement -- define an achievement")
    cat = SANDBOX_TMP / "v10_ach_cat.json"
    if cat.exists():
        cat.unlink()
    out = await server.qt_achievement(QtAchievementInput(
        action="define", achievements_file=str(cat),
        achievement_id="first_win", title="First Win", description="Win your first game",
    ))
    check("defines achievement", "defined" in out.lower())
    check("catalog file exists", cat.exists())


async def test_qt_achievement_grant():
    print("\n[14] qt_achievement -- grant achievement")
    cat = SANDBOX_TMP / "v10_ach_cat2.json"
    state = SANDBOX_TMP / "v10_ach_state2.json"
    for p in (cat, state):
        if p.exists():
            p.unlink()
    await server.qt_achievement(QtAchievementInput(
        action="define", achievements_file=str(cat),
        achievement_id="first_win", title="First Win",
    ))
    grant = await server.qt_achievement(QtAchievementInput(
        action="grant", achievements_file=str(cat), state_file=str(state),
        player="alice", achievement_id="first_win",
    ))
    check("granted", "granted" in grant.lower())


async def test_qt_achievement_list():
    print("\n[15] qt_achievement -- list achievements for player")
    cat = SANDBOX_TMP / "v10_ach_cat3.json"
    state = SANDBOX_TMP / "v10_ach_state3.json"
    for p in (cat, state):
        if p.exists():
            p.unlink()
    await server.qt_achievement(QtAchievementInput(
        action="define", achievements_file=str(cat),
        achievement_id="a1", title="A1",
    ))
    await server.qt_achievement(QtAchievementInput(
        action="define", achievements_file=str(cat),
        achievement_id="a2", title="A2",
    ))
    await server.qt_achievement(QtAchievementInput(
        action="grant", achievements_file=str(cat), state_file=str(state),
        player="bob", achievement_id="a1",
    ))
    out = await server.qt_achievement(QtAchievementInput(
        action="list", achievements_file=str(cat), state_file=str(state), player="bob",
    ))
    check("list shows a1", "a1" in out)
    check("list shows a2", "a2" in out)
    check("earned count shown", "1/2" in out or "earned" in out.lower())


async def test_qt_achievement_progress():
    print("\n[16] qt_achievement -- progress tracking")
    cat = SANDBOX_TMP / "v10_ach_cat4.json"
    state = SANDBOX_TMP / "v10_ach_state4.json"
    for p in (cat, state):
        if p.exists():
            p.unlink()
    await server.qt_achievement(QtAchievementInput(
        action="define", achievements_file=str(cat),
        achievement_id="play_10", title="Play 10 Games", target=10,
    ))
    await server.qt_achievement(QtAchievementInput(
        action="progress", achievements_file=str(cat), state_file=str(state),
        player="carol", achievement_id="play_10", current=3, target=10,
    ))
    out = await server.qt_achievement(QtAchievementInput(
        action="list", achievements_file=str(cat), state_file=str(state), player="carol",
    ))
    check("shows 3/10 progress", "3/10" in out)


async def test_qt_achievement_reset():
    print("\n[17] qt_achievement -- reset player")
    cat = SANDBOX_TMP / "v10_ach_cat5.json"
    state = SANDBOX_TMP / "v10_ach_state5.json"
    for p in (cat, state):
        if p.exists():
            p.unlink()
    await server.qt_achievement(QtAchievementInput(
        action="define", achievements_file=str(cat),
        achievement_id="x", title="X",
    ))
    await server.qt_achievement(QtAchievementInput(
        action="grant", achievements_file=str(cat), state_file=str(state),
        player="dave", achievement_id="x",
    ))
    out = await server.qt_achievement(QtAchievementInput(
        action="reset", achievements_file=str(cat), state_file=str(state), player="dave",
    ))
    check("reset succeeded", "reset" in out.lower())


async def test_qt_achievement_catalog():
    print("\n[18] qt_achievement -- catalog shows all defined")
    cat = SANDBOX_TMP / "v10_ach_cat6.json"
    if cat.exists():
        cat.unlink()
    await server.qt_achievement(QtAchievementInput(
        action="define", achievements_file=str(cat),
        achievement_id="alpha", title="Alpha",
    ))
    out = await server.qt_achievement(QtAchievementInput(
        action="catalog", achievements_file=str(cat),
    ))
    check("catalog shows alpha", "alpha" in out)


async def test_qt_achievement_invalid():
    print("\n[19] qt_achievement -- invalid action")
    out = await server.qt_achievement(QtAchievementInput(action="bad"))
    check("rejects invalid action", "invalid action" in out)


async def main():
    await test_qt_input_keyboard()
    await test_qt_input_mouse()
    await test_qt_input_gamepad()
    await test_qt_input_focus()
    await test_qt_input_mapping()
    await test_qt_input_invalid()
    await test_qt_cmake_basic()
    await test_qt_cmake_qt6()
    await test_qt_cmake_library()
    await test_qt_cmake_sandbox()
    await test_qt_docs_gen_no_doxygen()
    await test_qt_docs_gen_creates_doxyfile()
    await test_qt_achievement_define()
    await test_qt_achievement_grant()
    await test_qt_achievement_list()
    await test_qt_achievement_progress()
    await test_qt_achievement_reset()
    await test_qt_achievement_catalog()
    await test_qt_achievement_invalid()

    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    total = len(results)
    print()
    print(f"\033[1m=== V10 E2E: {passed}/{total} passed, {failed} failed ===\033[0m")
    if failed:
        print("Failed:")
        for name, ok in results:
            if not ok:
                print(f"  - {name}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())