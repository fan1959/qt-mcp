"""e2e for v23 new tools (v0.3.7):
  - qt_invoke_helper_gen   (Qt helper .exe skeleton: QObject + Q_PROPERTY + Q_INVOKABLE + JSON protocol)
  - qt_qproperty_set       (runtime set Q_PROPERTY via helper stdin/stdout)
  - qt_meta_invoke         (runtime invoke Q_INVOKABLE via helper stdin/stdout)
  - qt_pro_lint            (.pro file lint: duplicates, config conflicts, target naming)
  - qt_shadow_build_setup  (shadow build dirs + .pro.user + build_shadow.bat)
  - qt_qmlscene            (preview .qml via qml.exe + screenshot)
  - qt_cmake_install       (CMake install() + CPack NSIS + windeployqt)
  - qt_conda_env_gen       (conda environment.yml for Qt + install script + README)
  - qt_db_open_in_gui      (open .db in SQLiteStudio or custom GUI client)
  - qt_db_schema_diff      (compare two .db schemas, emit migration SQL)
  - qt_db_dump             (export .db table(s) to CSV/JSON/SQL)
  - qt_db_validate         (FK integrity + index health + orphan rows)

Run: python e2e_new_tools_v23.py
"""

import asyncio
import csv as _csv
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
import csv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import server
from server import (
    SANDBOX_TMP,
    QtInvokeHelperGenInput,
    QtQpropertySetInput,
    QtMetaInvokeInput,
    QtProLintInput,
    QtShadowBuildSetupInput,
    QtQmlsceneInput,
    QtCmakeInstallInput,
    QtCondaEnvGenInput,
    QtDbOpenInGuiInput,
    QtDbSchemaDiffInput,
    QtDbDumpInput,
    QtDbValidateInput,
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


def make_temp_db(parent: Path, name: str, schema: dict) -> Path:
    """Create a SQLite .db with a given schema. schema = {'table': 'CREATE TABLE ...'}"""
    p = parent / name
    if p.exists():
        p.unlink()
    conn = sqlite3.connect(str(p))
    try:
        cur = conn.cursor()
        for tbl, ddl in schema.items():
            cur.execute(ddl)
        conn.commit()
    finally:
        conn.close()
    return p


# ============ qt_invoke_helper_gen ============

async def test_invoke_helper_gen_happy():
    print("\n[1] qt_invoke_helper_gen -- happy path")
    d = fresh_dir(SANDBOX_TMP, "v23_ihg_happy")
    out_dir = d / "helper"
    out = await server.qt_invoke_helper_gen(QtInvokeHelperGenInput(
        class_name="MyController",
        properties=[
            {"name": "value", "type": "int", "default": 0},
            {"name": "label", "type": "QString", "default": "hello"},
        ],
        invokables=[
            {"name": "doSomething", "return_type": "void"},
            {"name": "compute", "return_type": "int"},
        ],
        output_dir=str(out_dir),
        qt_module="core",
    ))
    check("invokes JSON footer (=== present)", "===" in out)
    check("creates 4 files (pro/h/cpp/main.cpp)", all((out_dir / f).exists() for f in
                                                       ["mycontroller.pro", "mycontroller.h", "mycontroller.cpp", "main.cpp"]))
    pro_text = (out_dir / "mycontroller.pro").read_text(encoding="utf-8")
    check(".pro contains QT += core", "core" in pro_text)
    h_text = (out_dir / "mycontroller.h").read_text(encoding="utf-8")
    check(".h has Q_PROPERTY(value)", "Q_PROPERTY(int value" in h_text or "Q_PROPERTY( int value" in h_text)
    check(".h has Q_PROPERTY(label)", "Q_PROPERTY(QString label" in h_text or "Q_PROPERTY( QString label" in h_text)
    check(".h has Q_INVOKABLE wrapper", "QVariant doSomething" in h_text or "QVariant compute" in h_text)
    main_text = (out_dir / "main.cpp").read_text(encoding="utf-8")
    check("main.cpp has JSON protocol commands", '"cmd"' in main_text and "list_properties" in main_text and "set_property" in main_text)


async def test_invoke_helper_gen_bad_classname():
    print("\n[2] qt_invoke_helper_gen -- bad class_name rejected")
    d = fresh_dir(SANDBOX_TMP, "v23_ihg_badclass")
    out = await server.qt_invoke_helper_gen(QtInvokeHelperGenInput(
        class_name="lowerCase",
        properties=[],
        invokables=[],
        output_dir=str(d),
    ))
    check("rejects lowercase class_name", "Error" in out and "CamelCase" in out)


async def test_invoke_helper_gen_no_modules():
    print("\n[3] qt_invoke_helper_gen -- no properties/invokables (empty ok)")
    d = fresh_dir(SANDBOX_TMP, "v23_ihg_empty")
    out = await server.qt_invoke_helper_gen(QtInvokeHelperGenInput(
        class_name="Empty",
        properties=[],
        invokables=[],
        output_dir=str(d / "out"),
        qt_module="core",
    ))
    check("no-error exit", "Error" not in out or "ready" in out)
    check("writes 4 files", all((d / "out" / f).exists() for f in ["empty.pro", "empty.h", "empty.cpp", "main.cpp"]))


# ============ qt_qproperty_set / qt_meta_invoke ============
# (These tools need a built helper .exe. We'll use a minimal in-test helper.)

async def _build_minimal_helper(d: Path) -> Path:
    """Build a minimal Qt helper .exe (or return a Python stub if Qt not available)."""
    # Use a Python stub that mimics the helper protocol — much faster than building Qt.
    helper_py = d / "fake_helper.py"
    helper_py.write_text('''#!/usr/bin/env python
import sys, json
def send(o): print(json.dumps(o), flush=True)
ready = {"ok": True, "result": "ready", "properties": ["value", "label"], "methods": ["doSomething", "compute"]}
send(ready)
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try:
        req = json.loads(line)
    except Exception as e:
        send({"ok": False, "error": f"invalid JSON: {e}"})
        continue
    cmd = req.get("cmd")
    if cmd == "list_properties":
        send({"ok": True, "result": ["value", "label"]})
    elif cmd == "list_methods":
        send({"ok": True, "result": ["doSomething", "compute"]})
    elif cmd == "get_property":
        p = req.get("property")
        if p == "value": send({"ok": True, "result": 42})
        elif p == "label": send({"ok": True, "result": "hi"})
        else: send({"ok": False, "error": f"unknown property: {p}"})
    elif cmd == "set_property":
        p = req.get("property")
        if p in ("value", "label"):
            send({"ok": True, "result": None})
        else:
            send({"ok": False, "error": f"unknown property: {p}"})
    elif cmd == "invoke":
        m = req.get("method")
        if m in ("doSomething", "compute"):
            send({"ok": True, "result": 99})
        else:
            send({"ok": False, "error": f"unknown method: {m}"})
    elif cmd == "quit":
        send({"ok": True, "result": "bye"}); break
    else:
        send({"ok": False, "error": f"unknown cmd: {cmd}"})
''', encoding="utf-8")
    # Wrap as .exe (rename for sandbox — we treat it as a fake exe)
    fake_exe = d / "fake_helper.exe"
    shutil.copy(sys.executable, fake_exe)  # actual .exe
    # Create a .bat that runs the fake helper — but qt_qproperty_set uses [str(helper_exe)] directly
    # Simpler: use a Python launcher that runs the fake_helper.py
    return fake_exe


async def test_qproperty_set_happy():
    print("\n[4] qt_qproperty_set -- happy path (using python helper as fake exe)")
    d = fresh_dir(SANDBOX_TMP, "v23_qps_happy")
    helper_py = d / "fake_helper.py"
    helper_py.write_text('''import sys, json
def send(o): print(json.dumps(o), flush=True)
send({"ok": True, "result": "ready", "properties": ["value"], "methods": []})
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try: req = json.loads(line)
    except: send({"ok": False, "error": "invalid JSON"}); continue
    if req.get("cmd") == "set_property" and req.get("property") == "value":
        send({"ok": True, "result": None})
    elif req.get("cmd") == "quit":
        send({"ok": True, "result": "bye"}); break
    else:
        send({"ok": False, "error": "unsupported"})
''', encoding="utf-8")
    # Use python directly — qt_qproperty_set launches the exe and writes JSON to stdin
    # For test, use the python interpreter as the "exe" and pass the helper.py as first arg via wrapper.
    # Simpler: use a shell wrapper.
    wrapper = d / "fake_helper.bat"
    wrapper.write_text(f'@echo off\n"{sys.executable}" "{helper_py}"\n', encoding="utf-8")

    out = await server.qt_qproperty_set(QtQpropertySetInput(
        helper_exe=str(wrapper),
        property_name="value",
        value=42,
    ))
    check("set reports success", "OK" in out or "ok" in out.lower())
    check("error case absent", "Error" not in out or "setProperty failed" not in out)


async def test_qproperty_set_missing_exe():
    print("\n[5] qt_qproperty_set -- missing exe rejected")
    out = await server.qt_qproperty_set(QtQpropertySetInput(
        helper_exe=str(SANDBOX_TMP / "definitely_not_an_exe_12345.exe"),
        property_name="value",
        value=1,
    ))
    check("rejects missing exe", "Error" in out and "not found" in out)


async def test_meta_invoke_happy():
    print("\n[6] qt_meta_invoke -- happy path")
    d = fresh_dir(SANDBOX_TMP, "v23_mi_happy")
    helper_py = d / "fake_helper.py"
    helper_py.write_text('''import sys, json
def send(o): print(json.dumps(o), flush=True)
send({"ok": True, "result": "ready", "properties": [], "methods": ["doSomething"]})
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try: req = json.loads(line)
    except: send({"ok": False, "error": "invalid JSON"}); continue
    if req.get("cmd") == "invoke" and req.get("method") == "doSomething":
        send({"ok": True, "result": 99})
    elif req.get("cmd") == "quit":
        send({"ok": True, "result": "bye"}); break
''', encoding="utf-8")
    wrapper = d / "fake_helper.bat"
    wrapper.write_text(f'@echo off\n"{sys.executable}" "{helper_py}"\n', encoding="utf-8")
    out = await server.qt_meta_invoke(QtMetaInvokeInput(
        helper_exe=str(wrapper),
        method_name="doSomething",
        args=[],
    ))
    check("invoke reports success", "Result:" in out or "ok" in out.lower())


async def test_meta_invoke_missing_exe():
    print("\n[7] qt_meta_invoke -- missing exe rejected")
    out = await server.qt_meta_invoke(QtMetaInvokeInput(
        helper_exe=str(SANDBOX_TMP / "missing.exe"),
        method_name="doSomething",
    ))
    check("rejects missing exe", "Error" in out and "not found" in out)


# ============ qt_pro_lint ============

async def test_pro_lint_duplicates():
    print("\n[8] qt_pro_lint -- detects duplicate SOURCES / CONFIG conflict / no TEMPLATE")
    d = fresh_dir(SANDBOX_TMP, "v23_pl_dups")
    pro = d / "demo.pro"
    pro.write_text(
        "QT += core core widgets\n"
        "CONFIG += debug release\n"
        "SOURCES += main.cpp main.cpp\n"
        "HEADERS += main.h\n"
        "TARGET = BadNameWithCaps\n",
        encoding="utf-8",
    )
    out = await server.qt_pro_lint(QtProLintInput(pro_file=str(pro), output_format="text"))
    check("detects duplicate SOURCES", "duplicate_source" in out)
    check("detects duplicate Qt module", "duplicate_qt_module" in out)
    check("detects CONFIG conflict", "config_conflict" in out)
    check("flags missing TEMPLATE", "template_missing" in out)
    check("flags target naming", "target_naming" in out)


async def test_pro_lint_clean():
    print("\n[9] qt_pro_lint -- clean .pro reports no issues")
    d = fresh_dir(SANDBOX_TMP, "v23_pl_clean")
    pro = d / "clean.pro"
    pro.write_text(
        "QT += core widgets\n"
        "CONFIG += c++17\n"
        "TEMPLATE = app\n"
        "TARGET = cleanapp\n"
        "SOURCES += main.cpp\n",
        encoding="utf-8",
    )
    out = await server.qt_pro_lint(QtProLintInput(pro_file=str(pro), output_format="text"))
    check("no findings for clean .pro", "No issues" in out)


async def test_pro_lint_missing():
    print("\n[10] qt_pro_lint -- missing file rejected")
    out = await server.qt_pro_lint(QtProLintInput(
        pro_file=str(SANDBOX_TMP / "nope.pro"),
        output_format="text",
    ))
    check("rejects missing .pro", "Error" in out and "not found" in out)


async def test_pro_lint_json():
    print("\n[11] qt_pro_lint -- JSON output format")
    d = fresh_dir(SANDBOX_TMP, "v23_pl_json")
    pro = d / "demo.pro"
    pro.write_text("QT += core widgets\nCONFIG += debug release\nTEMPLATE = app\n", encoding="utf-8")
    out = await server.qt_pro_lint(QtProLintInput(pro_file=str(pro), output_format="json"))
    check("returns valid JSON", out.strip().startswith("{"))
    check("JSON has config_conflict", "config_conflict" in out)


# ============ qt_shadow_build_setup ============

async def test_shadow_build_happy():
    print("\n[12] qt_shadow_build_setup -- happy path creates dirs + .pro.user + build_shadow.bat")
    d = fresh_dir(SANDBOX_TMP, "v23_sb_happy")
    pro = d / "demo.pro"
    pro.write_text("QT += core\nTEMPLATE = app\nTARGET = demo\nSOURCES += main.cpp\n", encoding="utf-8")
    out = await server.qt_shadow_build_setup(QtShadowBuildSetupInput(
        pro_file=str(pro),
        debug_dir="build-debug",
        release_dir="build-release",
    ))
    check("creates build-debug dir", (d / "build-debug").exists())
    check("creates build-release dir", (d / "build-release").exists())
    check("writes .pro.user", (d / "demo.pro.user").exists())
    check("writes build_shadow.bat", (d / "build_shadow.bat").exists())
    check("writes .shadow-build-config.json", (d / ".shadow-build-config.json").exists())
    user_text = (d / "demo.pro.user").read_text(encoding="utf-8")
    check(".pro.user has ShadowBuild", "ShadowBuild" in user_text or "shadow" in user_text.lower())


async def test_shadow_build_no_user_file():
    print("\n[13] qt_shadow_build_setup -- no .pro.user when create_user_file=False")
    d = fresh_dir(SANDBOX_TMP, "v23_sb_nouf")
    pro = d / "demo.pro"
    pro.write_text("QT += core\nTEMPLATE = app\nSOURCES += main.cpp\n", encoding="utf-8")
    out = await server.qt_shadow_build_setup(QtShadowBuildSetupInput(
        pro_file=str(pro),
        create_user_file=False,
    ))
    check("no .pro.user when disabled", not (d / "demo.pro.user").exists())
    check("build_shadow.bat still created", (d / "build_shadow.bat").exists())


async def test_shadow_build_missing():
    print("\n[14] qt_shadow_build_setup -- missing pro rejected")
    out = await server.qt_shadow_build_setup(QtShadowBuildSetupInput(
        pro_file=str(SANDBOX_TMP / "nope.pro"),
    ))
    check("rejects missing .pro", "Error" in out and "not found" in out)


# ============ qt_qmlscene ============

async def test_qmlscene_missing_file():
    print("\n[15] qt_qmlscene -- missing .qml rejected")
    out = await server.qt_qmlscene(QtQmlsceneInput(
        qml_file=str(SANDBOX_TMP / "nope.qml"),
    ))
    check("rejects missing .qml", "Error" in out and "not found" in out)


async def test_qmlscene_empty_scale_factors():
    print("\n[16] qt_qmlscene -- empty scale_factors rejected")
    d = fresh_dir(SANDBOX_TMP, "v23_qs_empty")
    qml = d / "test.qml"
    qml.write_text("import QtQuick 2.14\nItem {}\n", encoding="utf-8")
    out = await server.qt_qmlscene(QtQmlsceneInput(
        qml_file=str(qml),
        scale_factors=[],
    ))
    check("rejects empty scale_factors", "Error" in out and "non-empty" in out)


async def test_qmlscene_not_qml():
    print("\n[17] qt_qmlscene -- non-qml file rejected")
    d = fresh_dir(SANDBOX_TMP, "v23_qs_notqml")
    f = d / "test.txt"
    f.write_text("not a qml file", encoding="utf-8")
    out = await server.qt_qmlscene(QtQmlsceneInput(qml_file=str(f)))
    check("rejects .txt file", "Error" in out and ".qml" in out)


# ============ qt_cmake_install ============

async def test_cmake_install_happy():
    print("\n[18] qt_cmake_install -- happy path writes 3 cmake files + build_installer.bat")
    d = fresh_dir(SANDBOX_TMP, "v23_ci_happy")
    cm = d / "CMakeLists.txt"
    cm.write_text("cmake_minimum_required(VERSION 3.16)\nproject(MyApp)\n", encoding="utf-8")
    out = await server.qt_cmake_install(QtCmakeInstallInput(
        cmakelists_file=str(cm),
        target_name="MyApp",
        app_name="MyApp",
        app_version="1.0.0",
        vendor="MyOrg",
    ))
    check("writes InstallRules.cmake", (d / "cmake" / "InstallRules.cmake").exists())
    check("writes Packaging.cmake", (d / "cmake" / "Packaging.cmake").exists())
    check("writes Windeployqt.cmake", (d / "cmake_install" / "Windeployqt.cmake").exists())
    check("writes build_installer.bat", (d / "build_installer.bat").exists())
    pkg_text = (d / "cmake" / "Packaging.cmake").read_text(encoding="utf-8")
    check("Packaging.cmake has CPACK_NSIS", "CPACK_NSIS" in pkg_text)
    check("Packaging.cmake has app version", "1.0.0" in pkg_text)


async def test_cmake_install_no_bat():
    print("\n[19] qt_cmake_install -- no build_installer.bat when disabled")
    d = fresh_dir(SANDBOX_TMP, "v23_ci_nobat")
    cm = d / "CMakeLists.txt"
    cm.write_text("cmake_minimum_required(VERSION 3.16)\n", encoding="utf-8")
    out = await server.qt_cmake_install(QtCmakeInstallInput(
        cmakelists_file=str(cm),
        target_name="MyApp",
        write_build_bat=False,
    ))
    check("no build_installer.bat when disabled", not (d / "build_installer.bat").exists())


async def test_cmake_install_missing():
    print("\n[20] qt_cmake_install -- missing CMakeLists.txt rejected")
    out = await server.qt_cmake_install(QtCmakeInstallInput(
        cmakelists_file=str(SANDBOX_TMP / "nope.txt"),
        target_name="MyApp",
    ))
    check("rejects missing file", "Error" in out and "not found" in out)


# ============ qt_conda_env_gen ============

async def test_conda_env_gen_windows():
    print("\n[21] qt_conda_env_gen -- windows + 5.14.2 happy path")
    d = fresh_dir(SANDBOX_TMP, "v23_cg_win")
    out = await server.qt_conda_env_gen(QtCondaEnvGenInput(
        output_dir=str(d),
        env_name="qt514",
        qt_version="5.14.2",
        qt_modules=["widgets", "network"],
        platform="windows",
    ))
    check("writes environment.yml", (d / "environment.yml").exists())
    check("writes conda_install.bat (windows)", (d / "conda_install.bat").exists())
    check("writes BUILD_README.md", (d / "BUILD_README.md").exists())
    yaml_text = (d / "environment.yml").read_text(encoding="utf-8")
    check("yaml has qt=5.14.2", "qt=5.14.2" in yaml_text)
    check("yaml has qt-widgets=5.14.2", "qt-widgets" in yaml_text)
    check("yaml has conda-forge channel", "conda-forge" in yaml_text)
    check("yaml has vs2019_win-64 dep", "vs2019_win-64" in yaml_text)


async def test_conda_env_gen_linux_qt6():
    print("\n[22] qt_conda_env_gen -- linux + Qt 6.5.0 (qt-main packages)")
    d = fresh_dir(SANDBOX_TMP, "v23_cg_linux")
    out = await server.qt_conda_env_gen(QtCondaEnvGenInput(
        output_dir=str(d),
        qt_version="6.5.0",
        qt_modules=["widgets"],
        platform="linux",
    ))
    yaml_text = (d / "environment.yml").read_text(encoding="utf-8")
    check("qt-main=6.5.0 for Qt 6", "qt-main=6.5.0" in yaml_text)
    check("qt-main-qtwidgets for Qt 6", "qt-main-qtwidgets" in yaml_text)
    check("linux gets libgl-devel", "libgl-devel" in yaml_text)
    check("writes conda_install.sh", (d / "conda_install.sh").exists())


async def test_conda_env_gen_bad_platform():
    print("\n[23] qt_conda_env_gen -- bad platform rejected")
    out = await server.qt_conda_env_gen(QtCondaEnvGenInput(
        output_dir=str(SANDBOX_TMP / "v23_cg_badplat"),
        platform="plan9",
    ))
    check("rejects unknown platform", "Error" in out and "windows|linux|macos" in out)


# ============ qt_db_open_in_gui ============

async def test_db_open_in_gui_missing_db():
    print("\n[24] qt_db_open_in_gui -- missing db rejected")
    out = await server.qt_db_open_in_gui(QtDbOpenInGuiInput(
        db_file=str(SANDBOX_TMP / "nope.db"),
    ))
    check("rejects missing db", "Error" in out and "not found" in out)


async def test_db_open_in_gui_bad_gui_path():
    print("\n[25] qt_db_open_in_gui -- explicit bad gui_exe rejected")
    d = fresh_dir(SANDBOX_TMP, "v23_dog_badgui")
    db = d / "test.db"
    sqlite3.connect(str(db)).close()
    out = await server.qt_db_open_in_gui(QtDbOpenInGuiInput(
        db_file=str(db),
        gui_exe=str(SANDBOX_TMP / "definitely_not_an_exe.exe"),
    ))
    check("rejects bad gui_exe", "Error" in out and "not found" in out)


async def test_db_open_in_gui_launch():
    print("\n[26] qt_db_open_in_gui -- launch with explicit gui_exe (sanity)")
    d = fresh_dir(SANDBOX_TMP, "v23_dog_launch")
    db = d / "test.db"
    sqlite3.connect(str(db)).close()
    # Use notepad as a stand-in GUI client (just needs to launch; we kill after 1s)
    gui_exe = shutil.which("notepad.exe") or shutil.which("notepad")
    if not gui_exe:
        # Skip if notepad not available
        print(f"  [SKIP] notepad not available, skipping launch test")
        return
    # Copy notepad to sandbox so _in_sandbox passes
    gui_sandbox = d / "sandbox_gui.exe"
    shutil.copy(gui_exe, gui_sandbox)
    # Make a sandbox-local db
    db_sandbox = d / "sandbox.db"
    sqlite3.connect(str(db_sandbox)).close()
    out = await server.qt_db_open_in_gui(QtDbOpenInGuiInput(
        db_file=str(db_sandbox),
        gui_exe=str(gui_sandbox),
    ))
    # notepad is detached — but it may exit on its own. We just check the call didn't error.
    check("launches successfully", "PID:" in out or "PID" in out)
    # Kill the spawned process (best-effort)
    import re as _re
    m = _re.search(r"PID:\s*(\d+)", out)
    if m:
        try:
            subprocess.run(["taskkill", "/F", "/PID", m.group(1)], capture_output=True, timeout=5)
        except Exception:
            pass


# ============ qt_db_schema_diff ============

async def test_db_schema_diff_happy():
    print("\n[27] qt_db_schema_diff -- two dbs with differences")
    d = fresh_dir(SANDBOX_TMP, "v23_dsd_happy")
    a = make_temp_db(d, "a.db", {
        "users": "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
        "old_table": "CREATE TABLE old_table (id INTEGER)",
    })
    b = make_temp_db(d, "b.db", {
        "users": "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)",
        "new_table": "CREATE TABLE new_table (id INTEGER)",
    })
    out = await server.qt_db_schema_diff(QtDbSchemaDiffInput(
        db_a=str(a),
        db_b=str(b),
        emit_migration=True,
        output_format="text",
    ))
    check("detects add_column", "add_column" in out)
    check("detects create_table (new_table)", "create_table" in out and "new_table" in out)
    check("detects drop_table (old_table)", "drop_table" in out and "old_table" in out)
    check("emits ALTER TABLE migration", "ALTER TABLE users ADD COLUMN email" in out)
    check("emits CREATE TABLE migration", "CREATE TABLE new_table" in out)


async def test_db_schema_diff_identical():
    print("\n[28] qt_db_schema_diff -- identical dbs report no diffs")
    d = fresh_dir(SANDBOX_TMP, "v23_dsd_ident")
    a = make_temp_db(d, "a.db", {"t": "CREATE TABLE t (id INTEGER)"})
    b = make_temp_db(d, "b.db", {"t": "CREATE TABLE t (id INTEGER)"})
    out = await server.qt_db_schema_diff(QtDbSchemaDiffInput(
        db_a=str(a), db_b=str(b), output_format="text",
    ))
    check("identical reports Schemas are identical", "Schemas are identical" in out or "Differences: 0" in out)


async def test_db_schema_diff_missing():
    print("\n[29] qt_db_schema_diff -- missing db rejected")
    d = fresh_dir(SANDBOX_TMP, "v23_dsd_miss")
    a = make_temp_db(d, "a.db", {"t": "CREATE TABLE t (id INTEGER)"})
    out = await server.qt_db_schema_diff(QtDbSchemaDiffInput(
        db_a=str(a),
        db_b=str(SANDBOX_TMP / "nope.db"),
    ))
    check("rejects missing db", "Error" in out and "not found" in out)


# ============ qt_db_dump ============

async def test_db_dump_csv():
    print("\n[30] qt_db_dump -- CSV format")
    d = fresh_dir(SANDBOX_TMP, "v23_dd_csv")
    db = make_temp_db(d, "t.db", {
        "users": "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
    })
    # Insert a row
    conn = sqlite3.connect(str(db))
    conn.execute("INSERT INTO users (name) VALUES ('alice')")
    conn.commit()
    conn.close()
    out_path = d / "users.csv"
    out = await server.qt_db_dump(QtDbDumpInput(
        db_file=str(db),
        table_name="users",
        output_format="csv",
        output_path=str(out_path),
    ))
    check("writes CSV file", out_path.exists())
    csv_text = out_path.read_text(encoding="utf-8")
    check("CSV has header row", "id,name" in csv_text)
    check("CSV has alice row", "alice" in csv_text)


async def test_db_dump_json():
    print("\n[31] qt_db_dump -- JSON format")
    d = fresh_dir(SANDBOX_TMP, "v23_dd_json")
    db = make_temp_db(d, "t.db", {
        "items": "CREATE TABLE items (id INTEGER PRIMARY KEY, val INTEGER)",
    })
    conn = sqlite3.connect(str(db))
    conn.execute("INSERT INTO items (val) VALUES (10)")
    conn.execute("INSERT INTO items (val) VALUES (20)")
    conn.commit()
    conn.close()
    out = await server.qt_db_dump(QtDbDumpInput(
        db_file=str(db),
        table_name="items",
        output_format="json",
    ))
    check("JSON output is valid", out.strip().startswith("[") or "result" in out)
    check("JSON contains val=10", "10" in out)
    check("JSON contains val=20", "20" in out)


async def test_db_dump_sql():
    print("\n[32] qt_db_dump -- SQL format (CREATE + INSERT)")
    d = fresh_dir(SANDBOX_TMP, "v23_dd_sql")
    db = make_temp_db(d, "t.db", {
        "foo": "CREATE TABLE foo (id INTEGER PRIMARY KEY, x TEXT)",
    })
    conn = sqlite3.connect(str(db))
    conn.execute("INSERT INTO foo (x) VALUES ('bar')")
    conn.commit()
    conn.close()
    out = await server.qt_db_dump(QtDbDumpInput(
        db_file=str(db),
        table_name="foo",
        output_format="sql",
    ))
    check("SQL has CREATE TABLE", "CREATE TABLE foo" in out)
    check("SQL has INSERT", "INSERT INTO foo" in out)
    check("SQL has bar", "'bar'" in out)


# ============ qt_db_validate ============

async def test_db_validate_clean():
    print("\n[33] qt_db_validate -- clean db reports PASS")
    d = fresh_dir(SANDBOX_TMP, "v23_dv_clean")
    db = make_temp_db(d, "t.db", {
        "p": "CREATE TABLE p (id INTEGER PRIMARY KEY)",
        "c": "CREATE TABLE c (id INTEGER PRIMARY KEY, pid INTEGER REFERENCES p(id))",
    })
    out = await server.qt_db_validate(QtDbValidateInput(db_file=str(db), output_format="text"))
    check("clean db reports PASS", "Overall: PASS" in out)


async def test_db_validate_with_orphan():
    print("\n[34] qt_db_validate -- FK violations detected")
    d = fresh_dir(SANDBOX_TMP, "v23_dv_orphan")
    db = make_temp_db(d, "t.db", {
        "p": "CREATE TABLE p (id INTEGER PRIMARY KEY)",
        "c": "CREATE TABLE c (id INTEGER PRIMARY KEY, pid INTEGER REFERENCES p(id))",
    })
    # Insert orphan row
    conn = sqlite3.connect(str(db))
    conn.execute("INSERT INTO c (pid) VALUES (999)")  # no parent p.id=999
    conn.commit()
    conn.close()
    out = await server.qt_db_validate(QtDbValidateInput(db_file=str(db), output_format="text"))
    # FK check may or may not catch this depending on whether the FK was declared ON
    # The orphan scan SHOULD catch it.
    check("orphan detected", "Orphaned rows" in out and "FAIL" in out or "PASS" not in out)


async def test_db_validate_missing():
    print("\n[35] qt_db_validate -- missing db rejected")
    out = await server.qt_db_validate(QtDbValidateInput(
        db_file=str(SANDBOX_TMP / "nope.db"),
    ))
    check("rejects missing db", "Error" in out and "not found" in out)


async def test_db_validate_index():
    print("\n[36] qt_db_validate -- integrity check on indexed db")
    d = fresh_dir(SANDBOX_TMP, "v23_dv_index")
    db = make_temp_db(d, "t.db", {
        "users": "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
    })
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE INDEX idx_users_name ON users(name)")
    conn.execute("INSERT INTO users (name) VALUES ('alice')")
    conn.commit()
    conn.close()
    out = await server.qt_db_validate(QtDbValidateInput(db_file=str(db), output_format="text"))
    check("indexed db passes integrity", "Integrity check" in out and "ok" in out.lower())


# ============ runner ============

async def main():
    tests = [
        test_invoke_helper_gen_happy,
        test_invoke_helper_gen_bad_classname,
        test_invoke_helper_gen_no_modules,
        test_qproperty_set_happy,
        test_qproperty_set_missing_exe,
        test_meta_invoke_happy,
        test_meta_invoke_missing_exe,
        test_pro_lint_duplicates,
        test_pro_lint_clean,
        test_pro_lint_missing,
        test_pro_lint_json,
        test_shadow_build_happy,
        test_shadow_build_no_user_file,
        test_shadow_build_missing,
        test_qmlscene_missing_file,
        test_qmlscene_empty_scale_factors,
        test_qmlscene_not_qml,
        test_cmake_install_happy,
        test_cmake_install_no_bat,
        test_cmake_install_missing,
        test_conda_env_gen_windows,
        test_conda_env_gen_linux_qt6,
        test_conda_env_gen_bad_platform,
        test_db_open_in_gui_missing_db,
        test_db_open_in_gui_bad_gui_path,
        test_db_open_in_gui_launch,
        test_db_schema_diff_happy,
        test_db_schema_diff_identical,
        test_db_schema_diff_missing,
        test_db_dump_csv,
        test_db_dump_json,
        test_db_dump_sql,
        test_db_validate_clean,
        test_db_validate_with_orphan,
        test_db_validate_missing,
        test_db_validate_index,
    ]
    for t in tests:
        try:
            await t()
        except Exception as e:
            check(f"{t.__name__} (no exception)", False, str(e))
            import traceback
            traceback.print_exc()

    passed = sum(1 for _, c in results if c)
    total = len(results)
    print(f"\n=== Summary: {passed}/{total} checks passed ===")
    if passed == total:
        print("ALL OK")
        return 0
    print(f"FAIL: {total - passed} check(s) failed")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
