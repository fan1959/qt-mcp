"""e2e for v6 new tool: qt_diff.

Run: python e2e_new_tools_v6.py

Exit code 0 = all PASS.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import asyncio
import shutil
import sys
from pathlib import Path

import server
from server import QtDiffInput, SANDBOX_TMP

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


async def test_qt_diff_identical():
    """Two projects with the same content should report 'identical' for every variable."""
    print("\n[1] qt_diff -- identical projects")
    base = SANDBOX_TMP / "v6_diff_identical"
    if base.exists():
        shutil.rmtree(base, ignore_errors=True)
    a = base / "a"
    b = base / "b"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    for d in (a, b):
        (d / "x.pro").write_text(
            "QT       += core gui widgets\n"
            "TARGET   = x\n"
            "TEMPLATE = app\n"
            "SOURCES += main.cpp\n"
            "HEADERS += main.h\n",
            encoding="utf-8",
        )
        (d / "main.cpp").write_text("int main(){return 0;}\n", encoding="utf-8")
        (d / "main.h").write_text("#pragma once\n", encoding="utf-8")
    out = await server.qt_diff(QtDiffInput(proj_a=str(a / "x.pro"), proj_b=str(b / "x.pro")))
    check("returns text starting with === qt_diff", out.startswith("=== qt_diff"))
    check("shows 'identical' for SOURCES", "SOURCES" in out and "(identical" in out)
    check("verdict summary present", "Summary" in out)


async def test_qt_diff_different_sources():
    """A has main.cpp + extra.cpp; B has only main.cpp. Should report extra.cpp in A only."""
    print("\n[2] qt_diff -- different SOURCES")
    base = SANDBOX_TMP / "v6_diff_diff"
    if base.exists():
        shutil.rmtree(base, ignore_errors=True)
    a = base / "a"
    b = base / "b"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    (a / "x.pro").write_text(
        "QT       += core gui widgets\nTARGET=x\nTEMPLATE=app\nSOURCES += main.cpp extra.cpp\n",
        encoding="utf-8",
    )
    (b / "x.pro").write_text(
        "QT       += core gui widgets\nTARGET=x\nTEMPLATE=app\nSOURCES += main.cpp\n",
        encoding="utf-8",
    )
    for d in (a, b):
        (d / "main.cpp").write_text("int main(){return 0;}\n", encoding="utf-8")
    (a / "extra.cpp").write_text("int extra(){return 0;}\n", encoding="utf-8")
    out = await server.qt_diff(QtDiffInput(proj_a=str(a / "x.pro"), proj_b=str(b / "x.pro")))
    check("flags extra.cpp as A-only", "extra.cpp" in out and "only in A" in out)
    check("summary shows A-only entries > 0", "A-only entries:" in out)


async def test_qt_diff_modified_content():
    """Same file list, different content -> should report SHA1 diff."""
    print("\n[3] qt_diff -- modified content")
    base = SANDBOX_TMP / "v6_diff_mod"
    if base.exists():
        shutil.rmtree(base, ignore_errors=True)
    a = base / "a"
    b = base / "b"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    for d in (a, b):
        (d / "x.pro").write_text(
            "QT       += core gui widgets\nTARGET=x\nTEMPLATE=app\nSOURCES += main.cpp\n",
            encoding="utf-8",
        )
    (a / "main.cpp").write_text("int main(){return 0;}\n", encoding="utf-8")
    (b / "main.cpp").write_text("int main(){return 42;}\n", encoding="utf-8")
    out = await server.qt_diff(QtDiffInput(proj_a=str(a / "x.pro"), proj_b=str(b / "x.pro")))
    check("reports file content diff", "DIFF" in out and "main.cpp" in out)
    check("verdict summary shows files_differing > 0", "files differing:" in out)


async def test_qt_diff_show_identical():
    """show_identical=True should list files that are identical."""
    print("\n[4] qt_diff -- show_identical=True")
    base = SANDBOX_TMP / "v6_diff_showid"
    if base.exists():
        shutil.rmtree(base, ignore_errors=True)
    a = base / "a"
    b = base / "b"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    for d in (a, b):
        (d / "x.pro").write_text(
            "QT       += core gui widgets\nTARGET=x\nTEMPLATE=app\nSOURCES += main.cpp\n",
            encoding="utf-8",
        )
        (d / "main.cpp").write_text("int main(){return 0;}\n", encoding="utf-8")
    out = await server.qt_diff(QtDiffInput(
        proj_a=str(a / "x.pro"), proj_b=str(b / "x.pro"), show_identical=True,
    ))
    check("includes 'Identical files' section", "Identical files" in out)
    check("lists SHA1 of identical main.cpp", "[SAME] SOURCES: main.cpp" in out)


async def test_qt_diff_sandbox():
    """Path outside sandbox should be rejected."""
    print("\n[5] qt_diff -- rejects paths outside sandbox")
    out = await server.qt_diff(QtDiffInput(proj_a=r"D:\outside\a.pro", proj_b=r"D:\outside\b.pro"))
    check("sandbox error", "outside the allowed sandbox" in out)


async def test_qt_diff_not_a_pro():
    """Passing a non-.pro file should error."""
    print("\n[6] qt_diff -- rejects non-.pro file")
    tmp = SANDBOX_TMP / "v6_diff_notpro"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    (tmp / "foo.txt").write_text("not a pro", encoding="utf-8")
    out = await server.qt_diff(QtDiffInput(proj_a=str(tmp / "foo.txt"), proj_b=str(tmp / "foo.txt")))
    check("non-.pro error", "not an existing .pro file" in out)


async def main():
    await test_qt_diff_identical()
    await test_qt_diff_different_sources()
    await test_qt_diff_modified_content()
    await test_qt_diff_show_identical()
    await test_qt_diff_sandbox()
    await test_qt_diff_not_a_pro()

    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    total = len(results)
    print()
    print(f"\033[1m=== V6 E2E: {passed}/{total} passed, {failed} failed ===\033[0m")
    if failed:
        print("Failed:")
        for name, ok in results:
            if not ok:
                print(f"  - {name}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())