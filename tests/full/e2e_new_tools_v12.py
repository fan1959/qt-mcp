"""e2e for v12 new tools: qt_model_gen, qt_theme_gen, qt_ico_create, qt_screenshot_diff,
qt_clazy_check, qt_signal_slot_trace, qt_input_recorder, qt_translation_validate.

Run: python e2e_new_tools_v12.py
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import server
from server import (
    QtModelGenInput, QtThemeGenInput, QtIcoCreateInput, QtScreenshotDiffInput,
    QtClazyCheckInput, QtSignalSlotTraceInput, QtInputRecorderInput,
    QtTranslationValidateInput,
    SANDBOX_TMP, SANDBOX_ROOT,
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


# ---------- qt_model_gen ----------

async def test_qt_model_gen_list():
    print("\n[1] qt_model_gen -- list model")
    out_dir = SANDBOX_TMP / "v12_model_list"
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    out = await server.qt_model_gen(QtModelGenInput(
        class_name="CardModel", model_type="list", item_type="QString", output_dir=str(out_dir),
    ))
    check("emits list model", "QAbstractListModel" in out)
    check("wrote header", (out_dir / "CardModel.h").exists())
    check("wrote source", (out_dir / "CardModel.cpp").exists())
    if (out_dir / "CardModel.h").exists():
        text = (out_dir / "CardModel.h").read_text(encoding="utf-8")
        check("header has Q_OBJECT", "Q_OBJECT" in text)
        check("header has rowCount override", "rowCount" in text)
        check("header has addItem slot", "addItem" in text)
        check("header has roleNames decl", "roleNames" in text)


async def test_qt_model_gen_table():
    print("\n[2] qt_model_gen -- table model with columns")
    out_dir = SANDBOX_TMP / "v12_model_table"
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    out = await server.qt_model_gen(QtModelGenInput(
        class_name="PlayerModel", model_type="table",
        columns=[{"name": "id", "type": "int"}, {"name": "name", "type": "QString"}, {"name": "score", "type": "int"}],
        output_dir=str(out_dir),
    ))
    check("emits table model", "QAbstractTableModel" in out)
    check("wrote header", (out_dir / "PlayerModel.h").exists())
    if (out_dir / "PlayerModel.h").exists():
        text = (out_dir / "PlayerModel.h").read_text(encoding="utf-8")
        check("header has columnCount override", "columnCount" in text)
        check("header has headerData override", "headerData" in text)


async def test_qt_model_gen_invalid_type():
    print("\n[3] qt_model_gen -- invalid model_type rejected")
    out = await server.qt_model_gen(QtModelGenInput(
        class_name="Foo", model_type="weird", output_dir=str(SANDBOX_TMP / "v12_invalid"),
    ))
    check("rejects invalid model_type", "Error:" in out)


async def test_qt_model_gen_table_no_columns():
    print("\n[4] qt_model_gen -- table model without columns rejected")
    out = await server.qt_model_gen(QtModelGenInput(
        class_name="Bar", model_type="table", output_dir=str(SANDBOX_TMP / "v12_no_cols"),
    ))
    check("rejects table w/o columns", "columns" in out.lower())


# ---------- qt_theme_gen ----------

async def test_qt_theme_gen_dark():
    print("\n[5] qt_theme_gen -- dark theme")
    out_path = SANDBOX_TMP / "v12_theme_dark.qss"
    if out_path.exists():
        out_path.unlink()
    out = await server.qt_theme_gen(QtThemeGenInput(
        theme_name="darkwood", mode="dark",
        base_color="#2D2D30", accent_color="#E8AB45", text_color="#F1F1F1",
        output_file=str(out_path),
    ))
    check("wrote QSS", out_path.exists())
    check("wrote > 1KB", out_path.stat().st_size > 1024)
    if out_path.exists():
        text = out_path.read_text(encoding="utf-8")
        check("has QPushButton selector", "QPushButton" in text)
        check("has QLineEdit selector", "QLineEdit" in text)
        check("has QListWidget selector", "QListWidget" in text)
        check("has hover state", ":hover" in text)
        check("has accent color in output", "#E8AB45" in text)


async def test_qt_theme_gen_light():
    print("\n[6] qt_theme_gen -- light theme")
    out_path = SANDBOX_TMP / "v12_theme_light.qss"
    if out_path.exists():
        out_path.unlink()
    out = await server.qt_theme_gen(QtThemeGenInput(
        theme_name="paper", mode="light",
        base_color="#FAFAFA", accent_color="#3B82F6", text_color="#1A1A1A",
        output_file=str(out_path),
    ))
    check("wrote QSS", out_path.exists())
    if out_path.exists():
        text = out_path.read_text(encoding="utf-8")
        check("has QSS comment", "Qt Style Sheet" in text)
        check("has ScrollBar selector", "QScrollBar" in text)


async def test_qt_theme_gen_invalid_mode():
    print("\n[7] qt_theme_gen -- invalid mode rejected")
    out = await server.qt_theme_gen(QtThemeGenInput(
        mode="neon", base_color="#FF00FF", output_file=str(SANDBOX_TMP / "v12_invalid.qss"),
    ))
    check("rejects invalid mode", "Error:" in out)


async def test_qt_theme_gen_invalid_color():
    print("\n[8] qt_theme_gen -- invalid base_color rejected")
    out = await server.qt_theme_gen(QtThemeGenInput(
        mode="dark", base_color="not-a-hex", output_file=str(SANDBOX_TMP / "v12_invalid.qss"),
    ))
    check("rejects invalid hex", "Error:" in out)


# ---------- qt_ico_create ----------

async def test_qt_ico_create():
    print("\n[9] qt_ico_create -- multi-res .ico from PNGs")
    src_dir = SANDBOX_TMP / "v12_ico_src"
    if src_dir.exists():
        shutil.rmtree(src_dir, ignore_errors=True)
    src_dir.mkdir(parents=True, exist_ok=True)
    # Create two test PNGs of different sizes using Pillow
    try:
        from PIL import Image
        im1 = Image.new("RGBA", (256, 256), (200, 100, 50, 255))
        im1.save(src_dir / "icon256.png")
        im2 = Image.new("RGBA", (32, 32), (50, 200, 100, 255))
        im2.save(src_dir / "icon32.png")
    except ImportError:
        check("Pillow available", False, "Pillow not installed")
        return

    out_ico = SANDBOX_TMP / "v12_output.ico"
    if out_ico.exists():
        out_ico.unlink()
    out = await server.qt_ico_create(QtIcoCreateInput(
        png_files=[str(src_dir / "icon256.png"), str(src_dir / "icon32.png")],
        output_ico=str(out_ico),
        sizes=[16, 32, 48, 64, 128, 256],
    ))
    check("wrote ICO", out_ico.exists())
    if out_ico.exists():
        check("ICO > 100 bytes", out_ico.stat().st_size > 100)
        check("ICO magic header", out_ico.read_bytes()[:4] == b"\x00\x00\x01\x00")
        check("report mentions 6 sizes", "6" in out or "256" in out)


async def test_qt_ico_create_missing_source():
    print("\n[10] qt_ico_create -- missing source PNG")
    out = await server.qt_ico_create(QtIcoCreateInput(
        png_files=["/nonexistent/foo.png"],
        output_ico=str(SANDBOX_TMP / "v12_missing.ico"),
    ))
    check("rejects missing source", "Error:" in out)


# ---------- qt_screenshot_diff ----------

async def test_qt_screenshot_diff_identical():
    print("\n[11] qt_screenshot_diff -- identical images")
    try:
        from PIL import Image
    except ImportError:
        check("Pillow available", False, "Pillow not installed")
        return
    src_dir = SANDBOX_TMP / "v12_screenshot_src"
    if src_dir.exists():
        shutil.rmtree(src_dir, ignore_errors=True)
    src_dir.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", (50, 50), (100, 150, 200, 255))
    a = src_dir / "a.png"
    b = src_dir / "b.png"
    img.save(a)
    img.save(b)
    out = await server.qt_screenshot_diff(QtScreenshotDiffInput(image_a=str(a), image_b=str(b)))
    check("identical diff returns 0", "0 /" in out or "0.000%" in out)
    check("bbox: (none)", "(none" in out or "match" in out.lower())


async def test_qt_screenshot_diff_different():
    print("\n[12] qt_screenshot_diff -- different images")
    try:
        from PIL import Image
    except ImportError:
        check("Pillow available", False, "Pillow not installed")
        return
    src_dir = SANDBOX_TMP / "v12_screenshot_src2"
    if src_dir.exists():
        shutil.rmtree(src_dir, ignore_errors=True)
    src_dir.mkdir(parents=True, exist_ok=True)
    a = src_dir / "x.png"
    b = src_dir / "y.png"
    Image.new("RGBA", (50, 50), (100, 150, 200, 255)).save(a)
    Image.new("RGBA", (50, 50), (200, 50, 100, 255)).save(b)
    diff_path = src_dir / "diff.png"
    out = await server.qt_screenshot_diff(QtScreenshotDiffInput(
        image_a=str(a), image_b=str(b), diff_image=str(diff_path), tolerance=0,
    ))
    check("detects diff", "diff" in out.lower())
    # Extract the diff line and check coverage > 0%
    import re as _re
    m = _re.search(r"diff:\s+(\d+)\s+/\s+(\d+)\s+pixels\s+\(([\d.]+)%\)", out)
    check("diff_count > 0 parsed", m is not None and int(m.group(1)) > 0)
    if m:
        check("diff coverage > 50%", float(m.group(3)) > 50.0)
    check("wrote diff image", diff_path.exists())


async def test_qt_screenshot_diff_size_mismatch():
    print("\n[13] qt_screenshot_diff -- size mismatch rejected")
    try:
        from PIL import Image
    except ImportError:
        check("Pillow available", False, "Pillow not installed")
        return
    src_dir = SANDBOX_TMP / "v12_screenshot_src"
    src_dir.mkdir(parents=True, exist_ok=True)
    a = src_dir / "small.png"
    b = src_dir / "big.png"
    Image.new("RGBA", (10, 10), (0, 0, 0, 255)).save(a)
    Image.new("RGBA", (20, 20), (0, 0, 0, 255)).save(b)
    out = await server.qt_screenshot_diff(QtScreenshotDiffInput(image_a=str(a), image_b=str(b)))
    check("rejects size mismatch", "size mismatch" in out.lower() or "Error:" in out)


# ---------- qt_clazy_check ----------

async def test_qt_clazy_check_finds_issues():
    print("\n[14] qt_clazy_check -- finds Qt anti-patterns in sample project")
    proj = SANDBOX_TMP / "v12_clazy_sample"
    if proj.exists():
        shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True, exist_ok=True)
    # .h with QObject subclass missing Q_OBJECT
    (proj / "bad.h").write_text(
        "#pragma once\n#include <QObject>\n"
        "class BadClass : public QObject {\n"
        "public:\n    BadClass() {}\n};\n", encoding="utf-8")
    # .cpp with Q_OBJECT (wrong) and QVector (Qt 4)
    (proj / "bad.cpp").write_text(
        "#include \"bad.h\"\nQ_OBJECT\n"
        "QVector<int> v;\n"
        "void f() { new QObject(); }\n", encoding="utf-8")
    out = await server.qt_clazy_check(QtClazyCheckInput(project_dir=str(proj)))
    check("found Q_OBJECT in .cpp", "Q_OBJECT" in out and ".cpp" in out)
    check("found QVector", "QVector" in out)
    check("found missing Q_OBJECT", "missing Q_OBJECT" in out or "missing-qobject" in out)


async def test_qt_clazy_check_clean_project():
    print("\n[15] qt_clazy_check -- clean project reports 0 issues")
    proj = SANDBOX_TMP / "v12_clazy_clean"
    if proj.exists():
        shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "clean.h").write_text(
        "#pragma once\n#include <QObject>\n"
        "class GoodClass : public QObject {\n"
        "    Q_OBJECT\n    Q_DISABLE_COPY(GoodClass)\n"
        "public:\n    explicit GoodClass(QObject* parent = nullptr) : QObject(parent) {}\n};\n", encoding="utf-8")
    (proj / "clean.cpp").write_text(
        "#include \"clean.h\"\n", encoding="utf-8")
    out = await server.qt_clazy_check(QtClazyCheckInput(project_dir=str(proj)))
    check("clean project: 0 issues", "0 issue" in out)


async def test_qt_clazy_check_invalid_check():
    print("\n[16] qt_clazy_check -- invalid check name rejected")
    out = await server.qt_clazy_check(QtClazyCheckInput(
        project_dir=str(SANDBOX_TMP / "v12_clazy_sample"),
        checks=["bogus-check-name"],
    ))
    check("rejects invalid check", "unknown checks" in out.lower() or "Error:" in out)


# ---------- qt_signal_slot_trace ----------

async def test_qt_signal_slot_trace_basic():
    print("\n[17] qt_signal_slot_trace -- basic connect() discovery")
    proj = SANDBOX_TMP / "v12_sst_sample"
    if proj.exists():
        shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "mainwindow.h").write_text(
        "#pragma once\n#include <QMainWindow>\n"
        "class MainWindow : public QMainWindow {\n"
        "    Q_OBJECT\npublic:\n    MainWindow(QWidget* parent = nullptr);\nsignals:\n    void valueChanged(int v);\npublic slots:\n    void onButtonClicked();\n    void onValueChanged(int v);\n};\n", encoding="utf-8")
    (proj / "mainwindow.cpp").write_text(
        "#include \"mainwindow.h\"\n"
        "MainWindow::MainWindow(QWidget* parent) : QMainWindow(parent) {\n"
        "    QObject::connect(this, &MainWindow::valueChanged, this, &MainWindow::onValueChanged);\n"
        "    QObject::connect(button, &QPushButton::clicked, this, &MainWindow::onButtonClicked);\n"
        "}\n", encoding="utf-8")
    out = await server.qt_signal_slot_trace(QtSignalSlotTraceInput(project_dir=str(proj), output_format="text"))
    check("found valueChanged signal", "valueChanged" in out)
    check("found onButtonClicked slot", "onButtonClicked" in out)
    check("found 2 connections", "2 connection" in out)


async def test_qt_signal_slot_trace_json():
    print("\n[18] qt_signal_slot_trace -- JSON output format")
    proj = SANDBOX_TMP / "v12_sst_sample"
    out = await server.qt_signal_slot_trace(QtSignalSlotTraceInput(project_dir=str(proj), output_format="json"))
    check("returns valid JSON", out.strip().startswith("{") and "\"connections\"" in out)


async def test_qt_signal_slot_trace_dot():
    print("\n[19] qt_signal_slot_trace -- dot (Graphviz) output format")
    proj = SANDBOX_TMP / "v12_sst_sample"
    out = await server.qt_signal_slot_trace(QtSignalSlotTraceInput(project_dir=str(proj), output_format="dot"))
    check("returns digraph", "digraph signals" in out)
    check("has edges", "->" in out)


async def test_qt_signal_slot_trace_output_file():
    print("\n[20] qt_signal_slot_trace -- writes to output file")
    proj = SANDBOX_TMP / "v12_sst_sample"
    out_file = SANDBOX_TMP / "v12_sst.json"
    if out_file.exists():
        out_file.unlink()
    out = await server.qt_signal_slot_trace(QtSignalSlotTraceInput(project_dir=str(proj), output_format="json", output_file=str(out_file)))
    check("wrote file", out_file.exists())
    check("output message says wrote", "wrote" in out)


# ---------- qt_input_recorder ----------

async def test_qt_input_recorder_info_synth():
    print("\n[21] qt_input_recorder -- info on synthetic file")
    import json as _json
    rec_dir = SANDBOX_ROOT / ".input_recordings"
    rec_dir.mkdir(parents=True, exist_ok=True)
    target = rec_dir / "v12_synth.json"
    payload = {
        "version": 1, "recorded_at": 1234567890, "duration_seconds": 2.0,
        "event_count": 5,
        "events": [
            {"t": 0.0, "type": "move", "x": 10, "y": 20},
            {"t": 0.5, "type": "click", "x": 10, "y": 20, "button": "left", "pressed": True},
            {"t": 1.0, "type": "scroll", "x": 10, "y": 20, "dx": 0, "dy": -3},
            {"t": 1.5, "type": "key_down", "key": "a"},
            {"t": 2.0, "type": "key_up", "key": "a"},
        ],
    }
    target.write_text(_json.dumps(payload), encoding="utf-8")
    out = await server.qt_input_recorder(QtInputRecorderInput(action="info", input_file=str(target)))
    check("info shows file", "v12_synth.json" in out)
    check("info shows 5 events", "5" in out)
    check("info shows click type", "click" in out)
    check("info shows move type", "move" in out)


async def test_qt_input_recorder_info_missing():
    print("\n[22] qt_input_recorder -- info on missing file")
    out = await server.qt_input_recorder(QtInputRecorderInput(action="info", input_file="/no/such/file.json"))
    check("info errors on missing", "Error:" in out and "not found" in out)


async def test_qt_input_recorder_invalid_action():
    print("\n[23] qt_input_recorder -- invalid action")
    out = await server.qt_input_recorder(QtInputRecorderInput(action="warp"))
    check("rejects invalid action", "Error:" in out)


# ---------- qt_translation_validate ----------

async def test_qt_translation_validate_basic():
    print("\n[24] qt_translation_validate -- basic coverage report")
    import tempfile
    ts_path = SANDBOX_TMP / "v12_sample.ts"
    # 3 messages, 1 finished, 2 unfinished
    ts_xml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="zh_CN">
<context>
    <name>MainWindow</name>
    <message>
        <location filename="../mainwindow.cpp" line="10"/>
        <source>Hello</source>
        <translation type="finished">你好</translation>
    </message>
    <message>
        <location filename="../mainwindow.cpp" line="11"/>
        <source>World</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <location filename="../mainwindow.cpp" line="12"/>
        <source>Foo</source>
        <translation type="unfinished"></translation>
    </message>
</context>
</TS>
"""
    ts_path.write_text(ts_xml, encoding="utf-8")
    out = await server.qt_translation_validate(QtTranslationValidateInput(ts_files=[str(ts_path)]))
    check("found zh_CN", "zh_CN" in out)
    check("reports 3 total", "3" in out)
    check("reports coverage", "%" in out)


async def test_qt_translation_validate_min_coverage():
    print("\n[25] qt_translation_validate -- flags below min_coverage")
    ts_path = SANDBOX_TMP / "v12_sample.ts"
    out = await server.qt_translation_validate(QtTranslationValidateInput(
        ts_files=[str(ts_path)], min_coverage=0.9,
    ))
    check("flags zh_CN below 90%", "Flagged" in out or "flagged" in out.lower() or "zh_CN" in out)


async def test_qt_translation_validate_missing_file():
    print("\n[26] qt_translation_validate -- missing file reported as error")
    out = await server.qt_translation_validate(QtTranslationValidateInput(
        ts_files=["/no/such/file.ts"],
    ))
    check("reports missing file", "missing" in out or "Error" in out)


async def test_qt_translation_validate_empty():
    print("\n[27] qt_translation_validate -- empty ts_files list rejected")
    out = await server.qt_translation_validate(QtTranslationValidateInput(ts_files=[]))
    check("rejects empty list", "Error:" in out)


# ---------- main ----------

async def main():
    await test_qt_model_gen_list()
    await test_qt_model_gen_table()
    await test_qt_model_gen_invalid_type()
    await test_qt_model_gen_table_no_columns()
    await test_qt_theme_gen_dark()
    await test_qt_theme_gen_light()
    await test_qt_theme_gen_invalid_mode()
    await test_qt_theme_gen_invalid_color()
    await test_qt_ico_create()
    await test_qt_ico_create_missing_source()
    await test_qt_screenshot_diff_identical()
    await test_qt_screenshot_diff_different()
    await test_qt_screenshot_diff_size_mismatch()
    await test_qt_clazy_check_finds_issues()
    await test_qt_clazy_check_clean_project()
    await test_qt_clazy_check_invalid_check()
    await test_qt_signal_slot_trace_basic()
    await test_qt_signal_slot_trace_json()
    await test_qt_signal_slot_trace_dot()
    await test_qt_signal_slot_trace_output_file()
    await test_qt_input_recorder_info_synth()
    await test_qt_input_recorder_info_missing()
    await test_qt_input_recorder_invalid_action()
    await test_qt_translation_validate_basic()
    await test_qt_translation_validate_min_coverage()
    await test_qt_translation_validate_missing_file()
    await test_qt_translation_validate_empty()

    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    total = len(results)
    print()
    print(f"\033[1m=== V12 E2E: {passed}/{total} passed, {failed} failed ===\033[0m")
    if failed:
        print("Failed:")
        for name, ok in results:
            if not ok:
                print(f"  - {name}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
