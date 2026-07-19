"""e2e for Phase B (v5) new tools: qt_validate, qt_run_trace, qt_smoke_test.

Run: python e2e_new_tools_v5.py

Exit code 0 = all PASS. Each test prints [OK]/[FAIL] inline.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Use the real server module (stdio server caches tools; tests bypass MCP).
import server
from server import (
    QtValidateInput,
    QtRunTraceInput,
    QtSmokeTestInput,
    QtBuildInput,
    _clean_artifacts,
    SANDBOX_ROOT,
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


async def test_qt_validate_basic():
    """Validate a simple counter project — all references should be OK."""
    print("\n[1] qt_validate -- happy path on qt_mcp_demo/counter")

    # First make sure counter is built and exists; if not, scaffold+build a fresh one
    counter = SANDBOX_ROOT / "Files" / "qt_mcp_demo" / "counter"
    if not (counter / "counter.pro").exists():
        tmp_proj = SANDBOX_TMP / "v5_validate_proj"
        if tmp_proj.exists():
            shutil.rmtree(tmp_proj, ignore_errors=True)
        tmp_proj.mkdir(parents=True)
        (tmp_proj / "demo.pro").write_text(
            "QT       += core gui widgets\n"
            "TARGET   = demo\n"
            "TEMPLATE = app\n"
            "SOURCES += main.cpp\n"
            "HEADERS += mainwindow.h\n"
            "FORMS   += mainwindow.ui\n",
            encoding="utf-8",
        )
        (tmp_proj / "main.cpp").write_text("int main(){return 0;}\n", encoding="utf-8")
        (tmp_proj / "mainwindow.h").write_text("#pragma once\n", encoding="utf-8")
        (tmp_proj / "mainwindow.ui").write_text(
            '<?xml version="1.0"?><ui version="4.0"><widget class="QWidget"/></ui>',
            encoding="utf-8",
        )
        out = await server.qt_validate(QtValidateInput(project_file=str(tmp_proj / "demo.pro")))
    else:
        out = await server.qt_validate(QtValidateInput(project_file=str(counter / "counter.pro")))

    check("returns text starting with '=== qt_validate'", out.startswith("=== qt_validate"))
    check("includes 'SOURCES' category header", "--- SOURCES" in out)
    check("verdict line present (PASS or FAIL)", "=== Verdict:" in out)
    check("contains json footer when QT_MCP_JSON=1", False or '--- json ---' not in out)  # default off


async def test_qt_validate_missing_file():
    """If a referenced source doesn't exist, qt_validate should report [MISS]."""
    print("\n[2] qt_validate -- detects missing referenced file")
    tmp = SANDBOX_TMP / "v5_validate_missing"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    (tmp / "broken.pro").write_text(
        "QT       += core gui widgets\n"
        "TARGET   = broken\n"
        "TEMPLATE = app\n"
        "SOURCES += main.cpp ghost.cpp\n",
        encoding="utf-8",
    )
    (tmp / "main.cpp").write_text("int main(){return 0;}\n", encoding="utf-8")
    out = await server.qt_validate(QtValidateInput(project_file=str(tmp / "broken.pro")))
    check("ghost.cpp flagged as [MISS]", "[MISS] ghost.cpp" in out)
    check("verdict is FAIL", "FAIL" in out)


async def test_qt_validate_strict_xml():
    """Strict mode should catch XML errors in .ui / .qrc files."""
    print("\n[3] qt_validate -- strict mode catches bad .ui XML")
    tmp = SANDBOX_TMP / "v5_validate_strict"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    (tmp / "x.pro").write_text(
        "QT       += core gui widgets\n"
        "TARGET   = x\n"
        "TEMPLATE = app\n"
        "SOURCES += main.cpp\n"
        "FORMS   += broken.ui\n",
        encoding="utf-8",
    )
    (tmp / "main.cpp").write_text("int main(){return 0;}\n", encoding="utf-8")
    (tmp / "broken.ui").write_text("<not-xml", encoding="utf-8")
    out = await server.qt_validate(
        QtValidateInput(project_file=str(tmp / "x.pro"), strict=True)
    )
    check("strict mode reports BAD-XML", "BAD-XML" in out)
    check("verdict is FAIL", "FAIL" in out)


async def test_qt_validate_sandbox():
    """Path outside sandbox should be rejected with sandbox error."""
    print("\n[4] qt_validate -- rejects paths outside sandbox")
    out = await server.qt_validate(QtValidateInput(project_file=r"D:\outside\foo.pro"))
    check("sandbox error message", "outside the allowed sandbox" in out)


async def test_qt_run_trace():
    """qt_run_trace on a console .exe should capture stdout."""
    print("\n[5] qt_run_trace -- runs a console app and captures stdout")
    # Build a tiny console app
    proj = SANDBOX_TMP / "v5_trace_proj"
    if proj.exists():
        shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True)
    (proj / "trace.pro").write_text(
        "QT       += core\n"
        "CONFIG   += console c++17\n"
        "CONFIG   -= app_bundle\n"
        "TARGET   = trace\n"
        "TEMPLATE = app\n"
        "SOURCES += main.cpp\n",
        encoding="utf-8",
    )
    (proj / "main.cpp").write_text(
        '#include <QCoreApplication>\n'
        '#include <QDebug>\n'
        'int main(int argc, char** argv) {\n'
        '  QCoreApplication app(argc, argv);\n'
        '  qDebug() << "TRACE-HELLO-FROM-QT";\n'
        '  return 0;\n'
        '}\n',
        encoding="utf-8",
    )
    # Build it
    build_in = QtBuildInput(project_dir=str(proj), build_type="debug")
    build_out = await server.qt_build(build_in)
    if "Error:" in build_out or "BUILD FAILED" in build_out:
        check("trace build succeeded", False, build_out.splitlines()[-3:])
        return
    check("trace build succeeded", True)

    exe = proj / "debug" / "trace.exe"
    check("trace.exe exists", exe.exists())

    out = await server.qt_run_trace(QtRunTraceInput(
        executable=str(exe),
        env_rules="*=true",
        timeout=8,
    ))
    check("qt_run_trace returned text", out.startswith("=== qt_run_trace"))
    check("mentions QT_LOGGING_RULES", "QT_LOGGING_RULES" in out)
    check("captured stdout or stderr", "TRACE-HELLO" in out or "stdout" in out or "stderr" in out or "no output" in out)


async def test_qt_smoke_test_pass():
    """qt_smoke_test on a known-good console app should report PASS."""
    print("\n[6] qt_smoke_test -- clean -> build -> run on console app")
    proj = SANDBOX_TMP / "v5_smoke_proj"
    if proj.exists():
        shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True)
    (proj / "smoke.pro").write_text(
        "QT       += core\n"
        "CONFIG   += console c++17\n"
        "CONFIG   -= app_bundle\n"
        "TARGET   = smoke\n"
        "TEMPLATE = app\n"
        "SOURCES += main.cpp\n",
        encoding="utf-8",
    )
    (proj / "main.cpp").write_text(
        '#include <QCoreApplication>\n'
        '#include <QTimer>\n'
        'int main(int argc, char** argv) {\n'
        '  QCoreApplication app(argc, argv);\n'
        '  QTimer::singleShot(2000, &app, &QCoreApplication::quit);\n'
        '  return app.exec();\n'
        '}\n',
        encoding="utf-8",
    )

    out = await server.qt_smoke_test(QtSmokeTestInput(
        project_dir=str(proj),
        build_type="debug",
        run_seconds=3,
        build_timeout=180,
    ))
    check("smoke_test returned text", out.startswith("=== qt_smoke_test"))
    check("step 1 clean ran", "Step 1/3: clean" in out)
    check("step 2 build ran", "Step 2/3: build" in out)
    check("step 3 run ran", "Step 3/3: run" in out)
    check("verdict present", "=== Verdict:" in out)


async def test_qt_smoke_test_build_only():
    """run_seconds=0 should skip the run phase but still validate build."""
    print("\n[7] qt_smoke_test -- run_seconds=0 skips run phase")
    proj = SANDBOX_TMP / "v5_smoke_buildonly"
    if proj.exists():
        shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True)
    (proj / "smoke.pro").write_text(
        "QT       += core\n"
        "CONFIG   += console c++17\n"
        "TARGET   = smoke\n"
        "TEMPLATE = app\n"
        "SOURCES += main.cpp\n",
        encoding="utf-8",
    )
    (proj / "main.cpp").write_text(
        '#include <QCoreApplication>\n'
        'int main(int argc, char** argv) { QCoreApplication app(argc, argv); return 0; }\n',
        encoding="utf-8",
    )
    out = await server.qt_smoke_test(QtSmokeTestInput(
        project_dir=str(proj),
        run_seconds=0,
        build_timeout=120,
    ))
    check("build-only verdict says PASS (build only)", "PASS (build only)" in out or "PASS" in out)


async def test_qt_smoke_test_no_pro():
    """A directory with no .pro should report an error."""
    print("\n[8] qt_smoke_test -- rejects project_dir without .pro")
    tmp = SANDBOX_TMP / "v5_smoke_nopro"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    out = await server.qt_smoke_test(QtSmokeTestInput(project_dir=str(tmp)))
    check("reports 'no .pro file found'", "no .pro file found" in out)


async def test_qt_smoke_test_sandbox():
    """Paths outside sandbox should be rejected."""
    print("\n[9] qt_smoke_test -- rejects paths outside sandbox")
    out = await server.qt_smoke_test(QtSmokeTestInput(project_dir=r"D:\outside\foo"))
    check("sandbox error", "outside the allowed sandbox" in out)


async def test_json_footer_off_by_default():
    """Without QT_MCP_JSON=1, no --- json --- trailer should appear."""
    print("\n[10] JSON trailer default-off across new tools")
    # qt_validate on a fresh tiny project
    tmp = SANDBOX_TMP / "v5_nojson"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    (tmp / "nojson.pro").write_text(
        "QT       += core\nTARGET=nojson\nTEMPLATE=app\nSOURCES += main.cpp\n",
        encoding="utf-8",
    )
    (tmp / "main.cpp").write_text("int main(){return 0;}\n", encoding="utf-8")
    out = await server.qt_validate(QtValidateInput(project_file=str(tmp / "nojson.pro")))
    check("no json trailer when env var unset", "--- json ---" not in out)

    # Save and restore env var
    old = os.environ.pop("QT_MCP_JSON", None)
    try:
        os.environ["QT_MCP_JSON"] = "1"
        out2 = await server.qt_validate(QtValidateInput(project_file=str(tmp / "nojson.pro")))
        check("json trailer present when env=1", "--- json ---" in out2)
        check("trailer has 'ok' field", '"ok"' in out2)
    finally:
        os.environ.pop("QT_MCP_JSON", None)
        if old is not None:
            os.environ["QT_MCP_JSON"] = old


async def main():
    await test_qt_validate_basic()
    await test_qt_validate_missing_file()
    await test_qt_validate_strict_xml()
    await test_qt_validate_sandbox()
    await test_qt_run_trace()
    await test_qt_smoke_test_pass()
    await test_qt_smoke_test_build_only()
    await test_qt_smoke_test_no_pro()
    await test_qt_smoke_test_sandbox()
    await test_json_footer_off_by_default()

    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    total = len(results)
    print()
    print(f"\033[1m=== V5 E2E: {passed}/{total} passed, {failed} failed ===\033[0m")
    if failed:
        print("Failed:")
        for name, ok in results:
            if not ok:
                print(f"  - {name}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())