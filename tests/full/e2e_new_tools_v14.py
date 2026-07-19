"""e2e for v14 new tools (v0.2.9): qt_env_diff, qt_dll_search_path, qt_audio_convert,
qt_qss_inspect, qt_svg_to_png, qt_qml_property_linter, qt_accessibility_check,
qt_pro_project_graph.

Run: python e2e_new_tools_v14.py
"""

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import server
from server import (
    QtEnvDiffInput, QtDllSearchPathInput, QtAudioConvertInput,
    QtQssInspectInput, QtSvgToPngInput, QtQmlPropertyLinterInput,
    QtAccessibilityCheckInput, QtProProjectGraphInput,
    SANDBOX_TMP, SANDBOX_ROOT, QT_ROOT, QT_32_ROOT, QMAKE,
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


# ---------- qt_env_diff ----------

async def test_qt_env_diff_basic():
    print("\n[1] qt_env_diff -- compare 64-bit vs 32-bit Qt")
    out = await server.qt_env_diff(QtEnvDiffInput(
        env_a_path=str(QT_ROOT),
        env_b_path=str(QT_32_ROOT),
    ))
    check("emits comparison header", "qt_env_diff" in out)
    check("shows env A", "A:" in out)
    check("shows env B", "B:" in out)
    check("reports qmake", "qmake" in out)
    check("reports modules count", "modules" in out)


async def test_qt_env_diff_missing_dir():
    print("\n[2] qt_env_diff -- missing directory rejected")
    out = await server.qt_env_diff(QtEnvDiffInput(
        env_a_path=str(SANDBOX_TMP / "nonexistent_a"),
        env_b_path=str(QT_ROOT),
    ))
    check("returns Error:", "Error:" in out)
    check("mentions path", "nonexistent_a" in out or "env_a_path" in out)


async def test_qt_env_diff_sandbox_rejection():
    print("\n[3] qt_env_diff -- sandbox rejection")
    out = await server.qt_env_diff(QtEnvDiffInput(
        env_a_path=r"C:\Windows\System32",
        env_b_path=str(QT_ROOT),
    ))
    check("returns Error:", "Error:" in out)
    check("mentions sandbox", "sandbox" in out.lower())


# ---------- qt_dll_search_path ----------

async def test_qt_dll_search_path_basic():
    print("\n[4] qt_dll_search_path -- analyze qmake.exe itself")
    out = await server.qt_dll_search_path(QtDllSearchPathInput(
        executable=str(QMAKE),
    ))
    check("emits header", "qt_dll_search_path" in out)
    check("lists search order", "Search order" in out or "search" in out.lower())
    check("reports DLL count", "DLL" in out)


async def test_qt_dll_search_path_missing_exe():
    print("\n[5] qt_dll_search_path -- missing exe rejected")
    out = await server.qt_dll_search_path(QtDllSearchPathInput(
        executable=str(SANDBOX_TMP / "no_such.exe"),
    ))
    check("returns Error:", "Error:" in out)


async def test_qt_dll_search_path_sandbox_rejection():
    print("\n[6] qt_dll_search_path -- sandbox rejection")
    out = await server.qt_dll_search_path(QtDllSearchPathInput(
        executable=r"C:\Windows\System32\cmd.exe",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions sandbox", "sandbox" in out.lower())


# ---------- qt_audio_convert ----------

async def test_qt_audio_convert_invalid_format():
    print("\n[7] qt_audio_convert -- invalid format rejected")
    out = await server.qt_audio_convert(QtAudioConvertInput(
        input_files=[str(SANDBOX_TMP / "fake.wav")],
        output_format="avi",
        output_dir=str(SANDBOX_TMP / "v14_audio"),
    ))
    check("returns Error:", "Error:" in out)


async def test_qt_audio_convert_empty_files():
    print("\n[8] qt_audio_convert -- empty input_files rejected")
    out = await server.qt_audio_convert(QtAudioConvertInput(
        input_files=[],
        output_format="mp3",
        output_dir=str(SANDBOX_TMP / "v14_audio"),
    ))
    check("returns Error:", "Error:" in out)


async def test_qt_audio_convert_sandbox_rejection():
    print("\n[9] qt_audio_convert -- output_dir sandbox rejection")
    out = await server.qt_audio_convert(QtAudioConvertInput(
        input_files=[str(SANDBOX_TMP / "fake.wav")],
        output_format="mp3",
        output_dir=r"C:\Windows\Temp\bad",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions sandbox", "sandbox" in out.lower())


# ---------- qt_qss_inspect ----------

async def test_qt_qss_inspect_valid_qss():
    print("\n[10] qt_qss_inspect -- parses a generated QSS file")
    qss_dir = fresh_dir(SANDBOX_TMP, "v14_qss")
    qss_path = qss_dir / "test.qss"
    qss_path.write_text(
        "/* generated test */\n"
        "QWidget { background-color: #2D2D30; color: #F1F1F1; }\n"
        "QPushButton { background: #E8AB45; padding: 6px; }\n"
        "QPushButton:hover { background: #FFD27A; }\n"
        "QPushButton { color: #F1F1F1; }  /* duplicate selector */\n"
        "QLabel { font-size: 12pt; color: red; }\n",
        encoding="utf-8",
    )
    out = await server.qt_qss_inspect(QtQssInspectInput(qss_file=str(qss_path)))
    check("emits header", "qt_qss_inspect" in out)
    check("counts selectors", "Selectors" in out)
    check("detects duplicate selectors", "QPushButton" in out and ("duplicate" in out.lower() or "x2" in out))


async def test_qt_qss_inspect_missing_file():
    print("\n[11] qt_qss_inspect -- missing file rejected")
    out = await server.qt_qss_inspect(QtQssInspectInput(
        qss_file=str(SANDBOX_TMP / "no_such.qss"),
    ))
    check("returns Error:", "Error:" in out)


async def test_qt_qss_inspect_sandbox_rejection():
    print("\n[12] qt_qss_inspect -- sandbox rejection")
    out = await server.qt_qss_inspect(QtQssInspectInput(
        qss_file=r"C:\Windows\System32\drivers\etc\hosts",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions sandbox", "sandbox" in out.lower())


# ---------- qt_svg_to_png ----------

async def test_qt_svg_to_png_empty_files():
    print("\n[13] qt_svg_to_png -- empty input_files rejected")
    out = await server.qt_svg_to_png(QtSvgToPngInput(
        input_files=[],
        output_dir=str(SANDBOX_TMP / "v14_svg"),
        widths=[64],
    ))
    check("returns Error:", "Error:" in out)


async def test_qt_svg_to_png_empty_widths():
    print("\n[14] qt_svg_to_png -- empty widths rejected")
    out = await server.qt_svg_to_png(QtSvgToPngInput(
        input_files=[str(SANDBOX_TMP / "fake.svg")],
        output_dir=str(SANDBOX_TMP / "v14_svg"),
        widths=[],
    ))
    check("returns Error:", "Error:" in out)


async def test_qt_svg_to_png_sandbox_rejection():
    print("\n[15] qt_svg_to_png -- output_dir sandbox rejection")
    out = await server.qt_svg_to_png(QtSvgToPngInput(
        input_files=[str(SANDBOX_TMP / "fake.svg")],
        output_dir=r"C:\Windows\Temp\bad",
        widths=[64],
    ))
    check("returns Error:", "Error:" in out)
    check("mentions sandbox", "sandbox" in out.lower())


# ---------- qt_qml_property_linter ----------

async def test_qt_qml_property_linter_clean():
    print("\n[16] qt_qml_property_linter -- clean QML file")
    qml_dir = fresh_dir(SANDBOX_TMP, "v14_qml")
    qml_path = qml_dir / "clean.qml"
    qml_path.write_text(
        "import QtQuick 2.14\n"
        "Item {\n"
        "    id: root\n"
        "    property int count: 0\n"
        "    property string label: 'hello'\n"
        "    Text {\n"
        "        text: root.label\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_qml_property_linter(QtQmlPropertyLinterInput(
        qml_files=[str(qml_path)],
    ))
    check("emits header", "qt_qml_property_linter" in out)
    check("shows file", "clean.qml" in out)
    check("shows properties count", "properties" in out)


async def test_qt_qml_property_linter_unused_prop():
    print("\n[17] qt_qml_property_linter -- detects unused property")
    qml_dir = fresh_dir(SANDBOX_TMP, "v14_qml2")
    qml_path = qml_dir / "dirty.qml"
    qml_path.write_text(
        "import QtQuick 2.14\n"
        "Item {\n"
        "    id: root\n"
        "    property int unused: 42\n"
        "    property string used: 'hello'\n"
        "    Text { text: root.used }\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_qml_property_linter(QtQmlPropertyLinterInput(
        qml_files=[str(qml_path)],
    ))
    check("detects unused", "unused" in out)


async def test_qt_qml_property_linter_sandbox_rejection():
    print("\n[18] qt_qml_property_linter -- sandbox rejection")
    out = await server.qt_qml_property_linter(QtQmlPropertyLinterInput(
        qml_files=[r"C:\Windows\System32\fake.qml"],
    ))
    check("returns Error:", "Error:" in out)


# ---------- qt_accessibility_check ----------

async def test_qt_accessibility_check_missing_a11y():
    print("\n[19] qt_accessibility_check -- detects missing a11y calls")
    src_dir = fresh_dir(SANDBOX_TMP, "v14_a11y")
    src_path = src_dir / "mainwindow.cpp"
    src_path.write_text(
        "#include <QPushButton>\n"
        "void setupUI() {\n"
        "    QPushButton *btn = new QPushButton(\"Click\");\n"
        "    btn->setText(\"OK\");\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_accessibility_check(QtAccessibilityCheckInput(
        source_files=[str(src_path)],
    ))
    check("emits header", "qt_accessibility_check" in out)
    check("reports missing", "missing" in out or "Issues" in out)


async def test_qt_accessibility_check_clean():
    print("\n[20] qt_accessibility_check -- clean file")
    src_dir = fresh_dir(SANDBOX_TMP, "v14_a11y2")
    src_path = src_dir / "good.cpp"
    src_path.write_text(
        "#include <QPushButton>\n"
        "void setupUI() {\n"
        "    QPushButton *btn = new QPushButton(\"Click\");\n"
        "    btn->setObjectName(\"okBtn\");\n"
        "    btn->setAccessibleName(\"OK Button\");\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_accessibility_check(QtAccessibilityCheckInput(
        source_files=[str(src_path)],
    ))
    check("emits header", "qt_accessibility_check" in out)
    check("reports setAccessibleName count", "setAccessibleName" in out)


async def test_qt_accessibility_check_sandbox_rejection():
    print("\n[21] qt_accessibility_check -- sandbox rejection")
    out = await server.qt_accessibility_check(QtAccessibilityCheckInput(
        source_files=[r"C:\Windows\System32\fake.cpp"],
    ))
    check("returns Error:", "Error:" in out)


# ---------- qt_pro_project_graph ----------

async def test_qt_pro_project_graph_basic():
    print("\n[22] qt_pro_project_graph -- emits DOT for a small project")
    proj_dir = fresh_dir(SANDBOX_TMP, "v14_prograph")
    pro_path = proj_dir / "demo.pro"
    (proj_dir / "main.cpp").write_text(
        '#include "mainwindow.h"\n'
        "int main(int argc, char *argv[]) { return 0; }\n",
        encoding="utf-8",
    )
    (proj_dir / "mainwindow.h").write_text(
        "#include <QMainWindow>\n"
        "class MainWindow : public QMainWindow { Q_OBJECT }; \n",
        encoding="utf-8",
    )
    (proj_dir / "mainwindow.cpp").write_text(
        '#include "mainwindow.h"\n'
        "#include <QPushButton>\n"
        "void MainWindow::setup() {}\n",
        encoding="utf-8",
    )
    pro_path.write_text(
        "QT       += core widgets\n"
        "SOURCES  += main.cpp mainwindow.cpp\n"
        "HEADERS  += mainwindow.h\n",
        encoding="utf-8",
    )
    out = await server.qt_pro_project_graph(QtProProjectGraphInput(
        pro_file=str(pro_path),
    ))
    check("emits DOT header", out.startswith("digraph") or "digraph" in out[:200])
    check("has cluster", "cluster_sources" in out)
    check("includes main.cpp", "main.cpp" in out)
    check("includes mainwindow.h", "mainwindow.h" in out)


async def test_qt_pro_project_graph_output_file():
    print("\n[23] qt_pro_project_graph -- writes DOT to file")
    proj_dir = fresh_dir(SANDBOX_TMP, "v14_prograph2")
    pro_path = proj_dir / "demo2.pro"
    (proj_dir / "a.cpp").write_text("#include <QtCore>\n", encoding="utf-8")
    pro_path.write_text("QT       += core\nSOURCES  += a.cpp\n", encoding="utf-8")
    out_dot = proj_dir / "graph.dot"
    out = await server.qt_pro_project_graph(QtProProjectGraphInput(
        pro_file=str(pro_path),
        output_dot=str(out_dot),
    ))
    check("reports file write", "wrote" in out or "output_dot" in out)
    check("DOT file created", out_dot.exists())
    if out_dot.exists():
        check("DOT file has digraph", "digraph" in out_dot.read_text(encoding="utf-8"))


async def test_qt_pro_project_graph_sandbox_rejection():
    print("\n[24] qt_pro_project_graph -- sandbox rejection")
    out = await server.qt_pro_project_graph(QtProProjectGraphInput(
        pro_file=r"C:\Windows\System32\fake.pro",
    ))
    check("returns Error:", "Error:" in out)


# ---------- registration count ----------

async def test_tool_count():
    print("\n[25] Tool registration count")
    tools = await server.mcp.list_tools()
    names = {t.name for t in tools}
    expected_new = {
        "qt_env_diff", "qt_dll_search_path", "qt_audio_convert", "qt_qss_inspect",
        "qt_svg_to_png", "qt_qml_property_linter", "qt_accessibility_check",
        "qt_pro_project_graph",
    }
    missing = expected_new - names
    check(f"all 8 v0.2.9 tools registered (total >= 78)", len(tools) >= 78 and not missing,
          hint=f"missing: {missing}" if missing else "")


# ---------- runner ----------

ALL_TESTS = [
    test_qt_env_diff_basic,
    test_qt_env_diff_missing_dir,
    test_qt_env_diff_sandbox_rejection,
    test_qt_dll_search_path_basic,
    test_qt_dll_search_path_missing_exe,
    test_qt_dll_search_path_sandbox_rejection,
    test_qt_audio_convert_invalid_format,
    test_qt_audio_convert_empty_files,
    test_qt_audio_convert_sandbox_rejection,
    test_qt_qss_inspect_valid_qss,
    test_qt_qss_inspect_missing_file,
    test_qt_qss_inspect_sandbox_rejection,
    test_qt_svg_to_png_empty_files,
    test_qt_svg_to_png_empty_widths,
    test_qt_svg_to_png_sandbox_rejection,
    test_qt_qml_property_linter_clean,
    test_qt_qml_property_linter_unused_prop,
    test_qt_qml_property_linter_sandbox_rejection,
    test_qt_accessibility_check_missing_a11y,
    test_qt_accessibility_check_clean,
    test_qt_accessibility_check_sandbox_rejection,
    test_qt_pro_project_graph_basic,
    test_qt_pro_project_graph_output_file,
    test_qt_pro_project_graph_sandbox_rejection,
    test_tool_count,
]


async def main():
    print("=" * 60)
    print("qt-mcp v0.2.9 e2e (8 new tools)")
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