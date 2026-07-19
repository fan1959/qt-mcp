"""e2e for v18 new tools (v0.3.2):
  - qt_translation_sync   (sync .ts with source tr() calls)
  - qt_async_await_lint   (async / concurrency anti-patterns)
  - qt_hotreload_check    (Q_PROPERTY completeness)
  - qt_perf_budget        (startup time budget)
  - qt_format_check       (clang-format audit + .clang-format init)

Run: python e2e_new_tools_v18.py
"""

import asyncio
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import server
from server import (
    SANDBOX_TMP,
    QtTranslationSyncInput,
    QtAsyncAwaitLintInput,
    QtHotreloadCheckInput,
    QtPerfBudgetInput,
    QtFormatCheckInput,
)

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
            subprocess.run(
                ["cmd", "/c", "rmdir", "/s", "/q", str(p)],
                check=False, capture_output=True, timeout=10,
            )
        except Exception:
            pass
        shutil.rmtree(p, ignore_errors=True)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ---------- qt_translation_sync ----------

async def test_translation_sync_finds_missing_and_orphan():
    print("\n[1] qt_translation_sync -- finds missing + orphan (dry run)")
    d = fresh_dir(SANDBOX_TMP, "v18_tsync_basic")
    (d / "main.cpp").write_text(
        'void f() { QString s = tr("Hello"); QString t = tr("World", "ctx"); }',
        encoding="utf-8",
    )
    ts = d / "i18n.ts"
    ts.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<TS version="2.1" language="en_US">\n'
        '<context>\n'
        '    <name>main</name>\n'
        '    <message><source>Hello</source><translation>Bonjour</translation></message>\n'
        '    <message><source>OldThing</source><translation>Old</translation></message>\n'
        '</context>\n'
        '</TS>\n',
        encoding="utf-8",
    )
    out = await server.qt_translation_sync(QtTranslationSyncInput(
        project_dir=str(d),
        ts_file=str(ts),
        apply=False,
    ))
    check("header in output", "qt_translation_sync" in out)
    check("finds missing 'World'", "'World'" in out)
    check("finds orphan 'OldThing'", "'OldThing'" in out)
    check("reports Apply: False", "Apply: False" in out)
    # File should NOT be modified in dry-run
    check("did NOT modify .ts in dry run", "World" not in ts.read_text(encoding="utf-8"))


async def test_translation_sync_apply_inserts_stubs():
    print("\n[2] qt_translation_sync -- apply=True inserts <message> stubs + .bak")
    d = fresh_dir(SANDBOX_TMP, "v18_tsync_apply")
    (d / "main.cpp").write_text(
        'void f() { QString s = tr("Hello"); QString t = tr("World"); }',
        encoding="utf-8",
    )
    ts = d / "i18n.ts"
    ts.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<TS version="2.1" language="en_US">\n'
        '<context><name>main</name></context>\n'
        '</TS>\n',
        encoding="utf-8",
    )
    out = await server.qt_translation_sync(QtTranslationSyncInput(
        project_dir=str(d),
        ts_file=str(ts),
        apply=True,
    ))
    bak = d / "i18n.ts.bak"
    check("Inserted stubs in report", "Inserted" in out)
    check(".bak created", bak.exists())
    new_text = ts.read_text(encoding="utf-8")
    check("Hello now in .ts", "<source>Hello</source>" in new_text)
    check("World now in .ts", "<source>World</source>" in new_text)
    check(".bak preserves original (no Hello)", "<source>Hello</source>" not in bak.read_text(encoding="utf-8"))


async def test_translation_sync_in_sync_no_diff():
    print("\n[3] qt_translation_sync -- in sync → no divergences")
    d = fresh_dir(SANDBOX_TMP, "v18_tsync_insync")
    (d / "main.cpp").write_text('void f() { tr("Hello"); }', encoding="utf-8")
    ts = d / "i18n.ts"
    ts.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<TS version="2.1" language="en_US">\n'
        '<context><name>main</name><message><source>Hello</source><translation></translation></message></context>\n'
        '</TS>\n',
        encoding="utf-8",
    )
    out = await server.qt_translation_sync(QtTranslationSyncInput(
        project_dir=str(d),
        ts_file=str(ts),
    ))
    check("reports in sync", "in sync" in out.lower() or "0" in out.split("Missing")[1].split("\n")[0])
    check("no Missing section populated", "Missing strings" not in out or "0" in out)


async def test_translation_sync_sandbox_rejection():
    print("\n[4] qt_translation_sync -- sandbox rejection")
    out = await server.qt_translation_sync(QtTranslationSyncInput(
        project_dir=r"C:\Windows",
        ts_file=r"C:\Windows\System32\drivers\etc\hosts",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions sandbox", "sandbox" in out.lower())


# ---------- qt_async_await_lint ----------

async def test_async_lint_qtconcurrent_run():
    print("\n[5] qt_async_await_lint -- QtConcurrent::run warning")
    d = fresh_dir(SANDBOX_TMP, "v18_async_run")
    (d / "w.cpp").write_text(
        '#include <QtConcurrent>\nvoid f() { QtConcurrent::run([](){}); }\n',
        encoding="utf-8",
    )
    out = await server.qt_async_await_lint(QtAsyncAwaitLintInput(
        source_files=[str(d / "w.cpp")],
    ))
    check("detects qtconcurrent_blocking_in_main rule", "qtconcurrent_blocking_in_main" in out)
    check("severity warning present", "warning" in out)


async def test_async_lint_waitforfinished():
    print("\n[6] qt_async_await_lint -- QFuture::waitForFinished warning")
    d = fresh_dir(SANDBOX_TMP, "v18_async_wait")
    (d / "w.cpp").write_text(
        '#include <QFuture>\nvoid f() { QFuture<int> fut; fut.waitForFinished(); }\n',
        encoding="utf-8",
    )
    out = await server.qt_async_await_lint(QtAsyncAwaitLintInput(
        source_files=[str(d / "w.cpp")],
    ))
    check("detects qfuture_waitforfinished", "qfuture_waitforfinished" in out)


async def test_async_lint_qthread_no_eventloop():
    print("\n[7] qt_async_await_lint -- QThread subclass without event loop")
    d = fresh_dir(SANDBOX_TMP, "v18_async_qthread")
    (d / "w.cpp").write_text(
        '#include <QThread>\nclass W : public QThread { void run() { /* no exec() */ } };\n',
        encoding="utf-8",
    )
    out = await server.qt_async_await_lint(QtAsyncAwaitLintInput(
        source_files=[str(d / "w.cpp")],
    ))
    check("detects qthread_no_eventloop", "qthread_no_eventloop" in out)


async def test_async_lint_clean_file():
    print("\n[8] qt_async_await_lint -- clean file produces no findings")
    d = fresh_dir(SANDBOX_TMP, "v18_async_clean")
    (d / "w.cpp").write_text('void f() { int x = 1; }\n', encoding="utf-8")
    out = await server.qt_async_await_lint(QtAsyncAwaitLintInput(
        source_files=[str(d / "w.cpp")],
    ))
    check("reports 0 findings", "Total findings: 0" in out)


async def test_async_lint_json_output():
    print("\n[9] qt_async_await_lint -- json output is valid JSON")
    import json
    d = fresh_dir(SANDBOX_TMP, "v18_async_json")
    (d / "w.cpp").write_text('void f() { QtConcurrent::run([](){}); }\n', encoding="utf-8")
    out = await server.qt_async_await_lint(QtAsyncAwaitLintInput(
        source_files=[str(d / "w.cpp")],
        output_format="json",
    ))
    # When QT_MCP_JSON=1 is in env (set by e2e_v29/v30/v31 autouse fixtures upstream),
    # tool output is followed by `--- json ---` footer (a second JSON object). Take the first.
    parsed = json.loads(out.split("\n\n--- json ---")[0].strip())
    check("json has summary key", "summary" in parsed)
    check("json has findings key", "findings" in parsed)


async def test_async_lint_min_severity_filter():
    print("\n[10] qt_async_await_lint -- min_severity='warning' filters info")
    d = fresh_dir(SANDBOX_TMP, "v18_async_sev")
    (d / "w.cpp").write_text(
        '#include <QThreadPool>\n'
        'void f() { QThreadPool::globalInstance()->start(new QThread); }\n',
        encoding="utf-8",
    )
    out_warn = await server.qt_async_await_lint(QtAsyncAwaitLintInput(
        source_files=[str(d / "w.cpp")], min_severity="warning",
    ))
    out_info = await server.qt_async_await_lint(QtAsyncAwaitLintInput(
        source_files=[str(d / "w.cpp")], min_severity="info",
    ))
    check("warning filter drops qthreadpool_direct_start", "qthreadpool_direct_start" not in out_warn)
    check("info filter keeps qthreadpool_direct_start", "qthreadpool_direct_start" in out_info)


# ---------- qt_hotreload_check ----------

async def test_hotreload_check_missing_notify():
    print("\n[11] qt_hotreload_check -- Q_PROPERTY missing NOTIFY")
    d = fresh_dir(SANDBOX_TMP, "v18_hr_notify")
    (d / "w.h").write_text(
        '#include <QObject>\n'
        'class W : public QObject {\n'
        '    Q_OBJECT\n'
        '    Q_PROPERTY(int value READ value)\n'
        'public:\n'
        '    int value() const { return 0; }\n'
        '};\n',
        encoding="utf-8",
    )
    out = await server.qt_hotreload_check(QtHotreloadCheckInput(
        header_files=[str(d / "w.h")],
    ))
    check("detects missing_notify rule", "missing_notify" in out)
    check("severity warning", "warning" in out)


async def test_hotreload_check_notify_signal_not_found():
    print("\n[12] qt_hotreload_check -- NOTIFY signal not in signals: block")
    d = fresh_dir(SANDBOX_TMP, "v18_hr_signal")
    (d / "w.h").write_text(
        '#include <QObject>\n'
        'class W : public QObject {\n'
        '    Q_OBJECT\n'
        '    Q_PROPERTY(int value READ value WRITE setValue NOTIFY bogusSignal)\n'
        'public:\n'
        '    int value() const { return 0; }\n'
        '    void setValue(int v) {}\n'
        'signals:\n'
        '    void valueChanged(int);\n'
        '};\n',
        encoding="utf-8",
    )
    out = await server.qt_hotreload_check(QtHotreloadCheckInput(
        header_files=[str(d / "w.h")],
    ))
    check("detects notify_signal_not_found", "notify_signal_not_found" in out)
    check("error severity", "error" in out)
    # Should NOT flag valueChanged (which IS declared)
    check("does NOT flag valueChanged", "valueChanged' is not" not in out)


async def test_hotreload_check_constant_with_write():
    print("\n[13] qt_hotreload_check -- CONSTANT + WRITE contradictory")
    d = fresh_dir(SANDBOX_TMP, "v18_hr_constwrite")
    (d / "w.h").write_text(
        '#include <QObject>\n'
        'class W : public QObject {\n'
        '    Q_OBJECT\n'
        '    Q_PROPERTY(int pi READ pi WRITE setPi CONSTANT)\n'
        'public:\n'
        '    int pi() const { return 0; }\n'
        '    void setPi(int v) {}\n'
        '};\n',
        encoding="utf-8",
    )
    out = await server.qt_hotreload_check(QtHotreloadCheckInput(
        header_files=[str(d / "w.h")],
    ))
    check("detects constant_with_write rule", "constant_with_write" in out)


async def test_hotreload_check_member_not_found():
    print("\n[14] qt_hotreload_check -- MEMBER references undeclared variable")
    d = fresh_dir(SANDBOX_TMP, "v18_hr_member")
    (d / "w.h").write_text(
        '#include <QObject>\n'
        'class W : public QObject {\n'
        '    Q_OBJECT\n'
        '    Q_PROPERTY(int count MEMBER m_count)\n'
        '};\n',
        encoding="utf-8",
    )
    out = await server.qt_hotreload_check(QtHotreloadCheckInput(
        header_files=[str(d / "w.h")],
    ))
    check("detects member_variable_not_found", "member_variable_not_found" in out)


async def test_hotreload_check_clean():
    print("\n[15] qt_hotreload_check -- well-formed Q_PROPERTY is clean")
    d = fresh_dir(SANDBOX_TMP, "v18_hr_clean")
    (d / "w.h").write_text(
        '#include <QObject>\n'
        'class W : public QObject {\n'
        '    Q_OBJECT\n'
        '    Q_PROPERTY(int value READ value WRITE setValue NOTIFY valueChanged)\n'
        'public:\n'
        '    int value() const { return 0; }\n'
        '    void setValue(int v) {}\n'
        'signals:\n'
        '    void valueChanged(int);\n'
        '};\n',
        encoding="utf-8",
    )
    out = await server.qt_hotreload_check(QtHotreloadCheckInput(
        header_files=[str(d / "w.h")],
    ))
    check("no findings on well-formed property", "no Q_PROPERTY issues" in out)


async def test_hotreload_check_json():
    print("\n[16] qt_hotreload_check -- json output is valid")
    import json as _json
    d = fresh_dir(SANDBOX_TMP, "v18_hr_json")
    (d / "w.h").write_text('class W { Q_PROPERTY(int v READ v) public: int v() const { return 0; } };\n', encoding="utf-8")
    out = await server.qt_hotreload_check(QtHotreloadCheckInput(
        header_files=[str(d / "w.h")], output_format="json",
    ))
    # When QT_MCP_JSON=1 is in env (set by e2e_v29/v30/v31 autouse fixtures upstream),
    # tool output is followed by `--- json ---` footer. Take the first JSON object.
    parsed = _json.loads(out.split("\n\n--- json ---")[0].strip())
    check("json summary present", "summary" in parsed)
    check("json findings list", isinstance(parsed.get("findings"), list))


# ---------- qt_perf_budget ----------

async def test_perf_budget_executable_not_found():
    print("\n[17] qt_perf_budget -- missing executable returns Error")
    out = await server.qt_perf_budget(QtPerfBudgetInput(
        executable=r"E:\Download_tools\QT\.tmp\nonexistent_xyz.exe",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions not found", "not found" in out.lower())


async def test_perf_budget_sandbox_rejection():
    print("\n[18] qt_perf_budget -- outside sandbox rejected")
    out = await server.qt_perf_budget(QtPerfBudgetInput(
        executable=r"C:\Windows\System32\cmd.exe",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions sandbox", "sandbox" in out.lower())


async def test_perf_budget_runs_against_bat_in_sandbox():
    print("\n[19] qt_perf_budget -- measures first CPU on a long-running .bat")
    bat_dir = fresh_dir(SANDBOX_TMP, "v18_perf_bat")
    bat = bat_dir / "stay_alive.bat"
    bat.write_text("@echo off\r\nping -n 3 127.0.0.1 > nul\r\necho done\r\n", encoding="utf-8")
    out = await server.qt_perf_budget(QtPerfBudgetInput(
        executable=str(bat),
        budget_ms=2000,
        max_wait_ms=2500,
    ))
    check("returns PASS or FAIL header", "Result:" in out)
    check("reports first CPU time", "First CPU activity" in out)
    check("killed after measurement", "killed after measurement" in out)


async def test_perf_budget_invalid_budget():
    print("\n[20] qt_perf_budget -- zero budget returns Error")
    # Use a real .bat inside sandbox so the budget check runs (not the existence check)
    bat_dir = fresh_dir(SANDBOX_TMP, "v18_perf_invbat")
    bat = bat_dir / "x.bat"
    bat.write_text("@echo off\r\nping -n 1 127.0.0.1 > nul\r\n", encoding="utf-8")
    out = await server.qt_perf_budget(QtPerfBudgetInput(
        executable=str(bat),
        budget_ms=0,
        max_wait_ms=500,
    ))
    check("returns Error:", "Error:" in out)
    check("mentions positive", "positive" in out.lower())


# ---------- qt_format_check ----------

_FAKE_CLANG_FORMAT_PY = '''#!/usr/bin/env python3
"""Fake clang-format stub for e2e_v18.

Behavior (accepts any args; identifies the target file as the last positional
that ends in a known C++ suffix):
  - basename contains "dirty" or "BAD" → emit 2 <replacement> entries
  - basename contains "clean" or "GOOD" → no replacements
  - otherwise: no replacements (default clean)
"""
import os
import sys

target = None
for a in sys.argv[1:]:
    if not a.startswith("-"):
        target = a
if not target or not os.path.exists(target):
    sys.exit(0)
name = os.path.splitext(os.path.basename(target))[0]
if "dirty" in name or "BAD" in name:
    print('<replacement offset="0" length="10">int x=1;</replacement>')
    print('<replacement offset="15" length="5">int y=2;</replacement>')
sys.exit(0)
'''


def _write_fake_stub(stub_dir: Path) -> Path:
    """Write the fake clang-format as a Python script. Returns the path to
    a .cmd wrapper that invokes `python <script>`. Used as `clang_format_exe`."""
    script = stub_dir / "_cf_stub.py"
    script.write_text(_FAKE_CLANG_FORMAT_PY, encoding="utf-8")
    wrapper = stub_dir / "cf_stub.cmd"
    wrapper.write_text(
        '@echo off\r\npython "%~dp0\\_cf_stub.py" %*\r\n',
        encoding="utf-8",
    )
    return wrapper


async def test_format_check_no_clang_format_errors():
    print("\n[21] qt_format_check -- missing clang-format returns Error")
    d = fresh_dir(SANDBOX_TMP, "v18_fmt_nocf")
    (d / "x.cpp").write_text("int main() { return 0; }\n", encoding="utf-8")
    # Don't set QT_FORMAT_EXE; rely on the tool's error path
    out = await server.qt_format_check(QtFormatCheckInput(
        target=str(d),
        style="llvm",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions clang-format", "clang-format" in out)


async def test_format_check_with_fake_stub_dirty_count():
    print("\n[22] qt_format_check -- fake stub: aggregates dirty/clean counts")
    d = fresh_dir(SANDBOX_TMP, "v18_fmt_stub")
    stub_dir = d / "_stub"
    stub_dir.mkdir(parents=True, exist_ok=True)
    stub_exe = _write_fake_stub(stub_dir)
    (d / "dirty_a.cpp").write_text("int x=  1;\n", encoding="utf-8")
    (d / "dirty_b.cpp").write_text("int y =2 ;\n", encoding="utf-8")
    (d / "clean_a.cpp").write_text("int z = 3;\n", encoding="utf-8")
    (d / "clean_b.h").write_text("class C {};\n", encoding="utf-8")
    out = await server.qt_format_check(QtFormatCheckInput(
        target=str(d),
        style="llvm",
        clang_format_exe=str(stub_exe),
    ))
    check("audit header", "qt_format_check" in out)
    check("dirty_files = 2", "dirty: 2" in out)
    check("clean_files = 2", "clean: 2" in out)
    check("total replacements = 4", "Total replacements needed: 4" in out)


async def test_format_check_init_clang_format_writes_template():
    print("\n[23] qt_format_check -- init_clang_format=True writes .clang-format")
    d = fresh_dir(SANDBOX_TMP, "v18_fmt_init")
    stub_dir = d / "_stub"
    stub_dir.mkdir(parents=True, exist_ok=True)
    stub_exe = _write_fake_stub(stub_dir)
    (d / "x.cpp").write_text("int z= 1;\n", encoding="utf-8")
    out = await server.qt_format_check(QtFormatCheckInput(
        target=str(d),
        style="qt",
        init_clang_format=True,
        clang_format_exe=str(stub_exe),
    ))
    cf = d / ".clang-format"
    check(".clang-format created", cf.exists())
    check(".clang-format mentions Qt style", "Qt" in cf.read_text(encoding="utf-8"))
    check("reports writing .clang-format", "Wrote .clang-format" in out)


async def test_format_check_init_idempotent_does_not_overwrite():
    print("\n[24] qt_format_check -- init is idempotent (does not overwrite)")
    d = fresh_dir(SANDBOX_TMP, "v18_fmt_idem")
    stub_dir = d / "_stub"
    stub_dir.mkdir(parents=True, exist_ok=True)
    stub_exe = _write_fake_stub(stub_dir)
    (d / "x.cpp").write_text("int z= 1;\n", encoding="utf-8")
    cf = d / ".clang-format"
    cf.write_text("# existing config\nBasedOnStyle: Google\n", encoding="utf-8")
    out = await server.qt_format_check(QtFormatCheckInput(
        target=str(d),
        style="llvm",
        init_clang_format=True,
        clang_format_exe=str(stub_exe),
    ))
    content = cf.read_text(encoding="utf-8")
    check("did NOT overwrite .clang-format", "existing config" in content)
    check("reports no template written", "Wrote .clang-format" not in out)


async def test_format_check_json_output():
    print("\n[25] qt_format_check -- json output is valid")
    import json as _json
    d = fresh_dir(SANDBOX_TMP, "v18_fmt_json")
    stub_dir = d / "_stub"
    stub_dir.mkdir(parents=True, exist_ok=True)
    stub_exe = _write_fake_stub(stub_dir)
    (d / "clean.cpp").write_text("int z= 1;\n", encoding="utf-8")
    out = await server.qt_format_check(QtFormatCheckInput(
        target=str(d),
        style="llvm",
        output_format="json",
        clang_format_exe=str(stub_exe),
    ))
    # When QT_MCP_JSON=1 is in env (set by e2e_v29/v30/v31 autouse fixtures upstream),
    # tool output is followed by `--- json ---` footer. Take the first JSON object.
    parsed = _json.loads(out.split("\n\n--- json ---")[0].strip())
    check("json summary", "summary" in parsed)
    check("json files list", isinstance(parsed.get("files"), list))


# ---------- tool count ----------

async def test_tool_count():
    print("\n[26] tool count -- v0.3.2 should be >= 90")
    tools = await server.mcp.list_tools()
    check(f"tool count >= 90 (got {len(tools)})", len(tools) >= 90)


ALL_TESTS = [
    test_translation_sync_finds_missing_and_orphan,
    test_translation_sync_apply_inserts_stubs,
    test_translation_sync_in_sync_no_diff,
    test_translation_sync_sandbox_rejection,
    test_async_lint_qtconcurrent_run,
    test_async_lint_waitforfinished,
    test_async_lint_qthread_no_eventloop,
    test_async_lint_clean_file,
    test_async_lint_json_output,
    test_async_lint_min_severity_filter,
    test_hotreload_check_missing_notify,
    test_hotreload_check_notify_signal_not_found,
    test_hotreload_check_constant_with_write,
    test_hotreload_check_member_not_found,
    test_hotreload_check_clean,
    test_hotreload_check_json,
    test_perf_budget_executable_not_found,
    test_perf_budget_sandbox_rejection,
    test_perf_budget_runs_against_bat_in_sandbox,
    test_perf_budget_invalid_budget,
    test_format_check_no_clang_format_errors,
    test_format_check_with_fake_stub_dirty_count,
    test_format_check_init_clang_format_writes_template,
    test_format_check_init_idempotent_does_not_overwrite,
    test_format_check_json_output,
    test_tool_count,
]


async def main():
    print("=" * 60)
    print("qt-mcp v0.3.2 e2e (5 new tools)")
    print("=" * 60)
    for t in ALL_TESTS:
        try:
            await t()
        except Exception as e:
            check(f"{t.__name__} (no crash)", False, hint=str(e))
    passed = sum(1 for _, ok in results if ok)
    failed = len(results) - passed
    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {len(results)} total")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
