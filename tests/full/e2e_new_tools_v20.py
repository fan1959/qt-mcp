"""e2e for v20 new tools (v0.3.4):
  - qt_perf_compare             (regression detection vs baseline JSON)
  - qt_resource_validate        (deep .qrc validation: naming / case / depth / size / prefix)
  - qt_test_coverage_diff       (lcov regression comparison)
  - qt_screenshot_baseline_capture (multi-scale baseline PNGs)
  - qt_console_messages         (runtime text-widget capture via pywinauto)

Run: python e2e_new_tools_v20.py
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import server
from server import (
    SANDBOX_TMP,
    QtPerfCompareInput,
    QtResourceValidateInput,
    QtTestCoverageDiffInput,
    QtScreenshotBaselineCaptureInput,
    QtConsoleMessagesInput,
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


# ---------- qt_perf_compare ----------

async def test_perf_compare_executable_not_found():
    print("\n[1] qt_perf_compare -- missing executable returns Error")
    d = fresh_dir(SANDBOX_TMP, "v20_pf_noexe")
    fake = d / "no_such_app.exe"
    baseline = d / "baseline.json"
    baseline.write_text('{"first_cpu_ms": 100, "first_window_ms": 200}', encoding="utf-8")
    out = await server.qt_perf_compare(QtPerfCompareInput(
        executable=str(fake),
        baseline_json=str(baseline),
    ))
    check("returns Error:", "Error:" in out)
    check("mentions executable", "executable" in out.lower())


async def test_perf_compare_baseline_not_found():
    print("\n[2] qt_perf_compare -- missing baseline_json returns Error")
    d = fresh_dir(SANDBOX_TMP, "v20_pf_nobs")
    fake_exe = d / "fake.exe"
    fake_exe.write_bytes(b"MZ")
    fake = d / "no_such_baseline.json"
    out = await server.qt_perf_compare(QtPerfCompareInput(
        executable=str(fake_exe),
        baseline_json=str(fake),
    ))
    check("returns Error:", "Error:" in out)
    check("mentions baseline_json", "baseline_json" in out.lower() or "baseline" in out.lower() or "not found" in out.lower())


async def test_perf_compare_baseline_missing_field():
    print("\n[3] qt_perf_compare -- baseline_json missing first_cpu_ms returns Error")
    d = fresh_dir(SANDBOX_TMP, "v20_pf_nofield")
    fake_exe = d / "fake.exe"
    fake_exe.write_bytes(b"MZ")
    baseline = d / "baseline.json"
    baseline.write_text('{"first_window_ms": 200}', encoding="utf-8")
    out = await server.qt_perf_compare(QtPerfCompareInput(
        executable=str(fake_exe),
        baseline_json=str(baseline),
    ))
    check("returns Error:", "Error:" in out)
    check("mentions first_cpu_ms", "first_cpu_ms" in out.lower() or "missing" in out.lower())


async def test_perf_compare_negative_threshold():
    print("\n[4] qt_perf_compare -- regression_ms<0 returns Error")
    d = fresh_dir(SANDBOX_TMP, "v20_pf_negthr")
    fake_exe = d / "fake.exe"
    fake_exe.write_bytes(b"MZ")
    baseline = d / "baseline.json"
    baseline.write_text('{"first_cpu_ms": 100, "first_window_ms": 200}', encoding="utf-8")
    out = await server.qt_perf_compare(QtPerfCompareInput(
        executable=str(fake_exe),
        baseline_json=str(baseline),
        regression_ms=-10,
    ))
    check("returns Error:", "Error:" in out)


async def test_perf_compare_happy_path_notepad():
    print("\n[5] qt_perf_compare -- happy path with notepad.exe (copied to sandbox)")
    d = fresh_dir(SANDBOX_TMP, "v20_pf_happy")
    baseline = d / "baseline.json"
    # Baseline claims very slow times to make PASS/FAIL deterministic
    baseline.write_text('{"first_cpu_ms": 5000, "first_window_ms": 10000}', encoding="utf-8")
    exe_in_sandbox = d / "notepad.exe"
    if not exe_in_sandbox.exists():
        try:
            shutil.copy(r"C:\Windows\notepad.exe", str(exe_in_sandbox))
        except OSError as e:
            check(f"copy notepad.exe to sandbox: {e}", False, hint=str(e))
            return
    out = await server.qt_perf_compare(QtPerfCompareInput(
        executable=str(exe_in_sandbox),
        baseline_json=str(baseline),
        regression_ms=2000,
        max_wait_ms=5000,
    ))
    # notepad.exe should launch in well under baseline (5000ms), so PASS expected
    check("returns Result line", "Result:" in out)
    check("json footer has result", '"result"' in out or "result" in out.lower())


# ---------- qt_resource_validate ----------

async def test_resource_validate_file_not_found():
    print("\n[6] qt_resource_validate -- missing qrc_file returns Error")
    d = fresh_dir(SANDBOX_TMP, "v20_rv_nofile")
    fake = d / "no_such.qrc"
    out = await server.qt_resource_validate(QtResourceValidateInput(qrc_file=str(fake)))
    check("returns Error:", "Error:" in out)


async def test_resource_validate_happy_path():
    print("\n[7] qt_resource_validate -- clean .qrc yields PASS")
    d = fresh_dir(SANDBOX_TMP, "v20_rv_happy")
    qrc = d / "clean.qrc"
    # Create a real image so missing_on_disk doesn't fire
    img = d / "icon.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    qrc.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE RCC>\n'
        '<RCC version="1.0">\n'
        '  <qresource prefix="/icons">\n'
        '    <file>icon.png</file>\n'
        '  </qresource>\n'
        '</RCC>\n',
        encoding="utf-8",
    )
    out = await server.qt_resource_validate(QtResourceValidateInput(qrc_file=str(qrc)))
    check("returns report", "qt_resource_validate" in out or "Findings" in out)
    check("no missing_on_disk error", "missing_on_disk" not in out)


async def test_resource_validate_naming_violation():
    print("\n[8] qt_resource_validate -- filename with spaces fires naming_convention")
    d = fresh_dir(SANDBOX_TMP, "v20_rv_naming")
    img = d / "My Image.PNG"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    qrc = d / "bad.qrc"
    qrc.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE RCC>\n'
        '<RCC version="1.0">\n'
        '  <qresource prefix="/icons">\n'
        '    <file>My Image.PNG</file>\n'
        '  </qresource>\n'
        '</RCC>\n',
        encoding="utf-8",
    )
    out = await server.qt_resource_validate(QtResourceValidateInput(qrc_file=str(qrc)))
    check("flags naming_convention", "naming_convention" in out)


async def test_resource_validate_case_collision():
    print("\n[9] qt_resource_validate -- two files differing only in case fires case_collision")
    d = fresh_dir(SANDBOX_TMP, "v20_rv_case")
    img1 = d / "Icon.PNG"
    img2 = d / "icon.png"
    img1.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    img2.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    qrc = d / "case.qrc"
    qrc.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE RCC>\n'
        '<RCC version="1.0">\n'
        '  <qresource prefix="/icons">\n'
        '    <file>Icon.PNG</file>\n'
        '    <file>icon.png</file>\n'
        '  </qresource>\n'
        '</RCC>\n',
        encoding="utf-8",
    )
    out = await server.qt_resource_validate(QtResourceValidateInput(qrc_file=str(qrc)))
    check("flags case_collision", "case_collision" in out or "duplicate_entry" in out)


async def test_resource_validate_missing_on_disk():
    print("\n[10] qt_resource_validate -- referencing nonexistent file fires missing_on_disk")
    d = fresh_dir(SANDBOX_TMP, "v20_rv_missing")
    qrc = d / "miss.qrc"
    qrc.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE RCC>\n'
        '<RCC version="1.0">\n'
        '  <qresource prefix="/icons">\n'
        '    <file>does_not_exist.png</file>\n'
        '  </qresource>\n'
        '</RCC>\n',
        encoding="utf-8",
    )
    out = await server.qt_resource_validate(QtResourceValidateInput(qrc_file=str(qrc)))
    check("flags missing_on_disk", "missing_on_disk" in out)
    check("Result is FAIL", "FAIL" in out)


async def test_resource_validate_output_json():
    print("\n[11] qt_resource_validate -- output_format=json returns JSON")
    d = fresh_dir(SANDBOX_TMP, "v20_rv_json")
    qrc = d / "j.qrc"
    qrc.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE RCC>\n'
        '<RCC version="1.0">\n'
        '  <qresource prefix="/">\n'
        '    <file>missing.png</file>\n'
        '  </qresource>\n'
        '</RCC>\n',
        encoding="utf-8",
    )
    out = await server.qt_resource_validate(QtResourceValidateInput(qrc_file=str(qrc), output_format="json"))
    check("output contains JSON", "{" in out and "findings" in out)
    check("parses as JSON", isinstance(json.loads(out.split("\n--- json ---")[0].strip()), dict))


# ---------- qt_test_coverage_diff ----------

def _write_lcov(path: Path, files: dict[str, tuple[int, int]]) -> None:
    """Helper: write a synthetic lcov .info file with given files."""
    lines = []
    for f, (lf, lh) in files.items():
        lines.append(f"SF:{f}")
        lines.append(f"LF:{lf}")
        lines.append(f"LH:{lh}")
        lines.append("end_of_record")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def test_coverage_diff_baseline_not_found():
    print("\n[12] qt_test_coverage_diff -- missing baseline_info returns Error")
    d = fresh_dir(SANDBOX_TMP, "v20_cd_noinfo")
    fake = d / "no.info"
    cur = d / "cur.info"
    cur.write_text("SF:x\nLF:10\nLH:5\nend_of_record\n", encoding="utf-8")
    out = await server.qt_test_coverage_diff(QtTestCoverageDiffInput(
        baseline_info=str(fake),
        current_info=str(cur),
    ))
    check("returns Error:", "Error:" in out)


async def test_coverage_diff_empty_info_file():
    print("\n[13] qt_test_coverage_diff -- empty/invalid info file returns Error")
    d = fresh_dir(SANDBOX_TMP, "v20_cd_empty")
    base = d / "base.info"
    base.write_text("", encoding="utf-8")
    cur = d / "cur.info"
    cur.write_text("SF:x\nLF:10\nLH:5\nend_of_record\n", encoding="utf-8")
    out = await server.qt_test_coverage_diff(QtTestCoverageDiffInput(
        baseline_info=str(base),
        current_info=str(cur),
    ))
    check("returns Error:", "Error:" in out)


async def test_coverage_diff_identical_passes():
    print("\n[14] qt_test_coverage_diff -- identical files yield PASS")
    d = fresh_dir(SANDBOX_TMP, "v20_cd_identical")
    base = d / "base.info"
    cur = d / "cur.info"
    files = {"src/a.cpp": (100, 80), "src/b.cpp": (50, 30)}
    _write_lcov(base, files)
    _write_lcov(cur, files)
    out = await server.qt_test_coverage_diff(QtTestCoverageDiffInput(
        baseline_info=str(base),
        current_info=str(cur),
    ))
    check("Result is PASS", "PASS" in out)
    check("Overall delta 0.00%", "0.00%" in out or "+0.00%" in out)


async def test_coverage_diff_regression_fails():
    print("\n[15] qt_test_coverage_diff -- coverage drop fires FAIL")
    d = fresh_dir(SANDBOX_TMP, "v20_cd_regr")
    base = d / "base.info"
    cur = d / "cur.info"
    _write_lcov(base, {"src/a.cpp": (100, 95), "src/b.cpp": (50, 45)})  # 95% / 90%
    _write_lcov(cur,  {"src/a.cpp": (100, 50), "src/b.cpp": (50, 45)})  # 50% / 90%
    out = await server.qt_test_coverage_diff(QtTestCoverageDiffInput(
        baseline_info=str(base),
        current_info=str(cur),
        regression_threshold=0.02,
    ))
    check("Result is FAIL", "FAIL" in out)
    check("mentions regression", "regress" in out.lower())


async def test_coverage_diff_output_json():
    print("\n[16] qt_test_coverage_diff -- output_format=json returns JSON")
    d = fresh_dir(SANDBOX_TMP, "v20_cd_json")
    base = d / "base.info"
    cur = d / "cur.info"
    files = {"src/a.cpp": (100, 80)}
    _write_lcov(base, files)
    _write_lcov(cur, files)
    out = await server.qt_test_coverage_diff(QtTestCoverageDiffInput(
        baseline_info=str(base),
        current_info=str(cur),
        output_format="json",
    ))
    check("JSON contains baseline_cov", '"baseline_cov"' in out)


# ---------- qt_screenshot_baseline_capture ----------

async def test_screenshot_baseline_empty_scale_factors():
    print("\n[17] qt_screenshot_baseline_capture -- empty scale_factors returns Error")
    out = await server.qt_screenshot_baseline_capture(QtScreenshotBaselineCaptureInput(
        executable=r"C:\Windows\notepad.exe",
        scale_factors=[],
    ))
    check("returns Error:", "Error:" in out)


async def test_screenshot_baseline_negative_scale():
    print("\n[18] qt_screenshot_baseline_capture -- negative scale_factor returns Error")
    out = await server.qt_screenshot_baseline_capture(QtScreenshotBaselineCaptureInput(
        executable=r"C:\Windows\notepad.exe",
        scale_factors=[1.0, -2.0],
    ))
    check("returns Error:", "Error:" in out)


async def test_screenshot_baseline_executable_not_found():
    print("\n[19] qt_screenshot_baseline_capture -- missing executable returns Error")
    d = fresh_dir(SANDBOX_TMP, "v20_sb_noexe")
    fake = d / "no_such.exe"
    out = await server.qt_screenshot_baseline_capture(QtScreenshotBaselineCaptureInput(
        executable=str(fake),
        scale_factors=[1.0],
        output_dir=str(d / "out"),
    ))
    check("returns Error:", "Error:" in out)


async def test_screenshot_baseline_happy_notepad():
    print("\n[20] qt_screenshot_baseline_capture -- happy path with notepad.exe (copied)")
    d = fresh_dir(SANDBOX_TMP, "v20_sb_happy")
    exe_in_sandbox = d / "notepad.exe"
    if not exe_in_sandbox.exists():
        try:
            shutil.copy(r"C:\Windows\notepad.exe", str(exe_in_sandbox))
        except OSError as e:
            check(f"copy notepad.exe to sandbox: {e}", False, hint=str(e))
            return
    out_dir = d / "captures"
    out = await server.qt_screenshot_baseline_capture(QtScreenshotBaselineCaptureInput(
        executable=str(exe_in_sandbox),
        scale_factors=[1.0],
        output_dir=str(out_dir),
        wait_seconds=2,
        label="test_happy",
    ))
    check("returns report header", "qt_screenshot_baseline_capture" in out)
    check("Manifest path mentioned", "manifest" in out.lower() or "Captured" in out)


# ---------- qt_console_messages ----------

async def test_console_messages_no_exe_no_pid():
    print("\n[21] qt_console_messages -- process_id=0 + no executable returns Error")
    out = await server.qt_console_messages(QtConsoleMessagesInput(
        process_id=0,
        executable="",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions executable", "executable" in out.lower())


async def test_console_messages_executable_not_found():
    print("\n[22] qt_console_messages -- missing executable returns Error")
    d = fresh_dir(SANDBOX_TMP, "v20_cm_noexe")
    fake = d / "no_such.exe"
    out = await server.qt_console_messages(QtConsoleMessagesInput(
        process_id=0,
        executable=str(fake),
    ))
    check("returns Error:", "Error:" in out)


async def test_console_messages_spawn_then_attach_fails_cleanly():
    print("\n[23] qt_console_messages -- spawn-then-attach code path (no real Qt app needed)")
    d = fresh_dir(SANDBOX_TMP, "v20_cm_spawn_attach")
    # Spawn a Python subprocess (lives in sandbox as long as we use sys.executable)
    # We use a tiny .py that just sleeps, so process survives and pywinauto can attach.
    test_script = d / "_sleeper.py"
    test_script.write_text("import time, sys\nsys.stdout.write('READY\\n')\nsys.stdout.flush()\ntime.sleep(30)\n", encoding="utf-8")
    import subprocess as _sp
    py_exe = sys.executable
    # Check py_exe is in sandbox
    py_in_sandbox = Path(py_exe).resolve()
    if str(py_in_sandbox).startswith(str(Path(server.SANDBOX_ROOT).resolve())):
        # Python is inside sandbox — use it directly
        proc = _sp.Popen([py_exe, str(test_script)], cwd=str(d),
                         stdout=_sp.PIPE, stderr=_sp.PIPE)
        try:
            import time as _t
            _t.sleep(1.0)  # let script start
            out = await server.qt_console_messages(QtConsoleMessagesInput(
                process_id=proc.pid,
                wait_seconds=0,
                max_messages=10,
                auto_id_contains="",
            ))
            # Either we attach successfully (no text widget, so empty result) OR
            # attach fails because the python process has no UI window
            check("returns report header", "qt_console_messages" in out)
            check("mentions process", f"pid={proc.pid}" in out or "Process:" in out)
        finally:
            proc.kill()
            try:
                proc.wait(timeout=2)
            except _sp.TimeoutExpired:
                pass
    else:
        # Python not in sandbox — skip with conditional OK
        check("python in sandbox: SKIP (not in sandbox, can't test attach)", True)


async def test_console_messages_invalid_pid():
    print("\n[24] qt_console_messages -- invalid process_id returns Error")
    out = await server.qt_console_messages(QtConsoleMessagesInput(
        process_id=999999,
    ))
    check("returns Error:", "Error:" in out)


async def test_console_messages_level_filter_token_no_match():
    print("\n[25] qt_console_messages -- level_filter reduces messages to 0 (test with spawned Python)")
    d = fresh_dir(SANDBOX_TMP, "v20_cm_filter")
    test_script = d / "_sleeper.py"
    test_script.write_text("import time, sys\ntime.sleep(30)\n", encoding="utf-8")
    import subprocess as _sp
    py_exe = sys.executable
    py_in_sandbox = Path(py_exe).resolve()
    if not str(py_in_sandbox).startswith(str(Path(server.SANDBOX_ROOT).resolve())):
        check("python in sandbox: SKIP", True)
        return
    proc = _sp.Popen([py_exe, str(test_script)], cwd=str(d),
                     stdout=_sp.PIPE, stderr=_sp.PIPE)
    try:
        import time as _t
        _t.sleep(1.0)
        out = await server.qt_console_messages(QtConsoleMessagesInput(
            process_id=proc.pid,
            wait_seconds=0,
            level_filter="NONEXISTENT_LEVEL_TOKEN_XYZ",
            max_messages=10,
        ))
        check("returns report header", "qt_console_messages" in out)
        check("Messages captured: 0 (filter excluded all)", "Messages captured: 0" in out)
    finally:
        proc.kill()
        try:
            proc.wait(timeout=2)
        except _sp.TimeoutExpired:
            pass


# ---------- tool count assertion ----------

async def test_tool_count():
    print("\n[26] tool count >= 100 (95 prior + 5 v0.3.4)")
    tools = await server.mcp.list_tools()
    n = len(tools)
    check(f"tool count >= 100 (actual={n})", n >= 100)


ALL_TESTS = [
    test_perf_compare_executable_not_found,
    test_perf_compare_baseline_not_found,
    test_perf_compare_baseline_missing_field,
    test_perf_compare_negative_threshold,
    test_perf_compare_happy_path_notepad,
    test_resource_validate_file_not_found,
    test_resource_validate_happy_path,
    test_resource_validate_naming_violation,
    test_resource_validate_case_collision,
    test_resource_validate_missing_on_disk,
    test_resource_validate_output_json,
    test_coverage_diff_baseline_not_found,
    test_coverage_diff_empty_info_file,
    test_coverage_diff_identical_passes,
    test_coverage_diff_regression_fails,
    test_coverage_diff_output_json,
    test_screenshot_baseline_empty_scale_factors,
    test_screenshot_baseline_negative_scale,
    test_screenshot_baseline_executable_not_found,
    test_screenshot_baseline_happy_notepad,
    test_console_messages_no_exe_no_pid,
    test_console_messages_executable_not_found,
    test_console_messages_spawn_then_attach_fails_cleanly,
    test_console_messages_invalid_pid,
    test_console_messages_level_filter_token_no_match,
    test_tool_count,
]


async def main():
    print("=" * 60)
    print("qt-mcp v0.3.4 e2e (5 new tools)")
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