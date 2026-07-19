"""e2e for v13 new tools (v0.2.8): qt_git_init, qt_installer_gen, qt_qml_component_gen,
qt_db_seed, qt_high_dpi_test, qt_property_browser.

Run: python e2e_new_tools_v13.py
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import server
from server import (
    QtGitInitInput, QtInstallerGenInput, QtQmlComponentGenInput,
    QtDbSeedInput, QtHighDpiTestInput, QtPropertyBrowserInput,
    SANDBOX_TMP, SANDBOX_ROOT,
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
    """Create a fresh directory inside parent, force-removing any prior contents.

    On Windows, `shutil.rmtree(..., ignore_errors=True)` does not always delete
    files inside a `.git` directory (object files are sometimes locked). We fall
    back to `cmd /c rmdir /s /q` which handles this reliably.
    """
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


def fresh_file(parent: Path, name: str) -> Path:
    """Create a fresh file inside parent, force-removing any prior contents."""
    p = parent / name
    if p.exists():
        try:
            p.unlink()
        except OSError:
            pass
    return p


# ---------- qt_git_init ----------

async def test_qt_git_init_happy():
    print("\n[1] qt_git_init -- happy path")
    proj = fresh_dir(SANDBOX_TMP, "v13_git_happy")
    (proj / "main.cpp").write_text("int main(){return 0;}\n")
    out = await server.qt_git_init(QtGitInitInput(
        project_dir=str(proj),
        git_user_name="Test User",
        git_user_email="test@example.com",
        initial_message="v0.2.8 e2e test commit",
    ))
    check("wrote .gitignore", (proj / ".gitignore").exists())
    check(".git directory created", (proj / ".git").exists())
    check("wrote README.md", (proj / "README.md").exists())
    check("output reports steps", "Steps performed" in out)
    check("git config user.name", "git config user.name" in out)
    check("commit SHA present", "Initial commit SHA:" in out)


async def test_qt_git_init_already_repo():
    print("\n[2] qt_git_init -- already a repo (error)")
    proj = fresh_dir(SANDBOX_TMP, "v13_git_dup")
    (proj / ".git").mkdir()  # fake existing repo
    out = await server.qt_git_init(QtGitInitInput(project_dir=str(proj)))
    check("error message", "already a git repo" in out)


async def test_qt_git_init_missing_dir():
    print("\n[3] qt_git_init -- nonexistent project_dir (error)")
    out = await server.qt_git_init(QtGitInitInput(project_dir=str(SANDBOX_TMP / "v13_nonexistent_xyz_dir")))
    check("error: directory not found", "does not exist" in out)


async def test_qt_git_init_outside_sandbox():
    print("\n[4] qt_git_init -- outside sandbox (rejected)")
    out = await server.qt_git_init(QtGitInitInput(project_dir=r"C:\Windows\Temp\v13_fake_proj"))
    check("sandbox rejection", "outside the allowed sandbox" in out)


# ---------- qt_installer_gen ----------

async def test_qt_installer_gen_nsis():
    print("\n[5] qt_installer_gen -- NSIS script")
    out_dir = fresh_dir(SANDBOX_TMP, "v13_inst_nsis")
    fake_exe = fresh_file(SANDBOX_TMP, "v13_fake_app.exe")
    fake_exe.write_bytes(b"MZ\x00\x00")
    out = await server.qt_installer_gen(QtInstallerGenInput(
        output_dir=str(out_dir),
        exe_path=str(fake_exe),
        app_name="MyGame",
        app_version="2.0.0",
        installer_type="nsis",
        vendor="Acme Games",
    ))
    check("wrote MyGame.nsi", (out_dir / "MyGame.nsi").exists())
    check("wrote build_installer.bat", (out_dir / "build_installer.bat").exists())
    check("script references makensis", "makensis" in (out_dir / "build_installer.bat").read_text())
    check("vendor in NSIS script", "Acme Games" in (out_dir / "MyGame.nsi").read_text())


async def test_qt_installer_gen_inno():
    print("\n[6] qt_installer_gen -- Inno Setup script")
    out_dir = fresh_dir(SANDBOX_TMP, "v13_inst_inno")
    fake_exe = fresh_file(SANDBOX_TMP, "v13_fake_app2.exe")
    fake_exe.write_bytes(b"MZ\x00\x00")
    out = await server.qt_installer_gen(QtInstallerGenInput(
        output_dir=str(out_dir),
        exe_path=str(fake_exe),
        app_name="OtherGame",
        installer_type="inno",
    ))
    check("wrote OtherGame.iss", (out_dir / "OtherGame.iss").exists())
    check("iss uses iscc", "iscc" in (out_dir / "build_installer.bat").read_text())


async def test_qt_installer_gen_bad_type():
    print("\n[7] qt_installer_gen -- invalid installer_type (error)")
    out_dir = fresh_dir(SANDBOX_TMP, "v13_inst_bad")
    fake_exe = fresh_file(SANDBOX_TMP, "v13_fake3.exe")
    fake_exe.write_bytes(b"MZ")
    out = await server.qt_installer_gen(QtInstallerGenInput(
        output_dir=str(out_dir),
        exe_path=str(fake_exe),
        app_name="X",
        installer_type="wix",  # not supported
    ))
    check("error: installer_type invalid", "must be 'nsis' or 'inno'" in out)


async def test_qt_installer_gen_missing_exe():
    print("\n[8] qt_installer_gen -- missing exe (error)")
    out_dir = fresh_dir(SANDBOX_TMP, "v13_inst_noexe")
    out = await server.qt_installer_gen(QtInstallerGenInput(
        output_dir=str(out_dir),
        exe_path=str(SANDBOX_TMP / "v13_nonexistent_xyz.exe"),
        app_name="Y",
    ))
    check("error: exe not found", "not found" in out)


# ---------- qt_qml_component_gen ----------

async def test_qt_qml_component_gen_single():
    print("\n[9] qt_qml_component_gen -- single component")
    out_dir = fresh_dir(SANDBOX_TMP, "v13_qml_single")
    out = await server.qt_qml_component_gen(QtQmlComponentGenInput(
        output_dir=str(out_dir),
        components=["card"],
        theme="dark",
    ))
    check("wrote Card.qml", (out_dir / "Card.qml").exists())
    check("wrote qmldir", (out_dir / "qmldir").exists())
    qmldir_text = (out_dir / "qmldir").read_text()
    check("qmldir has module line", qmldir_text.startswith("module "))


async def test_qt_qml_component_gen_all_six():
    print("\n[10] qt_qml_component_gen -- all 6 components")
    out_dir = fresh_dir(SANDBOX_TMP, "v13_qml_all")
    out = await server.qt_qml_component_gen(QtQmlComponentGenInput(
        output_dir=str(out_dir),
        components=["card", "board", "player", "hand", "deck", "tile"],
        theme="light",
    ))
    for c in ["Card", "Board", "Player", "Hand", "Deck", "Tile"]:
        check(f"wrote {c}.qml", (out_dir / f"{c}.qml").exists())
    qml_count = len(list(out_dir.glob("*.qml")))
    check("6 .qml files", qml_count == 6)


async def test_qt_qml_component_gen_unknown():
    print("\n[11] qt_qml_component_gen -- unknown component name (error)")
    out_dir = fresh_dir(SANDBOX_TMP, "v13_qml_bad")
    out = await server.qt_qml_component_gen(QtQmlComponentGenInput(
        output_dir=str(out_dir),
        components=["card", "banana"],  # banana doesn't exist
    ))
    check("error: unknown component", "unknown component" in out)
    check("lists available", "card" in out and "board" in out)


async def test_qt_qml_component_gen_empty_list():
    print("\n[12] qt_qml_component_gen -- empty list (error)")
    out = await server.qt_qml_component_gen(QtQmlComponentGenInput(
        output_dir=str(SANDBOX_TMP / "v13_qml_empty"),
        components=[],
    ))
    check("error: empty list", "is empty" in out)


# ---------- qt_db_seed ----------

async def test_qt_db_seed_single_table():
    print("\n[13] qt_db_seed -- single table, no seed")
    db_path = fresh_file(SANDBOX_TMP, "v13_db1.db")
    out = await server.qt_db_seed(QtDbSeedInput(
        db_path=str(db_path),
        tables=[{
            "name": "users",
            "columns": [
                {"name": "id", "type": "INTEGER", "pk": True},
                {"name": "email", "type": "TEXT", "not_null": True},
                {"name": "age", "type": "INTEGER"},
            ],
        }],
    ))
    check("db created", db_path.exists())
    check("examples.py written", (SANDBOX_TMP / "v13_db1_examples.py").exists())
    check("output reports table created", "users" in out)
    # Verify schema via sqlite3
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    conn.close()
    check("schema: 'users' table exists", "users" in tables)


async def test_qt_db_seed_with_seed_data():
    print("\n[14] qt_db_seed -- multi-table + seed data")
    db_path = fresh_file(SANDBOX_TMP, "v13_db2.db")
    out = await server.qt_db_seed(QtDbSeedInput(
        db_path=str(db_path),
        tables=[
            {"name": "players", "columns": [
                {"name": "id", "type": "INTEGER", "pk": True},
                {"name": "name", "type": "TEXT", "not_null": True},
                {"name": "score", "type": "INTEGER", "default": 0},
            ]},
            {"name": "games", "columns": [
                {"name": "id", "type": "INTEGER", "pk": True},
                {"name": "winner", "type": "TEXT"},
            ]},
        ],
        seed_data={
            "players": [
                {"name": "Alice", "score": 100},
                {"name": "Bob", "score": 50},
                {"name": "Carol", "score": 75},
            ],
        },
    ))
    check("db created", db_path.exists())
    check("seed inserted reported", "Seed rows: 3 inserted" in out)
    # Verify rows
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT name, score FROM players ORDER BY score DESC")
    rows = cur.fetchall()
    conn.close()
    check("Alice has score 100", rows[0] == ("Alice", 100))
    check("Bob has score 50", rows[-1] == ("Bob", 50))


async def test_qt_db_seed_already_exists():
    print("\n[15] qt_db_seed -- db already exists (error)")
    db_path = fresh_file(SANDBOX_TMP, "v13_db3.db")
    db_path.write_bytes(b"")  # touch the file
    out = await server.qt_db_seed(QtDbSeedInput(
        db_path=str(db_path),
        tables=[{"name": "x", "columns": [{"name": "id", "type": "INTEGER", "pk": True}]}],
    ))
    check("error: already exists", "already exists" in out)


async def test_qt_db_seed_empty_tables():
    print("\n[16] qt_db_seed -- empty tables list (error)")
    db_path = fresh_file(SANDBOX_TMP, "v13_db4.db")
    out = await server.qt_db_seed(QtDbSeedInput(
        db_path=str(db_path),
        tables=[],
    ))
    check("error: tables empty", "tables is empty" in out)


# ---------- qt_high_dpi_test ----------

async def test_qt_high_dpi_test_missing_exe():
    print("\n[17] qt_high_dpi_test -- missing exe (error)")
    out = await server.qt_high_dpi_test(QtHighDpiTestInput(
        executable=str(SANDBOX_TMP / "v13_no_exe.exe"),
        scale_factors=[1.0],
        screenshot_dir=str(SANDBOX_TMP / "v13_shots1"),
    ))
    check("error: executable not found", "not found" in out)


async def test_qt_high_dpi_test_empty_factors():
    print("\n[18] qt_high_dpi_test -- empty scale_factors (error)")
    out = await server.qt_high_dpi_test(QtHighDpiTestInput(
        executable=str(SANDBOX_TMP / "v13_never.exe"),
        scale_factors=[],
        screenshot_dir=str(SANDBOX_TMP / "v13_shots2"),
    ))
    check("error: empty scale_factors", "scale_factors is empty" in out)


async def test_qt_high_dpi_test_baseline_no_dir():
    print("\n[19] qt_high_dpi_test -- compare_with_baseline but no dir (error)")
    out = await server.qt_high_dpi_test(QtHighDpiTestInput(
        executable=str(SANDBOX_TMP / "v13_never.exe"),
        scale_factors=[1.0],
        screenshot_dir=str(SANDBOX_TMP / "v13_shots3"),
        compare_with_baseline=True,
        baseline_dir="",
    ))
    check("error: baseline_dir required", "baseline_dir is required" in out)


# ---------- qt_property_browser ----------

async def test_qt_property_browser_markdown():
    print("\n[20] qt_property_browser -- markdown format")
    h_file = fresh_file(SANDBOX_TMP, "v13_widget1.h")
    h_file.write_text("""
#include <QObject>
class MyWidget : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString name READ name WRITE setName NOTIFY nameChanged)
    Q_PROPERTY(int count READ count WRITE setCount NOTIFY countChanged)
    Q_PROPERTY(bool enabled READ enabled CONSTANT)
public:
    QString name() const;
    void setName(const QString&);
    int count() const;
    void setCount(int);
    bool enabled() const;
signals:
    void nameChanged();
    void countChanged();
};
""")
    out = await server.qt_property_browser(QtPropertyBrowserInput(header=str(h_file), output_format="markdown"))
    check("renders as markdown table", "| Name |" in out)
    check("contains 'name' property", "name" in out)
    check("contains 'count' property", "count" in out)
    check("contains 'enabled' CONSTANT", "enabled" in out and "CONSTANT" in out)


async def test_qt_property_browser_json():
    print("\n[21] qt_property_browser -- json format")
    h_file = fresh_file(SANDBOX_TMP, "v13_widget2.h")
    h_file.write_text("""
class Foo : public QObject {
    Q_OBJECT
    Q_PROPERTY(int x READ x WRITE setX NOTIFY xChanged)
public:
    int x() const;
    void setX(int);
signals:
    void xChanged();
};
""")
    out = await server.qt_property_browser(QtPropertyBrowserInput(header=str(h_file), output_format="json"))
    # Strip footer to get pure JSON. _json_footer emits `--- json ---` separator;
    # use that marker (not just `---`) so we don't split on stray `--` chars.
    json_part = out.split("--- json ---", 1)[0].strip()
    j = json.loads(json_part)
    check("json parsed", isinstance(j, dict))
    check("count == 1", j["count"] == 1)
    check("properties[0].name == x", j["properties"][0]["name"] == "x")
    check("properties[0].type == int", j["properties"][0]["type"] == "int")
    check("properties[0].READ == x", j["properties"][0].get("READ") == "x")
    check("properties[0].NOTIFY == xChanged", j["properties"][0].get("NOTIFY") == "xChanged")


async def test_qt_property_browser_html():
    print("\n[22] qt_property_browser -- html format")
    h_file = fresh_file(SANDBOX_TMP, "v13_widget3.h")
    h_file.write_text("class W:QObject{Q_OBJECT Q_PROPERTY(double v READ v CONSTANT) public:double v()const;};")
    out = await server.qt_property_browser(QtPropertyBrowserInput(header=str(h_file), output_format="html"))
    check("renders as HTML", "<table" in out)
    check("contains <th>Name</th>", "<th>Name</th>" in out)
    check("contains <td>v</td>", "<td>v</td>" in out)


async def test_qt_property_browser_no_properties():
    print("\n[23] qt_property_browser -- no Q_PROPERTY")
    h_file = fresh_file(SANDBOX_TMP, "v13_widget4.h")
    h_file.write_text("class Empty : public QObject { Q_OBJECT public: int x() const; };")
    out = await server.qt_property_browser(QtPropertyBrowserInput(header=str(h_file), output_format="markdown"))
    check("reports no properties", "no Q_PROPERTY found" in out)


async def test_qt_property_browser_missing_file():
    print("\n[24] qt_property_browser -- missing file (error)")
    out = await server.qt_property_browser(QtPropertyBrowserInput(
        header=str(SANDBOX_TMP / "v13_nonexistent.h"),
    ))
    check("error: header not found", "not found" in out)


async def test_qt_property_browser_output_file():
    print("\n[25] qt_property_browser -- write to output_file")
    h_file = fresh_file(SANDBOX_TMP, "v13_widget5.h")
    h_file.write_text("class W:QObject{Q_OBJECT Q_PROPERTY(int a READ a CONSTANT) public:int a()const;};")
    out_file = fresh_file(SANDBOX_TMP, "v13_props.md")
    out = await server.qt_property_browser(QtPropertyBrowserInput(
        header=str(h_file),
        output_format="markdown",
        output_file=str(out_file),
    ))
    check("output_file written", out_file.exists())
    check("report confirms write", "wrote" in out.lower())


# ---------- entry point ----------

async def main() -> int:
    print("=== e2e_new_tools_v13: v0.2.8 new tools ===")
    await test_qt_git_init_happy()
    await test_qt_git_init_already_repo()
    await test_qt_git_init_missing_dir()
    await test_qt_git_init_outside_sandbox()
    await test_qt_installer_gen_nsis()
    await test_qt_installer_gen_inno()
    await test_qt_installer_gen_bad_type()
    await test_qt_installer_gen_missing_exe()
    await test_qt_qml_component_gen_single()
    await test_qt_qml_component_gen_all_six()
    await test_qt_qml_component_gen_unknown()
    await test_qt_qml_component_gen_empty_list()
    await test_qt_db_seed_single_table()
    await test_qt_db_seed_with_seed_data()
    await test_qt_db_seed_already_exists()
    await test_qt_db_seed_empty_tables()
    await test_qt_high_dpi_test_missing_exe()
    await test_qt_high_dpi_test_empty_factors()
    await test_qt_high_dpi_test_baseline_no_dir()
    await test_qt_property_browser_markdown()
    await test_qt_property_browser_json()
    await test_qt_property_browser_html()
    await test_qt_property_browser_no_properties()
    await test_qt_property_browser_missing_file()
    await test_qt_property_browser_output_file()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\n=== {passed}/{total} passed ===")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))