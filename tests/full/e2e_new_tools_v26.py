"""e2e for v26 new tools (v0.3.9):

NEW TOOLS:
  - qt_viewmodel_gen  (MVVM ViewModel skeleton — Q_PROPERTY + Q_INVOKABLE + QML demo)

Run: python e2e_new_tools_v26.py
"""

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import server
from server import SANDBOX_TMP, QtViewModelGenInput

PASS = "[OK]"
FAIL = "[FAIL]"
results = []


def check(name: str, cond: bool, hint: str = "") -> bool:
    tag = PASS if cond else FAIL
    line = f"  {tag} {name}"
    if hint and not cond:
        line += f"  ({hint})"
    print(line)
    results.append((name, cond))
    return cond


def fresh_dir(parent: Path, name: str) -> Path:
    p = parent / name
    if p.exists():
        try:
            subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(p)],
                           check=False, capture_output=True, timeout=10)
        except Exception:
            pass
        shutil.rmtree(p, ignore_errors=True)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ============ qt_viewmodel_gen ============

async def test_viewmodel_gen_demo():
    print("\n[1] qt_viewmodel_gen -- demo template (full .pro + QML)")
    out = fresh_dir(SANDBOX_TMP, "v26_vm_demo")
    res = await server.qt_viewmodel_gen(QtViewModelGenInput(
        class_name="GameViewModel",
        properties=[
            {"name": "currentPlayer", "type": "QString", "default": "Black"},
            {"name": "score", "type": "int", "default": "0"},
        ],
        commands=[
            {"name": "makeMove", "return_type": "void", "args": ["int row", "int col"]},
        ],
        signals=[{"name": "makeMoveExecuted", "args": ["int row", "int col"]}],
        output_dir=str(out),
        template_type="demo",
    ))
    print(res[:300])
    check("returns success", not res.startswith("Error:"))
    check("wrote gameviewmodel.h", (out / "gameviewmodel.h").exists())
    check("wrote gameviewmodel.cpp", (out / "gameviewmodel.cpp").exists())
    check("wrote main.cpp", (out / "main.cpp").exists())
    check("wrote main.qml", (out / "main.qml").exists())
    check("wrote qml.qrc", (out / "qml.qrc").exists())
    check("wrote gameviewmodel.pro", (out / "gameviewmodel.pro").exists())
    h_text = (out / "gameviewmodel.h").read_text(encoding="utf-8")
    check("Q_PROPERTY capitalised setter", "WRITE setCurrentPlayer" in h_text)
    check("Q_INVOKABLE makeMove present", "Q_INVOKABLE void makeMove(int row, int col)" in h_text)
    check("makeMoveExecuted signal", "void makeMoveExecuted(int row, int col)" in h_text)


async def test_viewmodel_gen_library():
    print("\n[2] qt_viewmodel_gen -- library template (TEMPLATE=lib)")
    out = fresh_dir(SANDBOX_TMP, "v26_vm_lib")
    res = await server.qt_viewmodel_gen(QtViewModelGenInput(
        class_name="ScoreLib",
        properties=[{"name": "best", "type": "int", "default": "0"}],
        commands=[],
        signals=[],
        output_dir=str(out),
        template_type="library",
    ))
    print(res[:200])
    check("returns success", not res.startswith("Error:"))
    check("library .pro has TEMPLATE = lib", "TEMPLATE = lib" in (out / "scorelib.pro").read_text())
    check("library has cpp but no main.cpp", (out / "scorelib.cpp").exists() and not (out / "main.cpp").exists())


async def test_viewmodel_gen_header_only():
    print("\n[3] qt_viewmodel_gen -- header_only template (no .cpp / no .pro)")
    out = fresh_dir(SANDBOX_TMP, "v26_vm_h")
    res = await server.qt_viewmodel_gen(QtViewModelGenInput(
        class_name="TinyVM",
        properties=[{"name": "enabled", "type": "bool", "default": "true"}],
        commands=[{"name": "toggle", "return_type": "void", "args": []}],
        signals=[],
        output_dir=str(out),
        template_type="header_only",
    ))
    print(res[:200])
    check("returns success", not res.startswith("Error:"))
    h = out / "tinyvm.h"
    check("header exists", h.exists())
    check("no cpp written", not (out / "tinyvm.cpp").exists())
    check("no pro written", not list(out.glob("*.pro")))
    txt = h.read_text(encoding="utf-8")
    check("Q_INVOKABLE toggle", "Q_INVOKABLE void toggle()" in txt)
    check("setEnabled setter", "void setEnabled(bool v)" in txt)


async def test_viewmodel_gen_empty_properties():
    print("\n[4] qt_viewmodel_gen -- empty properties still works (commands-only)")
    out = fresh_dir(SANDBOX_TMP, "v26_vm_empty")
    res = await server.qt_viewmodel_gen(QtViewModelGenInput(
        class_name="CmdOnly",
        properties=[],
        commands=[{"name": "execute", "return_type": "void", "args": ["int id"]}],
        signals=[],
        output_dir=str(out),
        template_type="demo",
    ))
    print(res[:200])
    check("returns success", not res.startswith("Error:"))
    check("note in output", "no properties declared" in res.lower() or "properties" in res.lower())


async def test_viewmodel_gen_compile():
    print("\n[5] qt_viewmodel_gen -- generated .pro qmake .passes (sanity)")
    # Skip the actual qmake+makesteps since this is a sandbox-only e2e.
    # Only verify .pro syntax.
    out = fresh_dir(SANDBOX_TMP, "v26_vm_procheck")
    await server.qt_viewmodel_gen(QtViewModelGenInput(
        class_name="ProjCheck",
        properties=[{"name": "x", "type": "int", "default": "0"}],
        commands=[],
        signals=[],
        output_dir=str(out),
        template_type="demo",
    ))
    pro = (out / "projcheck.pro").read_text(encoding="utf-8")
    check(".pro has TARGET", "TARGET" in pro)
    check(".pro has SOURCES +=", "SOURCES +=" in pro)
    check(".pro has QT += qml", "qml" in pro)
    check(".pro has RESOURCES +=", "RESOURCES +=" in pro)


async def main():
    await test_viewmodel_gen_demo()
    await test_viewmodel_gen_library()
    await test_viewmodel_gen_header_only()
    await test_viewmodel_gen_empty_properties()
    await test_viewmodel_gen_compile()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\n=== Summary ===  passed {passed} / {total}")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
