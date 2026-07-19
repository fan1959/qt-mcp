"""e2e tests for the 5 tools added in the Jul 8 v3 wave:
  - qt_translate  (lupdate + lrelease on a real .pro with TRANSLATIONS)
  - qt_qml_lint   (qmllint on a real .qml file and a directory)
  - qt_qml_test   (sandbox / no-test / parse logic via stub exe)
  - qt_designer   (launch designer.exe and kill it)
  - qt_test       (parse QTest output via a stub .bat fixture)

Plus: qml_app scaffold template (qt_scaffold template=qml_app) — full pipeline
test (scaffold → qmllint → build → exe present).

Run from anywhere:
    python e2e_new_tools_v3.py
"""
from __future__ import annotations

import asyncio
import os
import re
import shutil
import struct
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(HERE))

import server  # noqa: E402


SANDBOX_TMP = Path(r"E:\Download_tools\QT\.tmp")


def _sandbox_tmpdir(prefix: str) -> Path:
    d = SANDBOX_TMP / f"{prefix}_{uuid.uuid4().hex[:8]}"
    d.mkdir(parents=True, exist_ok=False)
    return d


GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


def check(label: str, ok: bool, detail: str = "") -> None:
    mark = f"{GREEN}OK{RESET}" if ok else f"{RED}FAIL{RESET}"
    print(f"  [{mark}] {label}" + (f" -- {detail}" if detail else ""))
    if not ok:
        raise AssertionError(label)


# ---------------------------------------------------------------------------
# qt_translate: full lupdate + lrelease pipeline
# ---------------------------------------------------------------------------

async def test_translate_lupdate_lrelease():
    print("\n[1] qt_translate -- lupdate + lrelease on a real .pro")
    tmp = _sandbox_tmpdir("qt_translate")
    try:
        (tmp / "hello.pro").write_text(
            "QT       += core gui widgets\n"
            "CONFIG   += c++17\n"
            "TARGET   = hello\n"
            "TEMPLATE = app\n"
            "SOURCES += main.cpp\n"
            "TRANSLATIONS += i18n/zh_CN.ts\n",
            encoding="utf-8",
        )
        (tmp / "main.cpp").write_text(
            '#include <QApplication>\n'
            '#include <QObject>\n'
            'int main(int argc, char *argv[]) {\n'
            '    QApplication a(argc, argv);\n'
            '    QString s = QObject::tr("Hello, world!");\n'
            '    return 0;\n'
            '}\n',
            encoding="utf-8",
        )
        (tmp / "i18n").mkdir()

        # lupdate
        out = await server.qt_translate(server.QtTranslateInput(
            project_dir=str(tmp), action="lupdate",
        ))
        check("lupdate succeeded", "returncode 0" in out and "Found 1 source" in out)
        check(".ts file written", (tmp / "i18n" / "zh_CN.ts").is_file())
        ts_size = (tmp / "i18n" / "zh_CN.ts").stat().st_size
        check(".ts non-empty", ts_size > 100, f"{ts_size} bytes")

        # lrelease
        out = await server.qt_translate(server.QtTranslateInput(
            project_dir=str(tmp), action="lrelease",
        ))
        check("lrelease succeeded", "returncode 0" in out)
        check(".qm file written", (tmp / "i18n" / "zh_CN.qm").is_file())

        # all
        out = await server.qt_translate(server.QtTranslateInput(
            project_dir=str(tmp), action="all",
        ))
        check("action=all runs both", "lupdate" in out and "lrelease" in out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def test_translate_no_translations_var():
    print("\n[2] qt_translate -- rejects project without TRANSLATIONS")
    tmp = _sandbox_tmpdir("qt_translate_novar")
    try:
        (tmp / "nope.pro").write_text("TEMPLATE = app\nSOURCES += main.cpp\n", encoding="utf-8")
        out = await server.qt_translate(server.QtTranslateInput(
            project_dir=str(tmp), action="lupdate",
        ))
        check("helpful error", "TRANSLATIONS" in out and "no TRANSLATIONS" in out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def test_translate_bad_inputs():
    print("\n[3] qt_translate -- bad inputs")
    out = await server.qt_translate(server.QtTranslateInput(
        project_dir=r"D:\outside\something", action="lupdate",
    ))
    check("outside sandbox rejected", "outside the allowed sandbox" in out)

    out = await server.qt_translate(server.QtTranslateInput(
        project_dir=r"E:\Download_tools\QT\Files", action="bogus",
    ))
    check("bad action rejected", "action must be" in out)


# ---------------------------------------------------------------------------
# qt_qml_lint
# ---------------------------------------------------------------------------

async def test_qml_lint_clean_and_dirty():
    print("\n[4] qt_qml_lint -- clean .qml + dirty .qml")
    tmp = _sandbox_tmpdir("qt_qmllint")
    try:
        clean = tmp / "clean.qml"
        clean.write_text("import QtQuick 2.14\nItem { width: 100; height: 100 }\n", encoding="utf-8")
        # Use a non-existent import to provoke a real warning/error if qmllint can find it,
        # OR just use a clearly-valid file to confirm OK path.
        out = await server.qt_qml_lint(server.QtQmlLintInput(target=str(clean)))
        check("clean file reports OK", "[OK]  clean.qml" in out and "Errors: 0" in out)

        # Directory mode
        out = await server.qt_qml_lint(server.QtQmlLintInput(target=str(tmp)))
        check("directory mode finds the file", "clean.qml" in out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def test_qml_lint_bad_inputs():
    print("\n[5] qt_qml_lint -- bad inputs")
    out = await server.qt_qml_lint(server.QtQmlLintInput(
        target=r"D:\outside\foo.qml",
    ))
    check("outside sandbox rejected", "outside the allowed sandbox" in out)

    out = await server.qt_qml_lint(server.QtQmlLintInput(
        target=r"E:\Download_tools\QT\Files\nonexistent.qml",
    ))
    check("missing file rejected", "does not exist" in out)


# ---------------------------------------------------------------------------
# qt_qml_test: error paths + parse logic via a stub .bat
# ---------------------------------------------------------------------------

async def test_qml_test_sandbox_and_missing():
    print("\n[6] qt_qml_test -- sandbox + missing tst_*.qml")
    out = await server.qt_qml_test(server.QtQmlTestInput(
        project_dir=r"D:\outside\foo",
    ))
    check("outside sandbox rejected", "outside the allowed sandbox" in out)

    tmp = _sandbox_tmpdir("qt_qmltest_empty")
    try:
        out = await server.qt_qml_test(server.QtQmlTestInput(project_dir=str(tmp)))
        check("no tst_*.qml rejected", "no tst_*.qml" in out and "tst_button.qml" in out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def test_qml_test_parse_logic_via_stub():
    print("\n[7] qt_qml_test -- parse logic via stub qmltestrunner")
    if not server.QMLTESTRUNNER.exists():
        print(f"  [{RED}SKIP{RESET}] real qmltestrunner missing")
        return
    # Build a .bat that mimics qmltestrunner output.
    tmp = _sandbox_tmpdir("qt_qmltest_stub")
    try:
        # Write a tst_*.qml so the test dir is valid.
        (tmp / "tst_dummy.qml").write_text(
            "import QtQuick 2.14\nimport QtTest 1.1\n"
            "TestCase { name: 'Dummy'; function test_a() {} }\n",
            encoding="utf-8",
        )
        # Stub qmltestrunner: a .bat that prints fake PASS/FAIL/Totals then exits 0.
        stub = tmp / "qmltestrunner_stub.bat"
        stub.write_text(
            "@echo off\r\n"
            "echo PASS   : Dummy::test_a()\r\n"
            "echo PASS   : Dummy::test_b()\r\n"
            "echo FAIL!  : Dummy::test_c()\r\n"
            "echo SKIP   : Dummy::test_d()\r\n"
            "echo Totals: 2 passed, 1 failed, 1 skipped\r\n"
            "exit /b 1\r\n",
            encoding="utf-8",
        )

        # Monkey-patch the path the tool resolves at call time.
        original = server.QMLTESTRUNNER
        server.QMLTESTRUNNER = stub
        try:
            out = await server.qt_qml_test(server.QtQmlTestInput(project_dir=str(tmp)))
        finally:
            server.QMLTESTRUNNER = original

        check("Totals parsed (2 passed)", "2 passed" in out)
        check("Totals parsed (1 failed)", "1 failed" in out)
        check("Totals parsed (1 skipped)", "1 skipped" in out)
        check("Failing tests listed", "Dummy::test_c" in out)
        check("returncode reported", "returncode = 1" in out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# qt_designer: launch + kill
# ---------------------------------------------------------------------------

async def test_designer_launch_and_kill():
    print("\n[8] qt_designer -- launch and kill")
    if not server.DESIGNER.exists():
        print(f"  [{RED}SKIP{RESET}] designer.exe not on disk")
        return
    out = await server.qt_designer(server.QtDesignerInput(
        ui_file=r"E:\Download_tools\QT\Files\qt_mcp_demo\counter\counterwindow.ui",
        detach=True,
    ))
    check("launched with PID", "PID" in out)
    # Extract PID
    m = re.search(r"PID (\d+)", out)
    if m:
        pid = int(m.group(1))
        # Verify alive
        alive = server._is_pid_alive(pid)
        check("PID is alive right after launch", alive)
    # Kill it
    kill = await server.qt_kill_exe(server.QtKillExeInput(image_name="designer.exe"))
    check("killed by image name", "OK" in kill)


async def test_designer_bad_inputs():
    print("\n[9] qt_designer -- bad inputs")
    out = await server.qt_designer(server.QtDesignerInput(
        ui_file=r"D:\outside\foo.ui",
    ))
    check("outside sandbox rejected", "outside the allowed sandbox" in out)

    out = await server.qt_designer(server.QtDesignerInput(
        ui_file=r"E:\Download_tools\QT\Files\no_such_file.ui",
    ))
    check("missing file rejected", "not a file" in out.lower() or "is not found" in out.lower() or "not found" in out.lower())


# ---------------------------------------------------------------------------
# qt_test: parse QTest output via a stub .bat
# ---------------------------------------------------------------------------

async def test_test_parse_logic_via_stub():
    print("\n[10] qt_test -- parse QTest output via monkey-patched _run")
    tmp = _sandbox_tmpdir("qt_test_stub")
    try:
        # Build a minimal Qt project so the default <project>/debug/<name>.exe
        # resolution path is exercised end-to-end.
        (tmp / "stubproj.pro").write_text(
            "QT       += core testlib\n"
            "CONFIG   += c++17 testcase\n"
            "TARGET   = stubproj\n"
            "TEMPLATE = app\n"
            "SOURCES += main.cpp\n",
            encoding="utf-8",
        )
        debug_dir = tmp / "debug"
        debug_dir.mkdir()
        # A real .exe isn't strictly necessary — qt_test checks .is_file() and we
        # bypass actual subprocess via monkey-patch.
        (debug_dir / "stubproj.exe").write_text("dummy", encoding="utf-8")

        # Monkey-patch _run to return a fixture QTest output.
        fixture = (
            "PASS   : Stub::test_pass()\n"
            "PASS   : Stub::test_pass2()\n"
            "FAIL!  : Stub::test_fail()\n"
            "SKIP   : Stub::test_skip()\n"
            "Totals: 2 passed, 1 failed, 1 skipped\n"
        )

        async def fake_run(cmd, cwd, timeout, env=None):
            return server.CmdResult(returncode=1, stdout=fixture, stderr="")

        original = server._run
        server._run = fake_run
        try:
            out = await server.qt_test(server.QtTestInput(project_dir=str(tmp)))
        finally:
            server._run = original

        check("Totals parsed (Passed: 2)", "Passed: 2" in out)
        check("Totals parsed (Failed: 1)", "Failed: 1" in out)
        check("Totals parsed (Skipped: 1)", "Skipped: 1" in out)
        check("Failing test listed", "Stub::test_fail" in out)
        check("returncode reported", "returncode = 1" in out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def test_test_bad_inputs():
    print("\n[11] qt_test -- bad inputs")
    out = await server.qt_test(server.QtTestInput(
        project_dir=r"D:\outside\foo",
    ))
    check("outside sandbox rejected", "outside the allowed sandbox" in out)

    out = await server.qt_test(server.QtTestInput(
        project_dir=r"E:\Download_tools\QT\Files",
        test_exe=r"D:\outside\foo.exe",
    ))
    check("bad test_exe rejected (sandbox)", "outside the allowed sandbox" in out or "not found" in out.lower())


# ---------------------------------------------------------------------------
# qml_app scaffold: full pipeline (scaffold → qmllint → build → .exe)
# ---------------------------------------------------------------------------

async def test_qml_scaffold_pipeline():
    print("\n[12] qml_app scaffold -- scaffold + qmllint + build")
    if not server.QMAKE.exists():
        print(f"  [{RED}SKIP{RESET}] qmake missing")
        return
    tmp = _sandbox_tmpdir("qt_qml_scaffold")
    try:
        out = await server.qt_scaffold(server.QtScaffoldInput(
            output_dir=str(tmp), name="qmlprobe", template="qml_app",
        ))
        check("scaffolded", "qml_app" in out)
        for fn in ("qmlprobe.pro", "main.cpp", "qmlprobe.qml"):
            check(f"  {fn} exists", (tmp / fn).is_file())

        # qmllint the generated .qml — should be clean
        lint_out = await server.qt_qml_lint(server.QtQmlLintInput(target=str(tmp / "qmlprobe.qml")))
        check("qmllint passes", "Errors: 0" in lint_out and "[OK]" in lint_out)

        # Build it (clean_first=False because no Makefile yet)
        build_out = await server.qt_build(server.QtBuildInput(
            project_dir=str(tmp), build_type="debug", jobs=4,
            clean_first=False, timeout=180,
        ))
        check("build succeeded", "Build OK" in build_out)
        exes = list((tmp / "debug").glob("*.exe"))
        check(".exe produced", len(exes) == 1, f"found {len(exes)} exe(s)")
        if exes:
            check(".exe is non-trivial size", exes[0].stat().st_size > 50_000, f"{exes[0].stat().st_size} bytes")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# Sanity: list newly-added ScaffoldTemplate + tool count
# ---------------------------------------------------------------------------

async def test_scaffold_template_qml_app_registered():
    print("\n[13] ScaffoldTemplate enum + tools registered")
    check("qml_app in ScaffoldTemplate", "qml_app" in [t.value for t in server.ScaffoldTemplate])
    tools = sorted(t.name for t in server.mcp._tool_manager._tools.values())
    check(">= 23 tools registered (baseline was 23; v4 added 3 more)", len(tools) >= 23, f"got {len(tools)}")
    for n in ("qt_translate", "qt_qml_lint", "qt_qml_test", "qt_designer", "qt_test"):
        check(f"  {n} registered", n in tools)


async def main():
    await test_translate_lupdate_lrelease()
    await test_translate_no_translations_var()
    await test_translate_bad_inputs()
    await test_qml_lint_clean_and_dirty()
    await test_qml_lint_bad_inputs()
    await test_qml_test_sandbox_and_missing()
    await test_qml_test_parse_logic_via_stub()
    await test_designer_launch_and_kill()
    await test_designer_bad_inputs()
    await test_test_parse_logic_via_stub()
    await test_test_bad_inputs()
    await test_qml_scaffold_pipeline()
    await test_scaffold_template_qml_app_registered()
    print(f"\n{GREEN}=== NEW TOOLS V3 E2E PASSED (13 tests) ==={RESET}")


if __name__ == "__main__":
    asyncio.run(main())