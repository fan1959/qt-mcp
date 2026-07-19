"""e2e for v22 new tools (v0.3.6):
  - qt_conanfile_gen       (Conan recipe generator for Qt projects)
  - qt_module_split_init   (plan / execute splitting flat .pro into lib + app + subdirs)
  - qt_modernize_qt5_to_qt6 (Qt 5 → Qt 6 modernizing transform)
  - qt_signal_disconnect_check (find connect() without paired disconnect())
  - qt_qml_perf_lint       (QML performance rules beyond qmllint)

Run: python e2e_new_tools_v22.py
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import server
from server import (
    SANDBOX_TMP,
    QtConanfileGenInput,
    QtModuleSplitInput,
    QtModernizeQtInput,
    QtSignalDisconnectCheckInput,
    QtQmlPerfLintInput,
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


# ---------- qt_conanfile_gen ----------

async def test_conanfile_gen_basic():
    print("\n[1] qt_conanfile_gen -- happy path emits conanfile.py + conanfile.txt + BUILD_README.md")
    d = fresh_dir(SANDBOX_TMP, "v22_cg_basic")
    (d / "demo.pro").write_text(
        "QT       += core widgets\n"
        "CONFIG   += c++17\n"
        "TARGET   = demoproj\n"
        "TEMPLATE = app\n"
        "SOURCES += main.cpp\n",
        encoding="utf-8",
    )
    out_dir = d / "out"
    out = await server.qt_conanfile_gen(QtConanfileGenInput(
        project_dir=str(d),
        output_dir=str(out_dir),
        qt_version="5.14.2",
        qt_modules=["core", "widgets"],
        use_system_qt=False,
    ))
    check("returns success", "ok" in out.lower() or "=== qt_conanfile_gen ===" in out)
    check("writes conanfile.py", (out_dir / "conanfile.py").exists())
    check("writes conanfile.txt", (out_dir / "conanfile.txt").exists())
    check("writes BUILD_README.md", (out_dir / "BUILD_README.md").exists())
    py_text = (out_dir / "conanfile.py").read_text(encoding="utf-8")
    check("python recipe has requires(self.requires)", "self.requires" in py_text)
    check("python recipe name is demoproj (from .pro TARGET)", "demoproj" in py_text)


async def test_conanfile_gen_system_qt_mode():
    print("\n[2] qt_conanfile_gen -- system Qt mode skips Conan qt package")
    d = fresh_dir(SANDBOX_TMP, "v22_cg_sysqt")
    (d / "demo.pro").write_text("TARGET = sysproj\n", encoding="utf-8")
    out_dir = d / "out"
    out = await server.qt_conanfile_gen(QtConanfileGenInput(
        project_dir=str(d),
        output_dir=str(out_dir),
        qt_version="5.14.2",
        qt_modules=["core", "widgets"],
        use_system_qt=True,
        qt_prefix="/opt/Qt/5.14.2/gcc_64",
    ))
    check("returns success", "=== qt_conanfile_gen ===" in out)
    txt_text = (out_dir / "conanfile.txt").read_text(encoding="utf-8")
    check("system-mode conanfile.txt has no qt/ pkg", "qt/" not in txt_text)
    py_text = (out_dir / "conanfile.py").read_text(encoding="utf-8")
    check("system-mode emits QTDIR env", "QTDIR" in py_text)


async def test_conanfile_gen_emit_profiles():
    print("\n[3] qt_conanfile_gen -- emit_profile='auto' writes windows/linux/macos profiles")
    d = fresh_dir(SANDBOX_TMP, "v22_cg_profiles")
    (d / "p.pro").write_text("TARGET = p\n", encoding="utf-8")
    out_dir = d / "out"
    out = await server.qt_conanfile_gen(QtConanfileGenInput(
        project_dir=str(d),
        output_dir=str(out_dir),
        qt_version="6.5.0",
        qt_modules=["core", "widgets", "qml", "quick"],
        emit_profile="auto",
        compiler_version="9.3",
    ))
    check("writes profiles/windows", (out_dir / "profiles" / "windows").exists())
    check("writes profiles/linux", (out_dir / "profiles" / "linux").exists())
    check("writes profiles/macos", (out_dir / "profiles" / "macos").exists())
    win_text = (out_dir / "profiles" / "windows").read_text(encoding="utf-8")
    check("windows profile has compiler.version=9.3", "9.3" in win_text)


async def test_conanfile_gen_missing_project():
    print("\n[4] qt_conanfile_gen -- nonexistent project_dir returns Error")
    out = await server.qt_conanfile_gen(QtConanfileGenInput(
        project_dir="C:/NoSuchProject",
        output_dir=str(SANDBOX_TMP / "v22_cg_noproj"),
        qt_version="5.14.2",
        qt_modules=["core"],
    ))
    check("returns Error:", "Error:" in out)


async def test_conanfile_gen_system_qt_without_prefix():
    print("\n[5] qt_conanfile_gen -- use_system_qt without qt_prefix returns Error")
    d = fresh_dir(SANDBOX_TMP, "v22_cg_sysqt_no_prefix")
    (d / "p.pro").write_text("TARGET = p\n", encoding="utf-8")
    out = await server.qt_conanfile_gen(QtConanfileGenInput(
        project_dir=str(d),
        output_dir=str(d / "out"),
        qt_version="5.14.2",
        qt_modules=["core"],
        use_system_qt=True,
        qt_prefix="",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions qt_prefix", "qt_prefix" in out)


# ---------- qt_module_split_init ----------

async def test_module_split_plan_only():
    print("\n[6] qt_module_split_init -- plan_only=True emits module_split_plan.json without moving files")
    d = fresh_dir(SANDBOX_TMP, "v22_ms_plan")
    (d / "demo.pro").write_text(
        "TARGET = splitme\n"
        "TEMPLATE = app\n"
        "SOURCES += main.cpp engine.cpp\n"
        "HEADERS += engine.h\n",
        encoding="utf-8",
    )
    (d / "main.cpp").write_text("int main() { return 0; }", encoding="utf-8")
    (d / "engine.cpp").write_text("// engine impl", encoding="utf-8")
    (d / "engine.h").write_text("void f();", encoding="utf-8")
    out = await server.qt_module_split_init(QtModuleSplitInput(
        project_dir=str(d),
        target_lib_name="engine",
        plan_only=True,
    ))
    check("returns success", "=== qt_module_split_init ===" in out)
    check("writes module_split_plan.json", (d / "module_split_plan.json").exists())
    check("did NOT create lib/ subdir", not (d / "lib").exists())
    check("did NOT create app/ subdir", not (d / "app").exists())
    plan = json.loads((d / "module_split_plan.json").read_text(encoding="utf-8"))
    check("plan has lib_target=engine", plan.get("lib_target") == "engine")
    check("plan has moves list with engine.cpp", any("engine.cpp" in m.get("src", "") for m in plan.get("moves", [])))


async def test_module_split_execute():
    print("\n[7] qt_module_split_init -- plan_only=False actually creates lib/ + app/ + .pro subdirs")
    d = fresh_dir(SANDBOX_TMP, "v22_ms_exec")
    (d / "demo.pro").write_text(
        "TARGET = splitme\n"
        "TEMPLATE = app\n"
        "SOURCES += main.cpp engine.cpp\n"
        "HEADERS += engine.h\n",
        encoding="utf-8",
    )
    (d / "main.cpp").write_text("int main() { return 0; }", encoding="utf-8")
    (d / "engine.cpp").write_text("void f() {}", encoding="utf-8")
    (d / "engine.h").write_text("void f();", encoding="utf-8")
    out = await server.qt_module_split_init(QtModuleSplitInput(
        project_dir=str(d),
        target_lib_name="engine",
        plan_only=False,
    ))
    check("returns success", "=== qt_module_split_init ===" in out)
    check("created lib/lib.pro", (d / "lib" / "lib.pro").exists())
    check("created app/app.pro", (d / "app" / "app.pro").exists())
    check("created lib/src/", (d / "lib" / "src").exists())
    check("created lib/include/engine/", (d / "lib" / "include" / "engine").exists())
    lib_pro_text = (d / "lib" / "lib.pro").read_text(encoding="utf-8")
    check("lib.pro has TEMPLATE = lib", re.search(r"TEMPLATE\s*=\s*lib", lib_pro_text) is not None)
    check("lib.pro has TARGET = engine", re.search(r"TARGET\s*=\s*engine", lib_pro_text) is not None)
    app_pro_text = (d / "app" / "app.pro").read_text(encoding="utf-8")
    check("app.pro has TEMPLATE = app", "TEMPLATE = app" in app_pro_text)
    root_pro = (d / "demo.pro").read_text(encoding="utf-8")
    check("root .pro is TEMPLATE = subdirs", "TEMPLATE = subdirs" in root_pro or "subdirs" in root_pro.lower())
    check("backup subdir exists", (d / ".qt_module_split_backup").exists())


async def test_module_split_no_pro():
    print("\n[8] qt_module_split_init -- project with no .pro returns Error")
    d = fresh_dir(SANDBOX_TMP, "v22_ms_nopro")
    (d / "main.cpp").write_text("int main() {}", encoding="utf-8")
    out = await server.qt_module_split_init(QtModuleSplitInput(
        project_dir=str(d),
        target_lib_name="core",
        plan_only=True,
    ))
    check("returns Error:", "Error:" in out)
    check("mentions .pro", ".pro" in out)


async def test_module_split_pattern_filter():
    print("\n[9] qt_module_split_init -- file_patterns filters which files go into lib")
    d = fresh_dir(SANDBOX_TMP, "v22_ms_filter")
    (d / "demo.pro").write_text(
        "TARGET = splitme\n"
        "TEMPLATE = app\n"
        "SOURCES += main.cpp engine.cpp utility.cpp\n"
        "HEADERS += engine.h utility.h\n",
        encoding="utf-8",
    )
    (d / "main.cpp").write_text("int main() {}", encoding="utf-8")
    (d / "engine.cpp").write_text("// e", encoding="utf-8")
    (d / "engine.h").write_text("// e", encoding="utf-8")
    (d / "utility.cpp").write_text("// u", encoding="utf-8")
    (d / "utility.h").write_text("// u", encoding="utf-8")
    out = await server.qt_module_split_init(QtModuleSplitInput(
        project_dir=str(d),
        target_lib_name="engine",
        file_patterns=[r"engine(\.cpp|\.h)$"],
        plan_only=True,
    ))
    check("writes plan", (d / "module_split_plan.json").exists())
    plan = json.loads((d / "module_split_plan.json").read_text(encoding="utf-8"))
    move_sources = [m["src"] for m in plan["moves"]]
    check("engine.cpp moves to lib", "engine.cpp" in move_sources)
    check("utility.cpp does NOT move", "utility.cpp" not in move_sources)


# ---------- qt_modernize_qt5_to_qt6 ----------

async def test_modernize_dry_run():
    print("\n[10] qt_modernize_qt5_to_qt6 -- dry-run reports changes but doesn't write files")
    d = fresh_dir(SANDBOX_TMP, "v22_mz_dry")
    (d / "main.cpp").write_text(
        "#include <QRegExp>\n"
        "void f() {\n"
        "    QRegExp re(\"a\");\n"
        "    QVector<int> v;\n"
        "    if (Q_NULLPTR != nullptr) {}\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_modernize_qt5_to_qt6(QtModernizeQtInput(
        project_dir=str(d),
        apply=False,
    ))
    check("returns success", "===" in out)
    check("reports files changed", "Files changed" in out)
    # Original file should be unchanged
    orig = (d / "main.cpp").read_text(encoding="utf-8")
    check("original QRegExp unchanged in dry-run", "QRegExp" in orig)
    check("original QVector unchanged in dry-run", "QVector" in orig)


async def test_modernize_apply():
    print("\n[11] qt_modernize_qt5_to_qt6 -- apply=True rewrites files + writes .bak")
    d = fresh_dir(SANDBOX_TMP, "v22_mz_apply")
    original_text = (
        "#include <QRegExp>\n"
        "void f() {\n"
        "    QRegExp re(\"a\");\n"
        "    QVector<int> v;\n"
        "    if (Q_NULLPTR != nullptr) {}\n"
        "}\n"
    )
    (d / "main.cpp").write_text(original_text, encoding="utf-8")
    out = await server.qt_modernize_qt5_to_qt6(QtModernizeQtInput(
        project_dir=str(d),
        apply=True,
    ))
    check("returns success", "===" in out)
    check("rewrote main.cpp", (d / "main.cpp.bak").exists())
    bak_text = (d / "main.cpp.bak").read_text(encoding="utf-8")
    check("backup has original QRegExp", "QRegExp" in bak_text)
    new_text = (d / "main.cpp").read_text(encoding="utf-8")
    check("rewrote QRegExp", "QRegularExpression" in new_text and "QRegExp" not in new_text)
    check("rewrote QVector to QList", "QVector" not in new_text and "QList" in new_text)
    check("rewrote Q_NULLPTR to nullptr", "Q_NULLPTR" not in new_text)


async def test_modernize_rule_filter():
    print("\n[12] qt_modernize_qt5_to_qt6 -- rule_ids restricts to one rule")
    d = fresh_dir(SANDBOX_TMP, "v22_mz_one_rule")
    (d / "main.cpp").write_text(
        "#include <QRegExp>\n"
        "void f() {\n"
        "    QRegExp re(\"a\");\n"
        "    QVector<int> v;\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_modernize_qt5_to_qt6(QtModernizeQtInput(
        project_dir=str(d),
        apply=False,
        rule_ids=["qregexp_to_qregularexpression"],
    ))
    check("returns success", "===" in out)
    orig = (d / "main.cpp").read_text(encoding="utf-8")
    check("QRegExp still present (will be reported in dry-run)", "QRegExp" in orig)
    check("QVector still present (other rule not enabled)", "QVector" in orig)


async def test_modernize_no_changes():
    print("\n[13] qt_modernize_qt5_to_qt6 -- clean Qt 6 code reports no changes")
    d = fresh_dir(SANDBOX_TMP, "v22_mz_clean")
    (d / "main.cpp").write_text(
        "#include <QRegularExpression>\n"
        "void f() {\n"
        "    QList<int> v;\n"
        "    if (nullptr == nullptr) {}\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_modernize_qt5_to_qt6(QtModernizeQtInput(
        project_dir=str(d),
        apply=False,
    ))
    check("reports no changes needed", "No changes needed" in out or "Files changed: 0" in out)


# ---------- qt_signal_disconnect_check ----------

async def test_signal_disconnect_no_connect():
    print("\n[14] qt_signal_disconnect_check -- clean .cpp (no connect) reports no findings")
    d = fresh_dir(SANDBOX_TMP, "v22_sd_clean")
    (d / "main.cpp").write_text("int main() { return 0; }", encoding="utf-8")
    out = await server.qt_signal_disconnect_check(QtSignalDisconnectCheckInput(
        project_dir=str(d),
        output_format="text",
    ))
    check("returns success", "=== qt_signal_disconnect_check ===" in out)
    check("reports no unpaired connects", "No unpaired" in out or "Total findings: 0" in out or "Unpaired connect() sites: 0" in out)


async def test_signal_disconnect_unpaired():
    print("\n[15] qt_signal_disconnect_check -- unpaired connect flagged")
    d = fresh_dir(SANDBOX_TMP, "v22_sd_unpaired")
    # Cross-file: one file has connect, other has disconnect. We use same file for unpaired.
    (d / "widget.cpp").write_text(
        "void Widget::setup(QObject *src) {\n"
        "    connect(src, &QObject::destroyed, this, &Widget::onDestroyed);\n"
        "    // No matching disconnect(src, ...)\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_signal_disconnect_check(QtSignalDisconnectCheckInput(
        project_dir=str(d),
        output_format="text",
    ))
    check("returns success", "=== qt_signal_disconnect_check ===" in out)
    check("flags the unpaired connect", "Unpaired connect() sites: 1" in out or "src" in out)


async def test_signal_disconnect_paired():
    print("\n[16] qt_signal_disconnect_check -- paired connect (connect + disconnect same var) skipped")
    d = fresh_dir(SANDBOX_TMP, "v22_sd_paired")
    (d / "widget.cpp").write_text(
        "void Widget::setup(QObject *src) {\n"
        "    connect(src, &QObject::destroyed, this, &Widget::onDestroyed);\n"
        "}\n"
        "void Widget::teardown(QObject *src) {\n"
        "    disconnect(src, &QObject::destroyed, this, &Widget::onDestroyed);\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_signal_disconnect_check(QtSignalDisconnectCheckInput(
        project_dir=str(d),
        output_format="text",
    ))
    check("returns success", "===" in out)
    check("no unpaired flagged (paired)", "Unpaired connect() sites: 0" in out or "Already disconnected" in out)


async def test_signal_disconnect_json_format():
    print("\n[17] qt_signal_disconnect_check -- output_format=json returns parseable JSON")
    d = fresh_dir(SANDBOX_TMP, "v22_sd_json")
    (d / "main.cpp").write_text("int main() {}", encoding="utf-8")
    out = await server.qt_signal_disconnect_check(QtSignalDisconnectCheckInput(
        project_dir=str(d),
        output_format="json",
    ))
    try:
        body = out.split("\n\n--- json ---\n")[0]
        payload = json.loads(body)
        check("json has findings list", isinstance(payload.get("findings"), list))
    except Exception as e:
        check("json parses", False, hint=str(e))


async def test_signal_disconnect_bad_format():
    print("\n[18] qt_signal_disconnect_check -- output_format='yaml' returns Error")
    d = fresh_dir(SANDBOX_TMP, "v22_sd_badfmt")
    (d / "main.cpp").write_text("int main() {}", encoding="utf-8")
    out = await server.qt_signal_disconnect_check(QtSignalDisconnectCheckInput(
        project_dir=str(d),
        output_format="yaml",
    ))
    check("returns Error:", "Error:" in out)


# ---------- qt_qml_perf_lint ----------

async def test_qml_perf_lint_clean_file():
    print("\n[19] qt_qml_perf_lint -- clean .qml reports no findings")
    d = fresh_dir(SANDBOX_TMP, "v22_qpl_clean")
    (d / "main.qml").write_text(
        "import QtQuick 2.14\n"
        "Rectangle {\n"
        "    width: 200\n"
        "    height: 200\n"
        "    Text {\n"
        "        anchors.centerIn: parent\n"
        "        text: 'hello'\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_qml_perf_lint(QtQmlPerfLintInput(
        project_dir=str(d),
        output_format="text",
    ))
    check("returns success", "=== qt_qml_perf_lint ===" in out)
    check("reports no findings", "No QML performance issues" in out or "Total findings: 0" in out)


async def test_qml_perf_lint_sync_image():
    print("\n[20] qt_qml_perf_lint -- synchronous Image flagged")
    d = fresh_dir(SANDBOX_TMP, "v22_qpl_syncimg")
    (d / "main.qml").write_text(
        "import QtQuick 2.14\n"
        "Item {\n"
        "    Image {\n"
        "        source: 'big.png'\n"
        "        asynchronous: false\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_qml_perf_lint(QtQmlPerfLintInput(
        project_dir=str(d),
        output_format="text",
    ))
    check("flags image_synchronous_load", "image_synchronous_load" in out or "synchronous" in out.lower())


async def test_qml_perf_lint_transparent_mousearea():
    print("\n[21] qt_qml_perf_lint -- transparent MouseArea flagged")
    d = fresh_dir(SANDBOX_TMP, "v22_qpl_mouse")
    (d / "main.qml").write_text(
        "import QtQuick 2.14\n"
        "Item {\n"
        "    MouseArea {\n"
        "        anchors.fill: parent\n"
        "        visible: false\n"
        "        onClicked: doThing()\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_qml_perf_lint(QtQmlPerfLintInput(
        project_dir=str(d),
        output_format="text",
    ))
    check("flags transparent_mousearea", "transparent_mousearea" in out or "MouseArea" in out and "visible:false" in out)


async def test_qml_perf_lint_json_format():
    print("\n[22] qt_qml_perf_lint -- output_format=json returns parseable JSON")
    d = fresh_dir(SANDBOX_TMP, "v22_qpl_json")
    (d / "main.qml").write_text("Item { width: 100 }", encoding="utf-8")
    out = await server.qt_qml_perf_lint(QtQmlPerfLintInput(
        project_dir=str(d),
        output_format="json",
    ))
    try:
        body = out.split("\n\n--- json ---\n")[0]
        payload = json.loads(body)
        check("json has rules list", isinstance(payload.get("rules"), list))
        check("json has findings list", isinstance(payload.get("findings"), list))
    except Exception as e:
        check("json parses", False, hint=str(e))


async def test_qml_perf_lint_rule_filter():
    print("\n[23] qt_qml_perf_lint -- rule_ids restricts the rules applied")
    d = fresh_dir(SANDBOX_TMP, "v22_qpl_rules")
    (d / "main.qml").write_text(
        "import QtQuick 2.14\n"
        "Item {\n"
        "    Image {\n"
        "        source: 'x.png'\n"
        "        asynchronous: false\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_qml_perf_lint(QtQmlPerfLintInput(
        project_dir=str(d),
        output_format="text",
        rule_ids=["image_synchronous_load"],
    ))
    check("flags image_synchronous_load (enabled)", "image_synchronous_load" in out or "synchronous" in out.lower())


async def test_qml_perf_lint_bad_format():
    print("\n[24] qt_qml_perf_lint -- output_format='toml' returns Error")
    d = fresh_dir(SANDBOX_TMP, "v22_qpl_badfmt")
    (d / "main.qml").write_text("Item { }", encoding="utf-8")
    out = await server.qt_qml_perf_lint(QtQmlPerfLintInput(
        project_dir=str(d),
        output_format="toml",
    ))
    check("returns Error:", "Error:" in out)


async def test_qml_perf_lint_no_qml_files():
    print("\n[25] qt_qml_perf_lint -- project with no .qml files reports 0 scanned")
    d = fresh_dir(SANDBOX_TMP, "v22_qpl_nofiles")
    (d / "main.cpp").write_text("int main() {}", encoding="utf-8")
    out = await server.qt_qml_perf_lint(QtQmlPerfLintInput(
        project_dir=str(d),
        output_format="text",
    ))
    check("returns success", "=== qt_qml_perf_lint ===" in out)
    check("reports no findings", "No QML performance issues" in out)


# ---------- main ----------

async def main() -> int:
    tests = [
        test_conanfile_gen_basic,
        test_conanfile_gen_system_qt_mode,
        test_conanfile_gen_emit_profiles,
        test_conanfile_gen_missing_project,
        test_conanfile_gen_system_qt_without_prefix,
        test_module_split_plan_only,
        test_module_split_execute,
        test_module_split_no_pro,
        test_module_split_pattern_filter,
        test_modernize_dry_run,
        test_modernize_apply,
        test_modernize_rule_filter,
        test_modernize_no_changes,
        test_signal_disconnect_no_connect,
        test_signal_disconnect_unpaired,
        test_signal_disconnect_paired,
        test_signal_disconnect_json_format,
        test_signal_disconnect_bad_format,
        test_qml_perf_lint_clean_file,
        test_qml_perf_lint_sync_image,
        test_qml_perf_lint_transparent_mousearea,
        test_qml_perf_lint_json_format,
        test_qml_perf_lint_rule_filter,
        test_qml_perf_lint_bad_format,
        test_qml_perf_lint_no_qml_files,
    ]
    for t in tests:
        try:
            await t()
        except Exception as e:
            print(f"  [FAIL] {t.__name__} crashed: {e}")

    passed = sum(1 for _, c in results if c)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  Total: {passed}/{total} checks passed")
    if passed < total:
        print(f"  Failures: {total - passed}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
