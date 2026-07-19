"""e2e for v28 new tools (v0.4.0):
  - qt_modernize_qt5_to_qt6 extension (3 new rules: qstring_literal_wrap, qbytearray_literal_wrap, qchar_qlatin1char)
  - qt_signature_batch       (batch-sign .exe/.dll in a directory)
  - qt_module_split_cmake    (plan / execute splitting CMake project into lib + app + add_subdirectory)

Run: python e2e_new_tools_v28.py
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
    QtModernizeQtInput,
    QtSignatureInput,
    QtModuleSplitCmakeInput,
    QtSignatureBatchInput,
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


def fresh_dir(parent: Path, tag: str) -> Path:
    d = parent / f"v28_{tag}"
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    return d


# ---------- qt_modernize_qt5_to_qt6 extension (3 new rules) ----------


async def test_modernize_qstringliteral_dry_run():
    print("\n[1] qt_modernize_qt5_to_qt6 -- QString(\"literal\") → QStringLiteral dry-run")
    d = fresh_dir(SANDBOX_TMP, "mz_qstringliteral")
    (d / "main.cpp").write_text(
        '#include <QString>\n'
        'void f() {\n'
        '    QString a = QString("hello");\n'
        '    QString b = QString("world");\n'
        '}\n',
        encoding="utf-8",
    )
    out = await server.qt_modernize_qt5_to_qt6(QtModernizeQtInput(
        project_dir=str(d),
        apply=False,
        rule_ids=["qstring_constructor_to_literal"],
    ))
    check("returns success", "===" in out)
    check("reports 2 replacements", "qstring_constructor_to_literal: 2 replacement" in out)


async def test_modernize_qstringliteral_apply():
    print("\n[2] qt_modernize_qt5_to_qt6 -- apply rewrites + writes .bak")
    d = fresh_dir(SANDBOX_TMP, "mz_qstringliteral_apply")
    (d / "main.cpp").write_text(
        '#include <QString>\n'
        'void f() { QString a = QString("hello"); }\n',
        encoding="utf-8",
    )
    out = await server.qt_modernize_qt5_to_qt6(QtModernizeQtInput(
        project_dir=str(d),
        apply=True,
        rule_ids=["qstring_constructor_to_literal"],
    ))
    check("returns success", "===" in out)
    check(".bak created", (d / "main.cpp.bak").exists())
    new = (d / "main.cpp").read_text(encoding="utf-8")
    check("rewrote to QStringLiteral", 'QStringLiteral("hello")' in new)
    check("QString(\"hello\") no longer present", 'QString("hello")' not in new)


async def test_modernize_qbytearrayliteral():
    print("\n[3] qt_modernize_qt5_to_qt6 -- QByteArray(\"literal\") → QByteArrayLiteral")
    d = fresh_dir(SANDBOX_TMP, "mz_qbytearrayliteral")
    (d / "main.cpp").write_text(
        '#include <QByteArray>\n'
        'void f() {\n'
        '    QByteArray a = QByteArray("data");\n'
        '    QByteArray b = QByteArray("more");\n'
        '    QByteArray c = QByteArray("bytes");\n'
        '}\n',
        encoding="utf-8",
    )
    out = await server.qt_modernize_qt5_to_qt6(QtModernizeQtInput(
        project_dir=str(d),
        apply=True,
        rule_ids=["qbytearray_constructor_to_literal"],
    ))
    check("returns success", "===" in out)
    new = (d / "main.cpp").read_text(encoding="utf-8")
    check("QByteArrayLiteral used 3 times", new.count("QByteArrayLiteral(") == 3)
    check("QByteArray(\"...\") no longer present", 'QByteArray("' not in new)


async def test_modernize_qlatin1char():
    print("\n[4] qt_modernize_qt5_to_qt6 -- QChar('x') → QLatin1Char('x')")
    d = fresh_dir(SANDBOX_TMP, "mz_qlatin1char")
    (d / "main.cpp").write_text(
        '#include <QChar>\n'
        'void f() {\n'
        '    QChar c1 = QChar(\'a\');\n'
        '    QChar c2 = QChar(\'Z\');\n'
        '}\n',
        encoding="utf-8",
    )
    out = await server.qt_modernize_qt5_to_qt6(QtModernizeQtInput(
        project_dir=str(d),
        apply=True,
        rule_ids=["qchar_constructor_to_qlatin1char"],
    ))
    check("returns success", "===" in out)
    new = (d / "main.cpp").read_text(encoding="utf-8")
    check("QLatin1Char('a') present", "QLatin1Char('a')" in new)
    check("QLatin1Char('Z') present", "QLatin1Char('Z')" in new)
    check("QChar('a') no longer present", "QChar('a')" not in new)


async def test_modernize_all_new_rules_combined():
    print("\n[5] qt_modernize_qt5_to_qt6 -- 3 new rules together")
    d = fresh_dir(SANDBOX_TMP, "mz_all_new")
    (d / "main.cpp").write_text(
        '#include <QString>\n'
        '#include <QByteArray>\n'
        '#include <QChar>\n'
        'void f() {\n'
        '    QString s = QString("hi");\n'
        '    QByteArray b = QByteArray("ho");\n'
        '    QChar c = QChar(\'x\');\n'
        '}\n',
        encoding="utf-8",
    )
    out = await server.qt_modernize_qt5_to_qt6(QtModernizeQtInput(
        project_dir=str(d),
        apply=True,
        rule_ids=[
            "qstring_constructor_to_literal",
            "qbytearray_constructor_to_literal",
            "qchar_constructor_to_qlatin1char",
        ],
    ))
    check("returns success", "===" in out)
    new = (d / "main.cpp").read_text(encoding="utf-8")
    check("all 3 rules applied: QStringLiteral", "QStringLiteral(\"hi\")" in new)
    check("all 3 rules applied: QByteArrayLiteral", "QByteArrayLiteral(\"ho\")" in new)
    check("all 3 rules applied: QLatin1Char", "QLatin1Char('x')" in new)


# ---------- qt_signature_batch ----------


async def test_signature_batch_info():
    print("\n[6] qt_signature_batch -- info action reports signtool availability")
    # Create a fake .exe to satisfy the "directory must contain files" check
    d = fresh_dir(SANDBOX_TMP, "sig_batch_info")
    (d / "fake.exe").write_bytes(b"MZ\x00")  # minimal MZ header so file is recognized
    out = await server.qt_signature_batch(QtSignatureBatchInput(
        action="info",
        directory=str(d),
    ))
    check("returns success or 'Error' (acceptable — signtool may not be installed)", "===" in out or "Error" in out)


async def test_signature_batch_scan():
    print("\n[7] qt_signature_batch -- scan action lists files matching pattern")
    d = fresh_dir(SANDBOX_TMP, "sig_batch_scan")
    (d / "app.exe").write_bytes(b"MZ\x00")
    (d / "helper.dll").write_bytes(b"MZ\x00")
    (d / "readme.txt").write_text("not a binary", encoding="utf-8")
    out = await server.qt_signature_batch(QtSignatureBatchInput(
        action="scan",
        directory=str(d),
        patterns=["*.exe", "*.dll"],
    ))
    check("returns success", "===" in out)
    check("finds app.exe", "app.exe" in out)
    check("finds helper.dll", "helper.dll" in out)
    check("skips readme.txt", "readme.txt" not in out)


async def test_signature_batch_invalid_action():
    print("\n[8] qt_signature_batch -- invalid action returns Error")
    out = await server.qt_signature_batch(QtSignatureBatchInput(
        action="invalid_action_xyz",
        directory=str(SANDBOX_TMP),
    ))
    check("returns Error", "Error" in out)
    check("mentions invalid", "invalid" in out.lower())


async def test_signature_batch_missing_dir():
    print("\n[9] qt_signature_batch -- missing directory returns Error")
    out = await server.qt_signature_batch(QtSignatureBatchInput(
        action="scan",
        directory="/nonexistent/path/xyz_abc",
    ))
    check("returns Error", "Error" in out)


async def test_signature_batch_empty_dir():
    print("\n[10] qt_signature_batch -- empty dir reports no matches")
    d = fresh_dir(SANDBOX_TMP, "sig_batch_empty")
    out = await server.qt_signature_batch(QtSignatureBatchInput(
        action="scan",
        directory=str(d),
    ))
    check("returns success", "===" in out)
    check("reports 0 matches", "0 " in out or "no" in out.lower() or "No" in out)


# ---------- qt_module_split_cmake ----------


async def test_module_split_cmake_plan_only():
    print("\n[11] qt_module_split_cmake -- plan_only=True emits CMake plan JSON")
    d = fresh_dir(SANDBOX_TMP, "ms_cmake_plan")
    # Create some .cpp/.h to split
    (d / "core.cpp").write_text("int core() { return 0; }", encoding="utf-8")
    (d / "core.h").write_text("int core();", encoding="utf-8")
    (d / "main.cpp").write_text("int main() { return core(); }", encoding="utf-8")
    out = await server.qt_module_split_cmake(QtModuleSplitCmakeInput(
        project_dir=str(d),
        target_lib_name="core",
        plan_only=True,
    ))
    check("returns success", "===" in out)
    check("plan_only report present", "plan_only" in out.lower() or "Plan" in out)
    plan_path = d / "cmake_split_plan.json"
    check("plan JSON exists", plan_path.exists())
    if plan_path.exists():
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        check("plan has lib_target", plan.get("lib_target") == "core")
        check("plan has moves list", isinstance(plan.get("moves"), list))
        check("plan has generated files", isinstance(plan.get("generated"), list))


async def test_module_split_cmake_execute():
    print("\n[12] qt_module_split_cmake -- plan_only=False generates CMakeLists.txt tree")
    d = fresh_dir(SANDBOX_TMP, "ms_cmake_exec")
    (d / "core.cpp").write_text("int core() { return 1; }", encoding="utf-8")
    (d / "core.h").write_text("int core();", encoding="utf-8")
    (d / "main.cpp").write_text("#include \"core.h\"\nint main() { return core(); }", encoding="utf-8")
    out = await server.qt_module_split_cmake(QtModuleSplitCmakeInput(
        project_dir=str(d),
        target_lib_name="core",
        target_app_name="myapp",
        plan_only=False,
    ))
    check("returns success", "===" in out)
    check("root CMakeLists.txt created", (d / "CMakeLists.txt").exists())
    check("lib/CMakeLists.txt created", (d / "lib" / "CMakeLists.txt").exists())
    check("app/CMakeLists.txt created", (d / "app" / "CMakeLists.txt").exists())
    if (d / "CMakeLists.txt").exists():
        root_txt = (d / "CMakeLists.txt").read_text(encoding="utf-8")
        check("root uses add_subdirectory", "add_subdirectory" in root_txt)
        check("root has project()", "project(" in root_txt)
    if (d / "lib" / "CMakeLists.txt").exists():
        lib_txt = (d / "lib" / "CMakeLists.txt").read_text(encoding="utf-8")
        check("lib has add_library", "add_library" in lib_txt)
        check("lib has target core", "core" in lib_txt)
    if (d / "app" / "CMakeLists.txt").exists():
        app_txt = (d / "app" / "CMakeLists.txt").read_text(encoding="utf-8")
        check("app has add_executable", "add_executable" in app_txt)
        check("app has target_link_libraries", "target_link_libraries" in app_txt)


async def test_module_split_cmake_no_files():
    print("\n[13] qt_module_split_cmake -- directory with no .cpp/.h returns Error")
    d = fresh_dir(SANDBOX_TMP, "ms_cmake_empty")
    out = await server.qt_module_split_cmake(QtModuleSplitCmakeInput(
        project_dir=str(d),
        plan_only=True,
    ))
    check("returns Error", "Error" in out)


async def test_module_split_cmake_pattern_filter():
    print("\n[14] qt_module_split_cmake -- file_patterns regex filters what goes to lib")
    d = fresh_dir(SANDBOX_TMP, "ms_cmake_pat")
    (d / "core.cpp").write_text("int core() { return 0; }", encoding="utf-8")
    (d / "core.h").write_text("int core();", encoding="utf-8")
    (d / "extra.cpp").write_text("int extra() { return 0; }", encoding="utf-8")
    (d / "main.cpp").write_text("int main() { return 0; }", encoding="utf-8")
    out = await server.qt_module_split_cmake(QtModuleSplitCmakeInput(
        project_dir=str(d),
        target_lib_name="core",
        file_patterns=[r"^core\.(cpp|h)$"],
        plan_only=True,
    ))
    check("returns success", "===" in out)
    plan_path = d / "cmake_split_plan.json"
    if plan_path.exists():
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        moves = plan.get("moves", [])
        # core.cpp/h should be in moves; extra.cpp should not (filtered by pattern)
        src_moves = [m["src"] for m in moves]
        check("core.cpp goes to lib", any("core.cpp" in m for m in src_moves))
        check("extra.cpp filtered out", not any("extra.cpp" in m for m in src_moves))


# ---------- summary ----------


async def main():
    tests = [
        test_modernize_qstringliteral_dry_run,
        test_modernize_qstringliteral_apply,
        test_modernize_qbytearrayliteral,
        test_modernize_qlatin1char,
        test_modernize_all_new_rules_combined,
        test_signature_batch_info,
        test_signature_batch_scan,
        test_signature_batch_invalid_action,
        test_signature_batch_missing_dir,
        test_signature_batch_empty_dir,
        test_module_split_cmake_plan_only,
        test_module_split_cmake_execute,
        test_module_split_cmake_no_files,
        test_module_split_cmake_pattern_filter,
    ]
    for t in tests:
        try:
            await t()
        except Exception as e:
            check(f"{t.__name__} no exception", False, hint=str(e)[:80])
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\n=== v0.4.0 Summary === passed {passed} / {total}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))