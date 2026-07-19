"""e2e for v24 new tools (v0.3.8):

NEW TOOLS (7):
  - qt_cpp_tutorial_scaffold    (SCU C++ 强化 9 章 — 12 topic .cpp)
  - qt_mysql_setup              (MySQL/MariaDB starter project — qmake or cmake)
  - qt_http_client_gen          (QNetworkAccessManager HTTP client — async or sync)
  - qt_ftp_client_gen           (QNetworkAccessManager FTP client — upload/download/list)
  - qt_graphics_view_scaffold   (QGraphicsScene + View + 3 items + drag)
  - qt_multimedia_setup         (QMediaPlayer + QSoundEffect + QVideoWidget + .qrc)
  - qt_qstyle_sheet_gen         (QSS for 14 widget selectors — light or dark)

ENHANCEMENTS (3):
  - qt_scaffold   +4 templates (tictactoe_game / breakout_game / tasklist / music_player)
  - qt_db_seed    +mysql_check parameter (MySQL driver compatibility report)
  - qt_anim       +3 animation_types (double_buffer / painter_path / doodle_board)

Run: python e2e_new_tools_v24.py
"""

import asyncio
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import server
from server import (
    SANDBOX_TMP,
    QtScaffoldInput,
    QtDbSeedInput,
    QtAnimInput,
    QtCppTutorialScaffoldInput,
    QtMysqlSetupInput,
    QtHttpClientGenInput,
    QtFtpClientGenInput,
    QtGraphicsViewScaffoldInput,
    QtMultimediaSetupInput,
    QtQstyleSheetGenInput,
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
            subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(p)], check=False, capture_output=True, timeout=10)
        except Exception:
            pass
        shutil.rmtree(p, ignore_errors=True)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ============ ENHANCEMENTS ============

async def test_scaffold_4_new_templates():
    print("\n[1] qt_scaffold -- 4 new templates (tictactoe/breakout/tasklist/music_player)")
    for name, tpl, marker in [
        ("tictactoe", "tictactoe_game", "checkWinner"),
        ("breakout", "breakout_game", "QTimer"),
        ("tasklist", "tasklist", "QListView"),
        ("musicplayer", "music_player", "QMediaPlayer"),
    ]:
        d = fresh_dir(SANDBOX_TMP, f"v24_scaffold_{name}")
        out = await server.qt_scaffold(QtScaffoldInput(name=name, template=tpl, output_dir=str(d)))
        cpp_text = (d / f"{name}window.cpp").read_text(encoding="utf-8")
        check(f"{tpl} creates {name}window.cpp with {marker}", marker in cpp_text)


async def test_db_seed_mysql_check():
    print("\n[2] qt_db_seed -- mysql_check reports MySQL driver compat")
    d = fresh_dir(SANDBOX_TMP, "v24_dbseed_mysql")
    db = d / "test.db"
    if db.exists():
        db.unlink()
    out = await server.qt_db_seed(QtDbSeedInput(
        db_path=str(db),
        tables=[{"name": "t", "columns": [{"name": "id", "type": "INTEGER", "pk": True}]}],
        mysql_check=True,
    ))
    check("mysql_check appends MySQL report", "MySQL/QMYSQL driver compatibility" in out)
    check("reports libmysql.dll status", "libmysql.dll" in out)
    check("includes setup guidance", "enable MySQL support" in out)


async def test_anim_3_new_types():
    print("\n[3] qt_anim -- 3 new animation types (double_buffer/painter_path/doodle_board)")
    for at, marker in [
        ("double_buffer", "QPixmap"),
        ("painter_path", "QPainterPath"),
        ("doodle_board", "mouseMoveEvent"),
    ]:
        out = await server.qt_anim(QtAnimAnimInput := QtAnimInput(
            animation_type=at,
            end_value="dummy",
        ))
        check(f"{at} returns {marker} snippet", marker in out)


# ============ NEW TOOLS ============

async def test_cpp_tutorial_scaffold_hello():
    print("\n[4] qt_cpp_tutorial_scaffold -- hello_world topic")
    d = fresh_dir(SANDBOX_TMP, "v24_cpp_hello")
    out = await server.qt_cpp_tutorial_scaffold(QtCppTutorialScaffoldInput(
        topic="hello_world",
        output_dir=str(d),
    ))
    check("writes .cpp file", (d / "hello_world.cpp").exists())
    cpp_text = (d / "hello_world.cpp").read_text(encoding="utf-8")
    check("cpp has Hello World", "Hello, World!" in cpp_text or "hello world" in cpp_text.lower())
    check("cpp has iostream", "#include <iostream>" in cpp_text)


async def test_cpp_tutorial_scaffold_polymorphism():
    print("\n[5] qt_cpp_tutorial_scaffold -- polymorphism (advanced topic)")
    d = fresh_dir(SANDBOX_TMP, "v24_cpp_poly")
    out = await server.qt_cpp_tutorial_scaffold(QtCppTutorialScaffoldInput(
        topic="polymorphism",
        output_dir=str(d),
    ))
    cpp_text = (d / "polymorphism.cpp").read_text(encoding="utf-8")
    check("has virtual function", "virtual" in cpp_text)
    check("has override", "override" in cpp_text)


async def test_cpp_tutorial_scaffold_bad_topic():
    print("\n[6] qt_cpp_tutorial_scaffold -- bad topic rejected")
    out = await server.qt_cpp_tutorial_scaffold(QtCppTutorialScaffoldInput(
        topic="nonexistent",
        output_dir=str(SANDBOX_TMP / "v24_cpp_bad"),
    ))
    check("rejects unknown topic", "Error" in out and "unknown topic" in out)


async def test_mysql_setup_qmake():
    print("\n[7] qt_mysql_setup -- qmake mode")
    d = fresh_dir(SANDBOX_TMP, "v24_mysql_qmake")
    out = await server.qt_mysql_setup(QtMysqlSetupInput(
        output_dir=str(d),
        build_system="qmake",
    ))
    check("writes mysqlapp.pro", (d / "mysqlapp.pro").exists())
    check("writes dbmanager.h", (d / "dbmanager.h").exists())
    check("writes dbmanager.cpp", (d / "dbmanager.cpp").exists())
    check("writes main.cpp", (d / "main.cpp").exists())
    check("writes MySQL_SETUP.md", (d / "MySQL_SETUP.md").exists())
    pro_text = (d / "mysqlapp.pro").read_text(encoding="utf-8")
    check(".pro has sql module", "sql" in pro_text)
    cpp_text = (d / "dbmanager.cpp").read_text(encoding="utf-8")
    check("dbmanager uses QMYSQL", "QMYSQL" in cpp_text)


async def test_mysql_setup_cmake():
    print("\n[8] qt_mysql_setup -- cmake mode")
    d = fresh_dir(SANDBOX_TMP, "v24_mysql_cmake")
    out = await server.qt_mysql_setup(QtMysqlSetupInput(
        output_dir=str(d),
        build_system="cmake",
    ))
    check("writes CMakeLists.txt", (d / "CMakeLists.txt").exists())
    cm_text = (d / "CMakeLists.txt").read_text(encoding="utf-8")
    check("CMake has find_package Qt5 Sql", "Qt5" in cm_text and "Sql" in cm_text)


async def test_mysql_setup_bad_build_system():
    print("\n[9] qt_mysql_setup -- bad build_system rejected")
    out = await server.qt_mysql_setup(QtMysqlSetupInput(
        output_dir=str(SANDBOX_TMP / "v24_mysql_bad"),
        build_system="make",
    ))
    check("rejects bad build_system", "Error" in out and "qmake|cmake" in out)


async def test_http_client_gen_async_get():
    print("\n[10] qt_http_client_gen -- async + GET")
    d = fresh_dir(SANDBOX_TMP, "v24_http_async")
    out = await server.qt_http_client_gen(QtHttpClientGenInput(
        class_name="HttpClient",
        output_dir=str(d),
        method="GET",
        response_mode="async",
        build_system="qmake",
    ))
    check("writes httpclient.h", (d / "httpclient.h").exists())
    check("writes httpclient.cpp", (d / "httpclient.cpp").exists())
    check("writes main.cpp", (d / "main.cpp").exists())
    check("writes httpclient.pro", (d / "httpclient.pro").exists())
    h_text = (d / "httpclient.h").read_text(encoding="utf-8")
    check(".h has getFinished signal (async)", "getFinished" in h_text)
    cpp_text = (d / "httpclient.cpp").read_text(encoding="utf-8")
    check(".cpp uses QNetworkAccessManager", "QNetworkAccessManager" in cpp_text)


async def test_http_client_gen_sync_post():
    print("\n[11] qt_http_client_gen -- sync + POST")
    d = fresh_dir(SANDBOX_TMP, "v24_http_sync")
    out = await server.qt_http_client_gen(QtHttpClientGenInput(
        class_name="ApiClient",
        output_dir=str(d),
        method="POST",
        response_mode="sync",
    ))
    check("sync mode writes ApiClient", (d / "apiclient.h").exists())
    cpp_text = (d / "apiclient.cpp").read_text(encoding="utf-8")
    check("sync mode uses QEventLoop", "QEventLoop" in cpp_text)
    check("POST uses ContentType", "ContentType" in cpp_text or "Content-Type" in cpp_text)


async def test_ftp_client_gen_upload():
    print("\n[12] qt_ftp_client_gen -- upload operation")
    d = fresh_dir(SANDBOX_TMP, "v24_ftp_upload")
    out = await server.qt_ftp_client_gen(QtFtpClientGenInput(
        class_name="FtpClient",
        output_dir=str(d),
        operation="upload",
    ))
    check("writes ftpclient.h", (d / "ftpclient.h").exists())
    check("writes ftpclient.cpp", (d / "ftpclient.cpp").exists())
    cpp_text = (d / "ftpclient.cpp").read_text(encoding="utf-8")
    check("upload uses put()", "->put(" in cpp_text)
    check("upload progress signal", "uploadProgress" in cpp_text)


async def test_ftp_client_gen_list():
    print("\n[13] qt_ftp_client_gen -- list operation")
    d = fresh_dir(SANDBOX_TMP, "v24_ftp_list")
    out = await server.qt_ftp_client_gen(QtFtpClientGenInput(
        class_name="FtpClient",
        output_dir=str(d),
        operation="list",
    ))
    cpp_text = (d / "ftpclient.cpp").read_text(encoding="utf-8")
    check("list uses get()", "->get(" in cpp_text)
    check("list emits dirListing", "dirListing" in cpp_text)


async def test_graphics_view_scaffold():
    print("\n[14] qt_graphics_view_scaffold -- generates scene + view + drag")
    d = fresh_dir(SANDBOX_TMP, "v24_gv_scaffold")
    out = await server.qt_graphics_view_scaffold(QtGraphicsViewScaffoldInput(
        name="graphicsview",
        output_dir=str(d),
    ))
    check("writes graphicsviewwindow.h", (d / "graphicsviewwindow.h").exists())
    check("writes graphicsviewwindow.cpp", (d / "graphicsviewwindow.cpp").exists())
    check("writes graphicsview.pro", (d / "graphicsview.pro").exists())
    h_text = (d / "graphicsviewwindow.h").read_text(encoding="utf-8")
    check(".h has QGraphicsScene", "QGraphicsScene" in h_text)
    check(".h has QGraphicsView", "QGraphicsView" in h_text)
    check(".h has mousePressEvent", "mousePressEvent" in h_text)
    cpp_text = (d / "graphicsviewwindow.cpp").read_text(encoding="utf-8")
    check(".cpp adds Rect item", "addRect" in cpp_text)
    check(".cpp adds Ellipse item", "addEllipse" in cpp_text)


async def test_multimedia_setup():
    print("\n[15] qt_multimedia_setup -- generates main.cpp + pro + qrc + setup md")
    d = fresh_dir(SANDBOX_TMP, "v24_mm_setup")
    out = await server.qt_multimedia_setup(QtMultimediaSetupInput(output_dir=str(d)))
    check("writes main.cpp", (d / "main.cpp").exists())
    check("writes mediademo.pro", (d / "mediademo.pro").exists())
    check("writes sounds.qrc", (d / "sounds.qrc").exists())
    check("writes MULTIMEDIA_SETUP.md", (d / "MULTIMEDIA_SETUP.md").exists())
    check("sounds/click.wav created", (d / "sounds" / "click.wav").exists())
    pro_text = (d / "mediademo.pro").read_text(encoding="utf-8")
    check(".pro has multimedia module", "multimedia" in pro_text)
    cpp_text = (d / "main.cpp").read_text(encoding="utf-8")
    check("main.cpp uses QMediaPlayer", "QMediaPlayer" in cpp_text)
    check("main.cpp uses QSoundEffect", "QSoundEffect" in cpp_text)


async def test_qstyle_sheet_gen_light():
    print("\n[16] qt_qstyle_sheet_gen -- light theme with 3 selectors")
    d = fresh_dir(SANDBOX_TMP, "v24_qss_light")
    out_path = d / "style.qss"
    out = await server.qt_qstyle_sheet_gen(QtQstyleSheetGenInput(
        selectors=["QPushButton", "QLineEdit", "QListView"],
        output_path=str(out_path),
        theme="light",
    ))
    check("writes .qss file", out_path.exists())
    qss_text = out_path.read_text(encoding="utf-8")
    check("QSS has QPushButton", "QPushButton" in qss_text)
    check("QSS has QLineEdit", "QLineEdit" in qss_text)
    check("QSS has QListView", "QListView" in qss_text)
    check("light theme uses blue accent", "#4A90E2" in qss_text)


async def test_qstyle_sheet_gen_dark():
    print("\n[17] qt_qstyle_sheet_gen -- dark theme override")
    d = fresh_dir(SANDBOX_TMP, "v24_qss_dark")
    out_path = d / "dark.qss"
    out = await server.qt_qstyle_sheet_gen(QtQstyleSheetGenInput(
        selectors=["QPushButton", "QLineEdit", "QListView"],
        output_path=str(out_path),
        theme="dark",
    ))
    qss_text = out_path.read_text(encoding="utf-8")
    check("dark theme uses dark blue", "#2A6FBC" in qss_text)
    check("dark theme has QListView with dark bg", "#1E1E1E" in qss_text)


async def test_qstyle_sheet_gen_bad_selector():
    print("\n[18] qt_qstyle_sheet_gen -- bad selector rejected")
    out = await server.qt_qstyle_sheet_gen(QtQstyleSheetGenInput(
        selectors=["QPushButton", "QNonexistent"],
        output_path=str(SANDBOX_TMP / "v24_qss_bad" / "x.qss"),
    ))
    check("rejects unknown selector", "Error" in out and "unknown selector" in out)


async def test_qstyle_sheet_gen_empty():
    print("\n[19] qt_qstyle_sheet_gen -- empty selectors rejected")
    out = await server.qt_qstyle_sheet_gen(QtQstyleSheetGenInput(
        selectors=[],
        output_path=str(SANDBOX_TMP / "v24_qss_empty" / "x.qss"),
    ))
    check("rejects empty selectors", "Error" in out and "empty" in out)


# ============ runner ============

async def main():
    tests = [
        test_scaffold_4_new_templates,
        test_db_seed_mysql_check,
        test_anim_3_new_types,
        test_cpp_tutorial_scaffold_hello,
        test_cpp_tutorial_scaffold_polymorphism,
        test_cpp_tutorial_scaffold_bad_topic,
        test_mysql_setup_qmake,
        test_mysql_setup_cmake,
        test_mysql_setup_bad_build_system,
        test_http_client_gen_async_get,
        test_http_client_gen_sync_post,
        test_ftp_client_gen_upload,
        test_ftp_client_gen_list,
        test_graphics_view_scaffold,
        test_multimedia_setup,
        test_qstyle_sheet_gen_light,
        test_qstyle_sheet_gen_dark,
        test_qstyle_sheet_gen_bad_selector,
        test_qstyle_sheet_gen_empty,
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
