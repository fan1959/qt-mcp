"""e2e tests for the 4 new tools added in the Jul 8 v4 wave (plus console_app
scaffold template and qt_run env_vars support).

Tools covered:
  - qt_format         (clang-format integration — uses a fake stub we write to
                       disk so we don't need the real clang-format.exe)
  - qt_resources      (.qrc add/remove/list/validate)
  - qt_diagnose_env   (Qt/MinGW environment health check)

Other coverage:
  - console_app scaffold template (scaffold → qmake+make → run the .exe)
  - qt_run env_vars support (verify extra env is actually visible to the child)
  - 26-tool registration count

Run from anywhere:
    python e2e_new_tools_v4.py
"""
from __future__ import annotations

import asyncio
import os
import re
import shutil
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(HERE))

import server  # noqa: E402


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


# ---------------------------------------------------------------------------
# qt_format — fake clang-format stub
# ---------------------------------------------------------------------------

_FAKE_CLANG_FORMAT_PY = '''#!/usr/bin/env python3
"""Fake clang-format stub for e2e tests.

Behaves like clang-format but only on filenames containing "dirty" (a "would
reformat" signal) and "clean" (well-formatted):
  - dirty + in-place (-i): rewrites the file in place, prints REFORMATTED to stdout
  - dirty + check-only (no -i): prints a unified diff to stdout, exits 1
  - clean: no output, no rewrite
"""
import os, sys

# Detect in-place mode
in_place = "-i" in sys.argv

# The file is the only positional arg (the only non-flag arg)
positional = [a for a in sys.argv[1:] if not a.startswith("-")]
if not positional:
    sys.exit(0)

target = positional[-1]
name = os.path.basename(target)
is_dirty = "dirty" in name

if not is_dirty:
    sys.exit(0)

if in_place:
    with open(target, "w", encoding="utf-8") as f:
        f.write("// reformatted by stub\\nint x = 1;\\n")
    print("REFORMATTED")
    sys.exit(0)
else:
    # check-only: emit a diff and exit 1
    print("--- a/" + name)
    print("+++ b/" + name)
    print("@@ -1 +1 @@")
    print("-int   x   =   1;")
    print("+int x = 1;")
    sys.exit(1)
'''


def _make_fake_clang_format() -> Path:
    """Write a fake clang-format.py stub to a sandbox location and return its path.

    The tool is invoked as `python <stub> ...args...` — actually we just give the
    stub path directly, and rely on the shebang + 'py' launcher association.
    Simpler: write a .cmd wrapper that calls `python <stub.py>`.
    """
    py_path = SANDBOX_TMP / f"fake_clang_format_{uuid.uuid4().hex[:8]}.py"
    py_path.write_text(_FAKE_CLANG_FORMAT_PY, encoding="utf-8")
    # Create a .cmd wrapper that forwards to `python <py_path> %*`
    cmd_path = py_path.with_suffix(".cmd")
    cmd_path.write_text(f'@echo off\r\n"python" "{py_path}" %*\r\nexit /b %ERRORLEVEL%\r\n', encoding="ascii")
    return cmd_path


async def test_format_finds_no_exe():
    print("\n[1] qt_format -- no clang-format available")
    tmp = _sandbox_tmpdir("qt_format_noexe")
    try:
        (tmp / "x.cpp").write_text("int main(){}\n", encoding="utf-8")
        out = await server.qt_format(server.QtFormatInput(
            target=str(tmp), clang_format_exe="",
        ))
        check("clear error when no exe",
              "clang-format not found" in out,
              out.splitlines()[0][:80])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def test_format_in_place_with_stub():
    print("\n[2] qt_format -- in-place with fake stub (reformats 'dirty' files)")
    tmp = _sandbox_tmpdir("qt_format_inplace")
    stub = _make_fake_clang_format()
    try:
        (tmp / "clean.cpp").write_text("int x=1;\n", encoding="utf-8")
        (tmp / "dirty_file.cpp").write_text("int   x   =   1;\n", encoding="utf-8")
        out = await server.qt_format(server.QtFormatInput(
            target=str(tmp), clang_format_exe=str(stub), check_only=False,
        ))
        check("reformatted count surfaced", "reformatted: 1" in out, out[:200])
        check("unchanged count surfaced", "unchanged: 1" in out)
        # The dirty file should have been rewritten by the stub
        contents = (tmp / "dirty_file.cpp").read_text(encoding="utf-8")
        check("dirty file was rewritten", "reformatted by stub" in contents, contents[:60])
        check("clean file untouched", (tmp / "clean.cpp").read_text() == "int x=1;\n")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        try: stub.unlink()
        except OSError: pass


async def test_format_check_only_with_stub():
    print("\n[3] qt_format -- check-only mode (no file changes)")
    tmp = _sandbox_tmpdir("qt_format_check")
    stub = _make_fake_clang_format()
    try:
        (tmp / "dirty_file.cpp").write_text("int   x   =   1;\n", encoding="utf-8")
        original = (tmp / "dirty_file.cpp").read_text(encoding="utf-8")
        out = await server.qt_format(server.QtFormatInput(
            target=str(tmp), clang_format_exe=str(stub), check_only=True,
        ))
        check("NEEDS REFORMAT verdict emitted", "NEEDS REFORMAT" in out)
        check("would-change list non-empty", "would-change: 1" in out)
        check("file NOT modified by check-only",
              (tmp / "dirty_file.cpp").read_text() == original)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        try: stub.unlink()
        except OSError: pass


async def test_format_sandbox_rejected():
    print("\n[4] qt_format -- sandbox rejection")
    out = await server.qt_format(server.QtFormatInput(
        target=r"D:\outside\foo.cpp",
    ))
    check("outside sandbox rejected", "outside the allowed sandbox" in out)


# ---------------------------------------------------------------------------
# qt_resources — list / add / remove / validate
# ---------------------------------------------------------------------------

_SAMPLE_QRC = """<RCC>
    <qresource prefix="/">
        <file>images/icon.png</file>
    </qresource>
    <qresource prefix="/img">
        <file>subdir/logo.svg</file>
    </qresource>
</RCC>
"""


async def test_resources_list():
    print("\n[5] qt_resources -- list entries")
    tmp = _sandbox_tmpdir("qt_res_list")
    try:
        (tmp / "images").mkdir()
        (tmp / "images" / "icon.png").write_bytes(b"\x89PNG fake")
        qrc = tmp / "resources.qrc"
        qrc.write_text(_SAMPLE_QRC, encoding="utf-8")
        out = await server.qt_resources(server.QtResourcesInput(
            qrc_file=str(qrc), action="list",
        ))
        check("both prefixes listed", "prefix='/'" in out and "prefix='/img'" in out)
        check("icon.png listed", "icon.png" in out)
        check("logo.svg listed", "logo.svg" in out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def test_resources_add():
    print("\n[6] qt_resources -- add new files")
    tmp = _sandbox_tmpdir("qt_res_add")
    try:
        (tmp / "images").mkdir()
        (tmp / "images" / "icon.png").write_bytes(b"x")
        (tmp / "images" / "new_one.png").write_bytes(b"y")
        qrc = tmp / "resources.qrc"
        qrc.write_text(_SAMPLE_QRC, encoding="utf-8")
        out = await server.qt_resources(server.QtResourcesInput(
            qrc_file=str(qrc), action="add",
            files=["images/new_one.png"],
        ))
        check("add reports change", "1 change(s) applied" in out)
        # Verify file shows up in the .qrc now
        contents = qrc.read_text(encoding="utf-8")
        check("new file appears in .qrc", "new_one.png" in contents)
        # Idempotency: adding again should report 0 changes
        out2 = await server.qt_resources(server.QtResourcesInput(
            qrc_file=str(qrc), action="add",
            files=["images/new_one.png"],
        ))
        check("adding same file again is a no-op", "no changes applied" in out2)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def test_resources_remove():
    print("\n[7] qt_resources -- remove files")
    tmp = _sandbox_tmpdir("qt_res_remove")
    try:
        (tmp / "images").mkdir()
        (tmp / "images" / "icon.png").write_bytes(b"x")
        qrc = tmp / "resources.qrc"
        qrc.write_text(_SAMPLE_QRC, encoding="utf-8")
        out = await server.qt_resources(server.QtResourcesInput(
            qrc_file=str(qrc), action="remove",
            files=["images/icon.png"],
        ))
        check("remove reports change", "1 change(s) applied" in out)
        contents = qrc.read_text(encoding="utf-8")
        check("icon.png gone from .qrc", "icon.png" not in contents)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def test_resources_validate():
    print("\n[8] qt_resources -- validate (missing files + dupes)")
    tmp = _sandbox_tmpdir("qt_res_validate")
    try:
        (tmp / "images").mkdir()
        (tmp / "images" / "icon.png").write_bytes(b"x")
        # Build a qrc with one valid and one missing + a duplicate
        qrc = tmp / "resources.qrc"
        qrc.write_text(
            "<RCC>\n"
            "    <qresource prefix=\"/\">\n"
            "        <file>images/icon.png</file>\n"
            "        <file>images/missing.png</file>\n"
            "        <file>images/icon.png</file>\n"  # dupe
            "    </qresource>\n"
            "</RCC>\n",
            encoding="utf-8",
        )
        out = await server.qt_resources(server.QtResourcesInput(
            qrc_file=str(qrc), action="validate",
        ))
        check("missing file reported", "missing on disk: 1" in out)
        check("missing file path listed", "missing.png" in out)
        check("duplicate reported", "duplicates: 1" in out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def test_resources_sandbox_rejected():
    print("\n[9] qt_resources -- sandbox rejection")
    out = await server.qt_resources(server.QtResourcesInput(
        qrc_file=r"D:\outside\foo.qrc", action="list",
    ))
    check("outside sandbox rejected", "outside the allowed sandbox" in out)


# ---------------------------------------------------------------------------
# qt_diagnose_env
# ---------------------------------------------------------------------------

async def test_diagnose_env_basic():
    print("\n[10] qt_diagnose_env -- basic (no deep)")
    out = await server.qt_diagnose_env(server.QtDiagnoseEnvInput(deep=False))
    check("report includes Required binaries section", "=== Required binaries ===" in out)
    check("report includes Sandbox section", "=== Sandbox ===" in out)
    check("report includes Summary section", "=== Summary ===" in out)
    check("qmake OK", "[OK]   qmake (64-bit)" in out)
    check("mingw32-make OK", "[OK]   mingw32-make" in out)
    check("g++ OK", "[OK]   g++ (64-bit)" in out)
    check("summary line present", "checks OK" in out)


async def test_diagnose_env_deep():
    print("\n[11] qt_diagnose_env -- deep mode (runs --version)")
    out = await server.qt_diagnose_env(server.QtDiagnoseEnvInput(deep=True))
    check("Deep mode section present", "=== Deep mode: version checks ===" in out)
    check("qmake version reported", "qmake -v" in out)
    check("mingw32-make version reported", "mingw32-make --version" in out)
    check("g++ version reported", "g++ --version" in out)
    # Look for an actual version string (Qt 5.14.2, g++.exe (Rev...) etc.)
    check("a Qt version string surfaces",
          any(s in out for s in ("Qt 5.14", "5.14.2", "5.14")),
          "looking for Qt 5.14 in output")


# ---------------------------------------------------------------------------
# console_app scaffold — full pipeline (scaffold → build → run)
# ---------------------------------------------------------------------------

async def test_console_app_full_pipeline():
    print("\n[12] qt_scaffold console_app → qt_build → qt_run")
    tmp = _sandbox_tmpdir("qt_console_app")
    try:
        out = await server.qt_scaffold(server.QtScaffoldInput(
            name="mycli", template="console_app", output_dir=str(tmp),
        ))
        check("scaffold reports console_app", "Template: console_app" in out)
        check(".pro file written", (tmp / "mycli.pro").is_file())
        check("main.cpp written", (tmp / "main.cpp").is_file())
        # No window files for console app
        check("no .ui file", not (tmp / "mycliwindow.ui").exists())

        # Build it
        build_out = await server.qt_build(server.QtBuildInput(
            project_dir=str(tmp), build_type="debug", jobs=4, timeout=180,
        ))
        check("build looks successful",
              "returncode 0" in build_out or "Built" in build_out,
              build_out.splitlines()[-1] if build_out else "")

        # .exe should exist
        exe = tmp / "debug" / "mycli.exe"
        check("exe produced", exe.is_file(), str(exe))

        # Run it (the scaffold has QCommandLineParser + --version + --help)
        run_out = await server.qt_run(server.QtRunInput(
            executable=str(exe), args=["--version"],
            timeout=10, cwd=str(tmp),
        ))
        check("exe runs and shows version",
              "mycli" in run_out and "0.1.0" in run_out,
              run_out[:200])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# qt_run env_vars support — verify they reach the child
# ---------------------------------------------------------------------------

async def test_run_env_vars_visible_to_child():
    print("\n[13] qt_run -- env_vars are visible to the child process")
    tmp = _sandbox_tmpdir("qt_run_env")
    try:
        # Build a tiny C++ program that prints an env var
        src = tmp / "showenv.cpp"
        src.write_text(
            '#include <cstdlib>\n'
            '#include <cstdio>\n'
            'int main() {\n'
            '    const char* v = std::getenv("QT_MCP_TEST_VAR");\n'
            '    std::printf("VAL=%s\\n", v ? v : "(unset)");\n'
            '    return 0;\n'
            '}\n',
            encoding="utf-8",
        )
        # Compile directly with g++ from the same env qt-mcp uses
        gpp = server.MINGW_BIN_DIR / "g++.exe"
        exe = tmp / "showenv.exe"
        proc = await asyncio.create_subprocess_exec(
            str(gpp), str(src), "-o", str(exe),
            env=server._qt_env(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        check("g++ compiled the probe", exe.is_file())

        # Now run it via qt_run with env_vars, verify child sees the value
        out = await server.qt_run(server.QtRunInput(
            executable=str(exe), env_vars={"QT_MCP_TEST_VAR": "hello-from-mcp"},
            timeout=10, cwd=str(tmp),
        ))
        check("env var reached the child",
              "VAL=hello-from-mcp" in out,
              out[:200])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# 26-tool registration count
# ---------------------------------------------------------------------------

async def test_registration_count():
    print("\n[14] MCP tool registration count")
    import re
    text = (HERE / "server.py").read_text(encoding="utf-8")
    tools = re.findall(r"@mcp\.tool\(name=\"([^\"]+)\"", text)
    print(f"  -- found {len(tools)} tools")
    check(">= 26 tools registered (23 baseline + 3 new)", len(tools) >= 26)
    for required in ("qt_format", "qt_resources", "qt_diagnose_env"):
        check(f"{required} registered", required in tools)


# ---------------------------------------------------------------------------

async def main() -> int:
    tests = [
        test_format_finds_no_exe,
        test_format_in_place_with_stub,
        test_format_check_only_with_stub,
        test_format_sandbox_rejected,
        test_resources_list,
        test_resources_add,
        test_resources_remove,
        test_resources_validate,
        test_resources_sandbox_rejected,
        test_diagnose_env_basic,
        test_diagnose_env_deep,
        test_console_app_full_pipeline,
        test_run_env_vars_visible_to_child,
        test_registration_count,
    ]
    for t in tests:
        await t()
    print()
    print(f"{GREEN}=== NEW TOOLS V4 E2E PASSED ({len(tests)} tests) ==={RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
