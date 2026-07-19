"""e2e tests for the 3 tools added after the Jul 8 session:
  - qt_docs_search  (FTS5 over Tools/qt-mcp/docs_data/qt_5_14_2_docs.db)
  - qt_grep         (regex search across .h/.cpp/.ui/.qrc)
  - qt_class_wizard (generate .h/.cpp/.ui trio + verify it actually compiles)

Each test calls the underlying async function directly (no MCP round-trip).
That keeps the test fast and deterministic.

Run from anywhere:
    python e2e_new_tools_v2.py
"""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
import uuid
from pathlib import Path

# Make sibling server.py importable regardless of cwd.
HERE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(HERE))

import server  # noqa: E402


# The MCP sandbox rejects paths outside E:\Download_tools\QT, so tests that
# write temp files must put them under SANDBOX_TMP (E:\Download_tools\QT\.tmp).
SANDBOX_TMP = Path(r"E:\Download_tools\QT\.tmp")


def _sandbox_tmpdir(prefix: str) -> Path:
    d = SANDBOX_TMP / f"{prefix}_{uuid.uuid4().hex[:8]}"
    d.mkdir(parents=True, exist_ok=False)
    return d


GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


def check(label: str, ok: bool, detail: str = "") -> None:
    mark = f"{GREEN}OK{RESET}" if ok else f"{RED}FAIL{RESET}"
    print(f"  [{mark}] {label}" + (f" -- {detail}" if detail else ""))
    if not ok:
        raise AssertionError(label)


async def test_docs_search_basic():
    print("\n[1] qt_docs_search -- basic single-term query")
    inp = server.QtDocsSearchInput(query="QPushButton", module="qtwidgets", limit=5)
    out = await server.qt_docs_search(inp)
    check("returns output", isinstance(out, str) and len(out) > 100)
    check("mentions QPushButton class page", "QPushButton Class" in out)
    check("module filter respected (only qtwidgets)", "qtwidgets" in out)
    check("no other modules leak in", "qtcore" not in out and "qtquick" not in out)


async def test_docs_search_fts5_syntax():
    print("\n[2] qt_docs_search -- FTS5 AND / NOT / phrase")
    inp = server.QtDocsSearchInput(query="QPushButton AND click", limit=3)
    out = await server.qt_docs_search(inp)
    check("AND query works", "Found" in out and "QPushButton" in out)

    inp = server.QtDocsSearchInput(query='"signal slot"', limit=3)
    out = await server.qt_docs_search(inp)
    check("phrase query works", "Found" in out)


async def test_docs_search_bad_inputs():
    print("\n[3] qt_docs_search -- bad inputs give helpful errors")
    inp = server.QtDocsSearchInput(query="QPushButton AND")  # dangling operator
    out = await server.qt_docs_search(inp)
    check("dangling AND rejected with hint", "FTS5 rejected" in out and "reminders" in out)

    inp = server.QtDocsSearchInput(query="nonsense_xyz_no_match", limit=5)
    out = await server.qt_docs_search(inp)
    check("no-results message is friendly", "No results" in out and "Try" in out)

    inp = server.QtDocsSearchInput(query="QPushButton", module="../../../etc")
    out = await server.qt_docs_search(inp)
    check("bad module name rejected", "invalid module" in out.lower())


async def test_grep_finds_known_symbols():
    print("\n[4] qt_grep -- finds known C++ symbols in counter project")
    inp = server.QtGrepInput(
        project_dir=r"E:\Download_tools\QT\Files\qt_mcp_demo\counter",
        pattern="QTimer",
        max_results=20,
    )
    out = await server.qt_grep(inp)
    check("finds QTimer matches", "counter.h:" in out)
    check("finds connect() call", "QTimer::timeout" in out)
    check("lists file:line: format", "counter.h:5:" in out)
    check("no false hits in .o/.obj files", ".o:" not in out and ".obj:" not in out)


async def test_grep_respects_globs_and_case():
    print("\n[5] qt_grep -- globs and case sensitivity")
    inp = server.QtGrepInput(
        project_dir=r"E:\Download_tools\QT\Files\qt_mcp_demo\counter",
        pattern="setupUi",
        file_glob="*.cpp",
        case_sensitive=False,
        max_results=50,
    )
    out = await server.qt_grep(inp)
    check("hits .cpp only (no .ui)", ".cpp:" in out)
    check("no .ui hits", ".ui:" not in out)

    inp = server.QtGrepInput(
        project_dir=r"E:\Download_tools\QT\Files\qt_mcp_demo\counter",
        pattern="SETUPI",  # uppercase, case-sensitive
        case_sensitive=True,
        max_results=50,
    )
    out = await server.qt_grep(inp)
    check("case-sensitive search excludes wrong case", "No matches" in out)


async def test_grep_skips_build_dirs():
    print("\n[6] qt_grep -- skips build-* / debug / release dirs")
    inp = server.QtGrepInput(
        project_dir=r"E:\Download_tools\QT\Files\qt_mcp_demo\counter",
        pattern="QApplication",
        max_results=20,
    )
    out = await server.qt_grep(inp)
    check("main.cpp hit included", "main.cpp:" in out)
    check("no debug/ or release/ leaks", "debug/" not in out and "release/" not in out)


async def test_grep_bad_inputs():
    print("\n[7] qt_grep -- bad inputs give helpful errors")
    inp = server.QtGrepInput(
        project_dir=r"E:\Download_tools\QT\Files\qt_mcp_demo\counter\counter.pro",
        pattern="foo",
    )
    out = await server.qt_grep(inp)
    check("non-directory rejected", "not a directory" in out.lower())

    inp = server.QtGrepInput(
        project_dir=r"D:\outside\something",
        pattern="foo",
    )
    out = await server.qt_grep(inp)
    check("outside-sandbox rejected", "outside the allowed sandbox" in out)

    inp = server.QtGrepInput(
        project_dir=r"E:\Download_tools\QT\Files\qt_mcp_demo\counter",
        pattern="[unclosed",
    )
    out = await server.qt_grep(inp)
    check("bad regex rejected", "bad regex" in out)


async def test_class_wizard_generates_and_compiles():
    print("\n[8] qt_class_wizard -- generates a working class and compiles it")
    tmp = _sandbox_tmpdir("qt_wizard")
    try:
        inp = server.QtClassWizardInput(
            output_dir=str(tmp),
            class_name="WizardProbe",
            base_class="QWidget",
            has_ui=True,
            header_extra=(
                "    Q_PROPERTY(int counter READ counter WRITE setCounter NOTIFY counterChanged)\n"
                "public:\n"
                "    int counter() const { return m_counter; }\n"
                "public slots:\n"
                "    void setCounter(int v);\n"
                "signals:\n"
                "    void counterChanged(int v);\n"
                "private:\n"
                "    int m_counter = 0;"
            ),
            source_extra="    setCounter(0);",
        )
        out = await server.qt_class_wizard(inp)
        check("success message",
              "Generated WizardProbe" in out or "Generated wizardprobe" in out,
              f"got: {out[:120]!r}")
        for fn in ("wizardprobe.h", "wizardprobe.cpp", "wizardprobe.ui"):
            check(f"{fn} exists", (tmp / fn).is_file())

        # Verify it actually compiles via moc + uic + g++.
        qt_root = Path(r"E:\Download_tools\QT\5.14.2\mingw73_64")
        qt_inc = qt_root / "include"
        mingw = Path(r"E:\Download_tools\QT\Tools\mingw730_64\bin")
        moc = qt_root / "bin" / "moc.exe"
        uic = qt_root / "bin" / "uic.exe"
        gpp = mingw / "g++.exe"

        if not all(p.exists() for p in (moc, uic, gpp)):
            print(f"  [{RED}SKIP{RESET}] moc/uic/g++ not on disk -- skipping compile check")
            return

        import subprocess
        env = dict(os.environ)
        env["PATH"] = f"{qt_root / 'bin'};{mingw};{env.get('PATH', '')}"

        r = subprocess.run(
            [str(moc), "-I", str(tmp), "wizardprobe.h", "-o", "moc_wizardprobe.cpp"],
            cwd=tmp, capture_output=True, text=True, env=env,
        )
        check("moc exit 0", r.returncode == 0, r.stderr[:200] if r.returncode else "")

        r = subprocess.run(
            [str(uic), "wizardprobe.ui", "-o", "ui_wizardprobe.h"],
            cwd=tmp, capture_output=True, text=True, env=env,
        )
        check("uic exit 0", r.returncode == 0, r.stderr[:200] if r.returncode else "")

        r = subprocess.run(
            [
                str(gpp), "-c", "-O0", "-fno-exceptions",
                "-I", str(qt_inc),
                "-I", str(qt_inc / "QtCore"),
                "-I", str(qt_inc / "QtWidgets"),
                "-I", str(qt_inc / "QtGui"),
                "-I", str(tmp),
                "wizardprobe.cpp", "moc_wizardprobe.cpp",
            ],
            cwd=tmp, capture_output=True, text=True, env=env,
        )
        check("g++ exit 0", r.returncode == 0, (r.stderr + r.stdout)[-300:] if r.returncode else "")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def test_class_wizard_refuses_overwrite():
    print("\n[9] qt_class_wizard -- refuses to overwrite existing files")
    tmp = _sandbox_tmpdir("qt_wizard_ow")
    try:
        inp = server.QtClassWizardInput(
            output_dir=str(tmp), class_name="MyProbe", base_class="QWidget",
        )
        await server.qt_class_wizard(inp)
        out = await server.qt_class_wizard(inp)
        check("refuses overwrite", "refuse to overwrite" in out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def test_class_wizard_validates_inputs():
    print("\n[10] qt_class_wizard -- validates inputs")
    inp = server.QtClassWizardInput(
        output_dir=r"C:\Windows\Temp\bad", class_name="Foo", base_class="QWidget",
    )
    out = await server.qt_class_wizard(inp)
    check("outside sandbox rejected", "outside the allowed sandbox" in out)

    inp = server.QtClassWizardInput(
        output_dir=r"E:\Download_tools\QT\Files", class_name="1bad", base_class="QWidget",
    )
    out = await server.qt_class_wizard(inp)
    check("bad class name rejected", "invalid class_name" in out)

    inp = server.QtClassWizardInput(
        output_dir=r"E:\Download_tools\QT\Files", class_name="Foo", base_class="not-a-class!",
    )
    out = await server.qt_class_wizard(inp)
    check("bad base class rejected", "invalid base_class" in out)


async def test_class_wizard_no_ui_path():
    print("\n[11] qt_class_wizard -- has_ui=False skips .ui generation")
    tmp = _sandbox_tmpdir("qt_wizard_nui")
    try:
        inp = server.QtClassWizardInput(
            output_dir=str(tmp), class_name="NoUiClass", base_class="QObject", has_ui=False,
        )
        out = await server.qt_class_wizard(inp)
        check("no .ui file written", not (tmp / "nouiclass.ui").exists())
        check("has .h and .cpp", (tmp / "nouiclass.h").exists() and (tmp / "nouiclass.cpp").exists())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def main():
    await test_docs_search_basic()
    await test_docs_search_fts5_syntax()
    await test_docs_search_bad_inputs()
    await test_grep_finds_known_symbols()
    await test_grep_respects_globs_and_case()
    await test_grep_skips_build_dirs()
    await test_grep_bad_inputs()
    await test_class_wizard_generates_and_compiles()
    await test_class_wizard_refuses_overwrite()
    await test_class_wizard_validates_inputs()
    await test_class_wizard_no_ui_path()
    print(f"\n{GREEN}=== NEW TOOLS V2 E2E PASSED (11 tests) ==={RESET}")


if __name__ == "__main__":
    asyncio.run(main())