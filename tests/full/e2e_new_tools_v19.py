"""e2e for v19 new tools (v0.3.3):
  - qt_widget_introspect   (pywinauto widget tree: snapshot / find / details)
  - qt_layout_check        (.ui layout anti-patterns: stretch / nesting / dupe name)
  - qt_cppcheck            (cppcheck --json wrapper)
  - qt_thread_affinity_check (QObject cross-thread signal/slot)
  - qt_sanitizer_run       (build + run with -fsanitize=address)

Run: python e2e_new_tools_v19.py
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
    QtWidgetIntrospectInput,
    QtLayoutCheckInput,
    QtCppcheckInput,
    QtThreadAffinityCheckInput,
    QtSanitizerRunInput,
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


# ---------- qt_widget_introspect ----------

async def test_widget_introspect_invalid_action():
    print("\n[1] qt_widget_introspect -- invalid action returns Error")
    out = await server.qt_widget_introspect(QtWidgetIntrospectInput(
        action="bad",
        process_id=0,
        executable=r"C:\Windows\notepad.exe",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions invalid action", "invalid action" in out.lower())


async def test_widget_introspect_no_args():
    print("\n[2] qt_widget_introspect -- process_id=0 + no executable returns Error")
    out = await server.qt_widget_introspect(QtWidgetIntrospectInput(
        action="snapshot",
        process_id=0,
        executable="",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions executable", "executable" in out.lower())


async def test_widget_introspect_details_no_auto_id():
    print("\n[3] qt_widget_introspect -- details without auto_id returns Error")
    out = await server.qt_widget_introspect(QtWidgetIntrospectInput(
        action="details",
        process_id=99999,
        auto_id="",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions auto_id", "auto_id" in out.lower())


async def test_widget_introspect_executable_not_found():
    print("\n[4] qt_widget_introspect -- nonexistent executable returns Error")
    d = fresh_dir(SANDBOX_TMP, "v19_wi_noexe")
    fake_exe = d / "no_such_app.exe"
    # Don't create it
    out = await server.qt_widget_introspect(QtWidgetIntrospectInput(
        action="snapshot",
        process_id=0,
        executable=str(fake_exe),
    ))
    check("returns Error:", "Error:" in out)
    check("mentions not found", "not found" in out.lower())


async def test_widget_introspect_sandbox_rejection():
    print("\n[5] qt_widget_introspect -- out-of-sandbox executable rejected")
    out = await server.qt_widget_introspect(QtWidgetIntrospectInput(
        action="snapshot",
        process_id=0,
        executable=r"C:\Windows\notepad.exe",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions sandbox", "sandbox" in out.lower())


# ---------- qt_layout_check ----------

async def test_layout_check_invalid_format():
    print("\n[6] qt_layout_check -- invalid output_format returns Error")
    out = await server.qt_layout_check(QtLayoutCheckInput(
        source=str(SANDBOX_TMP),
        output_format="xml",
    ))
    check("returns Error:", "Error:" in out)


async def test_layout_check_source_not_found():
    print("\n[7] qt_layout_check -- nonexistent source returns Error")
    out = await server.qt_layout_check(QtLayoutCheckInput(
        source=str(SANDBOX_TMP / "no_such_dir_xyz"),
    ))
    check("returns Error:", "Error:" in out)
    check("mentions not found", "not found" in out.lower())


async def test_layout_check_clean_ui():
    print("\n[8] qt_layout_check -- well-formed .ui reports 0 findings")
    d = fresh_dir(SANDBOX_TMP, "v19_lc_clean")
    ui = d / "clean.ui"
    ui.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<ui version="4.0">\n'
        ' <widget class="QWidget" name="Form">\n'
        '  <layout class="QVBoxLayout" name="vbox">\n'
        '   <item>\n'
        '    <widget class="QPushButton" name="btnOk">\n'
        '     <property name="text"><string>OK</string></property>\n'
        '    </widget>\n'
        '   </item>\n'
        '   <item>\n'
        '    <widget class="QPushButton" name="btnCancel">\n'
        '     <property name="text"><string>Cancel</string></property>\n'
        '    </widget>\n'
        '   </item>\n'
        '  </layout>\n'
        ' </widget>\n'
        '</ui>\n',
        encoding="utf-8",
    )
    out = await server.qt_layout_check(QtLayoutCheckInput(
        source=str(ui),
        min_severity="warning",
    ))
    check("returns ok header", "qt_layout_check" in out)
    check("Total findings: 0", "Total findings: 0" in out)


async def test_layout_check_dupe_object_names():
    print("\n[9] qt_layout_check -- duplicate objectName detected")
    d = fresh_dir(SANDBOX_TMP, "v19_lc_dupe")
    ui = d / "dupe.ui"
    ui.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<ui version="4.0">\n'
        ' <widget class="QWidget" name="Form">\n'
        '  <layout class="QVBoxLayout" name="vbox">\n'
        '   <item>\n'
        '    <widget class="QPushButton" name="btnSame">\n'
        '     <property name="text"><string>A</string></property>\n'
        '    </widget>\n'
        '   </item>\n'
        '   <item>\n'
        '    <widget class="QPushButton" name="btnSame">\n'
        '     <property name="text"><string>B</string></property>\n'
        '    </widget>\n'
        '   </item>\n'
        '  </layout>\n'
        ' </widget>\n'
        '</ui>\n',
        encoding="utf-8",
    )
    out = await server.qt_layout_check(QtLayoutCheckInput(
        source=str(ui),
        min_severity="warning",
    ))
    check("detects dupe", "duplicated_object_name" in out)
    check("mentions btnSame", "btnSame" in out)


async def test_layout_check_deep_nesting():
    print("\n[10] qt_layout_check -- deep nesting (>5) detected")
    d = fresh_dir(SANDBOX_TMP, "v19_lc_deep")
    ui = d / "deep.ui"
    # 7 levels of layout nesting
    nest = ""
    for i in range(7):
        nest += f'<layout class="QVBoxLayout" name="L{i}"><item><widget class="QWidget" name="W{i}">'
    nest += '<layout class="QVBoxLayout" name="Inner"></layout>'
    for i in range(6, -1, -1):
        nest += '</widget></item></layout>'
    ui.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<ui version="4.0">\n'
        ' <widget class="QWidget" name="Form">\n'
        f'  {nest}\n'
        ' </widget>\n'
        '</ui>\n',
        encoding="utf-8",
    )
    out = await server.qt_layout_check(QtLayoutCheckInput(
        source=str(ui),
        min_severity="warning",
    ))
    check("detects deep nesting", "deep_nesting" in out)


async def test_layout_check_widget_no_layout_parent():
    print("\n[11] qt_layout_check -- widget without layout parent detected")
    d = fresh_dir(SANDBOX_TMP, "v19_lc_nolayout")
    ui = d / "nolayout.ui"
    ui.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<ui version="4.0">\n'
        ' <widget class="QWidget" name="Form">\n'
        '  <widget class="QPushButton" name="orphan">\n'
        '   <property name="text"><string>Orphan</string></property>\n'
        '  </widget>\n'
        ' </widget>\n'
        '</ui>\n',
        encoding="utf-8",
    )
    out = await server.qt_layout_check(QtLayoutCheckInput(
        source=str(ui),
        min_severity="warning",
    ))
    check("detects widget_no_layout_parent", "widget_no_layout_parent" in out)


async def test_layout_check_no_stretch():
    print("\n[12] qt_layout_check -- layout with no stretch (info)")
    d = fresh_dir(SANDBOX_TMP, "v19_lc_nostretch")
    ui = d / "nostretch.ui"
    ui.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<ui version="4.0">\n'
        ' <widget class="QWidget" name="Form">\n'
        '  <layout class="QHBoxLayout" name="hbox">\n'
        '   <item><widget class="QPushButton" name="btnA"><property name="text"><string>A</string></property></widget></item>\n'
        '   <item><widget class="QPushButton" name="btnB"><property name="text"><string>B</string></property></widget></item>\n'
        '   <item><widget class="QPushButton" name="btnC"><property name="text"><string>C</string></property></widget></item>\n'
        '  </layout>\n'
        ' </widget>\n'
        '</ui>\n',
        encoding="utf-8",
    )
    out = await server.qt_layout_check(QtLayoutCheckInput(
        source=str(ui),
        min_severity="info",
    ))
    check("detects layout_no_stretch", "layout_no_stretch" in out)


async def test_layout_check_json_output():
    print("\n[13] qt_layout_check -- json output is valid JSON")
    d = fresh_dir(SANDBOX_TMP, "v19_lc_json")
    ui = d / "x.ui"
    ui.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<ui version="4.0"><widget class="QWidget" name="F"></widget></ui>\n',
        encoding="utf-8",
    )
    out = await server.qt_layout_check(QtLayoutCheckInput(
        source=str(ui),
        output_format="json",
    ))
    check("output is JSON", '"summary"' in out and '"files_scanned"' in out)


async def test_layout_check_severity_filter():
    print("\n[14] qt_layout_check -- severity filter excludes info")
    d = fresh_dir(SANDBOX_TMP, "v19_lc_sev")
    ui = d / "sev.ui"
    ui.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<ui version="4.0">\n'
        ' <widget class="QWidget" name="Form">\n'
        '  <layout class="QHBoxLayout" name="hbox">\n'
        '   <item><widget class="QPushButton" name="a"><property name="text"><string>A</string></property></widget></item>\n'
        '   <item><widget class="QPushButton" name="b"><property name="text"><string>B</string></property></widget></item>\n'
        '  </layout>\n'
        ' </widget>\n'
        '</ui>\n',
        encoding="utf-8",
    )
    out_warn = await server.qt_layout_check(QtLayoutCheckInput(
        source=str(ui), min_severity="warning",
    ))
    check("warning-only excludes layout_no_stretch", "layout_no_stretch" not in out_warn)


# ---------- qt_cppcheck ----------

_FAKE_CPPCHECK_PY = '''#!/usr/bin/env python3
"""Fake cppcheck stub for e2e_v19. Reads --json from argv and emits one or
more JSON diagnostic objects to stdout.

Heuristic: the LAST positional that ends in .cpp/.h/.cxx is the target.
Its basename controls behavior:
  - contains "clean" -> emit {"diagnostics": []} (zero findings, valid JSON)
  - contains "dirty" -> emit 3 diagnostics (warning + style + performance)
  - otherwise -> emit 1 warning diagnostic
"""
import json
import os
import sys

target = None
for a in sys.argv[1:]:
    if not a.startswith("-") and (a.endswith(".cpp") or a.endswith(".h") or a.endswith(".cxx")):
        target = a

if target is None or not os.path.exists(target):
    print(json.dumps({"diagnostics": []}))
    sys.exit(0)

base = os.path.splitext(os.path.basename(target))[0]
if "clean" in base:
    print(json.dumps({"diagnostics": []}))
    sys.exit(0)
elif "dirty" in base:
    diags = [
        {"file": target, "line": 10, "severity": "warning", "id": "uninitvar",
         "message": "Variable 'x' is not initialized."},
        {"file": target, "line": 25, "severity": "style", "id": "unusedVariable",
         "message": "Unused variable: y"},
        {"file": target, "line": 40, "severity": "performance", "id": "passByValue",
         "message": "Function parameter 'z' should be passed by const reference."},
    ]
else:
    diags = [
        {"file": target, "line": 5, "severity": "warning", "id": "nullPointer",
         "message": "Possible null pointer dereference."},
    ]
print(json.dumps({"diagnostics": diags}))
sys.exit(0)
'''


def _write_fake_cppcheck_stub(stub_dir: Path) -> Path:
    script = stub_dir / "_cppcheck_stub.py"
    script.write_text(_FAKE_CPPCHECK_PY, encoding="utf-8")
    wrapper = stub_dir / "cppcheck_stub.cmd"
    wrapper.write_text(
        '@echo off\r\npython "%~dp0\\_cppcheck_stub.py" %*\r\n',
        encoding="utf-8",
    )
    return wrapper


async def test_cppcheck_invalid_format():
    print("\n[15] qt_cppcheck -- invalid output_format returns Error")
    out = await server.qt_cppcheck(QtCppcheckInput(
        source_dir=str(SANDBOX_TMP),
        output_format="xml",
    ))
    check("returns Error:", "Error:" in out)


async def test_cppcheck_source_not_found():
    print("\n[16] qt_cppcheck -- nonexistent source_dir returns Error")
    out = await server.qt_cppcheck(QtCppcheckInput(
        source_dir=str(SANDBOX_TMP / "no_such_dir_zzz"),
    ))
    check("returns Error:", "Error:" in out)
    check("mentions not found", "not found" in out.lower())


async def test_cppcheck_explicit_exe_not_found():
    print("\n[17] qt_cppcheck -- explicit cppcheck_exe not on disk returns Error")
    out = await server.qt_cppcheck(QtCppcheckInput(
        source_dir=str(SANDBOX_TMP),
        cppcheck_exe=str(SANDBOX_TMP / "no_such_cppcheck.exe"),
    ))
    check("returns Error:", "Error:" in out)
    check("mentions not found", "not found" in out.lower() or "cppcheck not found" in out.lower())


async def test_cppcheck_with_fake_stub_clean_source():
    print("\n[18] qt_cppcheck -- fake stub on 'clean' source: 0 findings")
    d = fresh_dir(SANDBOX_TMP, "v19_cc_clean")
    cpp = d / "clean.cpp"
    cpp.write_text("int main() { return 0; }\n", encoding="utf-8")
    stub_dir = d / "stub"
    stub_dir.mkdir()
    exe = _write_fake_cppcheck_stub(stub_dir)
    out = await server.qt_cppcheck(QtCppcheckInput(
        source_dir=str(cpp),
        cppcheck_exe=str(exe),
    ))
    check("header present", "qt_cppcheck" in out)
    check("Total findings: 0", "Total findings: 0" in out)


async def test_cppcheck_with_fake_stub_dirty_source():
    print("\n[19] qt_cppcheck -- fake stub on 'dirty' source: 3 findings aggregated")
    d = fresh_dir(SANDBOX_TMP, "v19_cc_dirty")
    cpp = d / "dirty.cpp"
    cpp.write_text("int main() { int x; int y; return x + y; }\n", encoding="utf-8")
    stub_dir = d / "stub"
    stub_dir.mkdir()
    exe = _write_fake_cppcheck_stub(stub_dir)
    out = await server.qt_cppcheck(QtCppcheckInput(
        source_dir=str(cpp),
        cppcheck_exe=str(exe),
    ))
    check("Total findings: 3", "Total findings: 3" in out)
    check("warning count = 1", "'warning': 1" in out)
    check("style count = 1", "'style': 1" in out)
    check("performance count = 1", "'performance': 1" in out)


async def test_cppcheck_severity_filter():
    print("\n[20] qt_cppcheck -- severity_filter keeps only matching severities")
    d = fresh_dir(SANDBOX_TMP, "v19_cc_sev")
    cpp = d / "dirty.cpp"
    cpp.write_text("int main() { return 0; }\n", encoding="utf-8")
    stub_dir = d / "stub"
    stub_dir.mkdir()
    exe = _write_fake_cppcheck_stub(stub_dir)
    out = await server.qt_cppcheck(QtCppcheckInput(
        source_dir=str(cpp),
        cppcheck_exe=str(exe),
        severity_filter="warning",
    ))
    # dirty stub emits 1 warning + 1 style + 1 performance; filter=warning keeps only 1
    check("filtered total = 1", "Total findings: 1" in out)


async def test_cppcheck_json_output():
    print("\n[21] qt_cppcheck -- JSON output is well-formed")
    d = fresh_dir(SANDBOX_TMP, "v19_cc_json")
    cpp = d / "default.cpp"
    cpp.write_text("int main() { return 0; }\n", encoding="utf-8")
    stub_dir = d / "stub"
    stub_dir.mkdir()
    exe = _write_fake_cppcheck_stub(stub_dir)
    out = await server.qt_cppcheck(QtCppcheckInput(
        source_dir=str(cpp),
        cppcheck_exe=str(exe),
        output_format="json",
    ))
    check("output starts with brace", out.lstrip().startswith("{"))
    check("contains summary", '"summary"' in out)
    check("contains findings array", '"findings"' in out)


# ---------- qt_thread_affinity_check ----------

async def test_thread_affinity_no_files():
    print("\n[22] qt_thread_affinity_check -- empty source_files returns Error")
    out = await server.qt_thread_affinity_check(QtThreadAffinityCheckInput(
        source_files=[],
    ))
    check("returns Error:", "Error:" in out)


async def test_thread_affinity_invalid_format():
    print("\n[23] qt_thread_affinity_check -- invalid format returns Error")
    out = await server.qt_thread_affinity_check(QtThreadAffinityCheckInput(
        source_files=[str(SANDBOX_TMP / "x.cpp")],
        output_format="xml",
    ))
    check("returns Error:", "Error:" in out)


async def test_thread_affinity_file_not_found():
    print("\n[24] qt_thread_affinity_check -- missing file returns Error")
    out = await server.qt_thread_affinity_check(QtThreadAffinityCheckInput(
        source_files=[str(SANDBOX_TMP / "no_such_file.cpp")],
    ))
    check("returns Error:", "Error:" in out)
    check("mentions not found", "not found" in out.lower())


async def test_thread_affinity_clean_cpp():
    print("\n[25] qt_thread_affinity_check -- clean .cpp reports 0 findings")
    d = fresh_dir(SANDBOX_TMP, "v19_ta_clean")
    cpp = d / "worker.cpp"
    cpp.write_text(
        '// clean file, no thread primitives\n'
        'int add(int a, int b) { return a + b; }\n',
        encoding="utf-8",
    )
    out = await server.qt_thread_affinity_check(QtThreadAffinityCheckInput(
        source_files=[str(cpp)],
        min_severity="warning",
    ))
    check("Total findings: 0", "Total findings: 0" in out)


async def test_thread_affinity_direct_connection_cross_thread():
    print("\n[26] qt_thread_affinity_check -- Qt::DirectConnection + moveToThread detected")
    d = fresh_dir(SANDBOX_TMP, "v19_ta_direct")
    cpp = d / "cross.cpp"
    cpp.write_text(
        '#include <QObject>\n'
        'class A : public QObject {\n'
        '  Q_OBJECT\n'
        'public slots:\n'
        '  void work() { /* do stuff */ }\n'
        '};\n'
        'void setup(A* a, A* b) {\n'
        '  a->moveToThread(nullptr);\n'
        '  QObject::connect(a, SIGNAL(foo()), b, SLOT(work()), Qt::DirectConnection);\n'
        '}\n',
        encoding="utf-8",
    )
    out = await server.qt_thread_affinity_check(QtThreadAffinityCheckInput(
        source_files=[str(cpp)],
        min_severity="warning",
    ))
    check("detects direct_connection_cross_thread", "direct_connection_cross_thread" in out)


async def test_thread_affinity_qthread_no_exec():
    print("\n[27] qt_thread_affinity_check -- QThread subclass without exec detected")
    d = fresh_dir(SANDBOX_TMP, "v19_ta_qthread")
    cpp = d / "badthread.cpp"
    cpp.write_text(
        '#include <QThread>\n'
        'class MyThread : public QThread {\n'
        'public:\n'
        '  void run() override { /* no exec() */ }\n'
        '};\n',
        encoding="utf-8",
    )
    out = await server.qt_thread_affinity_check(QtThreadAffinityCheckInput(
        source_files=[str(cpp)],
        min_severity="warning",
    ))
    check("detects qthread_run_without_exec", "qthread_run_without_exec" in out)


async def test_thread_affinity_qthread_with_exec_is_clean():
    print("\n[28] qt_thread_affinity_check -- QThread subclass WITH exec() is clean")
    d = fresh_dir(SANDBOX_TMP, "v19_ta_qthreadok")
    cpp = d / "goodthread.cpp"
    cpp.write_text(
        '#include <QThread>\n'
        'class MyThread : public QThread {\n'
        'public:\n'
        '  void run() override { exec(); }\n'
        '};\n',
        encoding="utf-8",
    )
    out = await server.qt_thread_affinity_check(QtThreadAffinityCheckInput(
        source_files=[str(cpp)],
        min_severity="warning",
    ))
    check("Total findings: 0", "Total findings: 0" in out)


async def test_thread_affinity_json_output():
    print("\n[29] qt_thread_affinity_check -- json output valid")
    d = fresh_dir(SANDBOX_TMP, "v19_ta_json")
    cpp = d / "x.cpp"
    cpp.write_text("int main() { return 0; }\n", encoding="utf-8")
    out = await server.qt_thread_affinity_check(QtThreadAffinityCheckInput(
        source_files=[str(cpp)],
        output_format="json",
    ))
    check("contains summary", '"summary"' in out)
    check("contains findings", '"findings"' in out)


# ---------- qt_sanitizer_run ----------

async def test_sanitizer_run_invalid_type():
    print("\n[30] qt_sanitizer_run -- invalid sanitizer_type returns Error")
    d = fresh_dir(SANDBOX_TMP, "v19_sr_invtype")
    (d / "x.pro").write_text("QT += widgets\nSOURCES = main.cpp\n", encoding="utf-8")
    out = await server.qt_sanitizer_run(QtSanitizerRunInput(
        project_dir=str(d),
        sanitizer_type="bogus",
    ))
    check("returns Error:", "Error:" in out)


async def test_sanitizer_run_invalid_build_type():
    print("\n[31] qt_sanitizer_run -- invalid build_type returns Error")
    d = fresh_dir(SANDBOX_TMP, "v19_sr_invbuild")
    (d / "x.pro").write_text("QT += widgets\nSOURCES = main.cpp\n", encoding="utf-8")
    out = await server.qt_sanitizer_run(QtSanitizerRunInput(
        project_dir=str(d),
        sanitizer_type="address",
        build_type="nonsense",
    ))
    check("returns Error:", "Error:" in out)


async def test_sanitizer_run_no_pro_file():
    print("\n[32] qt_sanitizer_run -- missing .pro returns Error")
    d = fresh_dir(SANDBOX_TMP, "v19_sr_nopro")
    out = await server.qt_sanitizer_run(QtSanitizerRunInput(
        project_dir=str(d),
    ))
    check("returns Error:", "Error:" in out)
    check("mentions .pro", ".pro" in out)


async def test_sanitizer_run_project_dir_not_found():
    print("\n[33] qt_sanitizer_run -- nonexistent project_dir returns Error")
    out = await server.qt_sanitizer_run(QtSanitizerRunInput(
        project_dir=str(SANDBOX_TMP / "no_such_proj_zzz"),
    ))
    check("returns Error:", "Error:" in out)


async def test_sanitizer_run_sandbox_rejection():
    print("\n[34] qt_sanitizer_run -- out-of-sandbox project_dir rejected")
    out = await server.qt_sanitizer_run(QtSanitizerRunInput(
        project_dir=r"C:\Windows",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions sandbox", "sandbox" in out.lower())


async def test_sanitizer_run_patches_pro_with_flag():
    """Validate that .pro gets patched with the flag (without actually running build)."""
    print("\n[35] qt_sanitizer_run -- patches .pro with -fsanitize=address (build-only)")
    d = fresh_dir(SANDBOX_TMP, "v19_sr_patch")
    pro = d / "myapp.pro"
    pro.write_text(
        "QT += widgets\n"
        "SOURCES = main.cpp\n"
        "TARGET = myapp\n",
        encoding="utf-8",
    )
    cpp = d / "main.cpp"
    cpp.write_text(
        '#include <QApplication>\nint main(int argc, char** argv) { QApplication app(argc, argv); return 0; }\n',
        encoding="utf-8",
    )
    # build_type=debug + run_seconds=0 + set timeout_seconds very short so
    # qmake fails fast (it will be missing in fresh_dir env). The point is
    # that the sanitizer build directory is created and the .pro gets patched
    # BEFORE the build tool fails — the patch artifact is what we verify.
    out = await server.qt_sanitizer_run(QtSanitizerRunInput(
        project_dir=str(d),
        sanitizer_type="address",
        build_type="debug",
        run_seconds=0,
        timeout_seconds=5,
        keep_sanitizer_build=True,
    ))
    san_dir = d / "sanitizer-address-debug"
    check("sanitizer build dir exists", san_dir.exists())
    if san_dir.exists():
        san_pro = san_dir / "myapp.pro"
        check("patched .pro exists", san_pro.exists())
        if san_pro.exists():
            content = san_pro.read_text(encoding="utf-8")
            check("contains -fsanitize=address", "-fsanitize=address" in content)
            check("contains QMAKE_LFLAGS", "QMAKE_LFLAGS" in content)
            check("contains qt_sanitizer_run marker", "qt_sanitizer_run" in content)


# ---------- meta ----------

async def test_tool_count():
    print("\n[36] tool count == 95 (90 prior + 5 v0.3.3)")
    tools = await server.mcp.list_tools()
    n = len(tools)
    expected = 95
    check(f"tool count >= {expected} (actual={n})", n >= expected)


ALL_TESTS = [
    test_widget_introspect_invalid_action,
    test_widget_introspect_no_args,
    test_widget_introspect_details_no_auto_id,
    test_widget_introspect_executable_not_found,
    test_widget_introspect_sandbox_rejection,
    test_layout_check_invalid_format,
    test_layout_check_source_not_found,
    test_layout_check_clean_ui,
    test_layout_check_dupe_object_names,
    test_layout_check_deep_nesting,
    test_layout_check_widget_no_layout_parent,
    test_layout_check_no_stretch,
    test_layout_check_json_output,
    test_layout_check_severity_filter,
    test_cppcheck_invalid_format,
    test_cppcheck_source_not_found,
    test_cppcheck_explicit_exe_not_found,
    test_cppcheck_with_fake_stub_clean_source,
    test_cppcheck_with_fake_stub_dirty_source,
    test_cppcheck_severity_filter,
    test_cppcheck_json_output,
    test_thread_affinity_no_files,
    test_thread_affinity_invalid_format,
    test_thread_affinity_file_not_found,
    test_thread_affinity_clean_cpp,
    test_thread_affinity_direct_connection_cross_thread,
    test_thread_affinity_qthread_no_exec,
    test_thread_affinity_qthread_with_exec_is_clean,
    test_thread_affinity_json_output,
    test_sanitizer_run_invalid_type,
    test_sanitizer_run_invalid_build_type,
    test_sanitizer_run_no_pro_file,
    test_sanitizer_run_project_dir_not_found,
    test_sanitizer_run_sandbox_rejection,
    test_sanitizer_run_patches_pro_with_flag,
    test_tool_count,
]


async def main():
    print("=" * 60)
    print("qt-mcp v0.3.3 e2e (5 new tools)")
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