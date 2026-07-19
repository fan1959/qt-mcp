import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

"""E2E test for the new structured JSON diagnostics in qt_build / qt_build_diagnostics.

Two projects, exercised separately because mingw32-make stops after the first
failing translation unit, so a single project can only trigger one family of
errors reliably:

  - ProjA (g++ only): warning + error in demowindow.cpp
  - ProjB (moc only): malformed signal in badheader.h

Verifies:
  - qt_build failure embeds a `--- diagnostics (JSON) ---` block
  - parsing the block yields the right severities/tools/file:line:col
  - the sidecar log (<project>/.qt_mcp_last_build.log) is written
  - qt_build_diagnostics (no recompile) returns the same diagnostics
  - explicit build_log override path works
  - sandbox rejection + missing-log error paths
"""
import asyncio
import json
import re
import shutil
import sys
import textwrap
import uuid
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).parent.parent.parent / "server.py"
TMP_ROOT = Path(r"E:\Download_tools\QT\.tmp")

DIAG_BLOCK_RE = re.compile(r"--- diagnostics \(JSON\) ---\n(\[\s*[\s\S]*?\n\])", re.MULTILINE)


async def call(session, tool, expect_error=False, **kwargs):
    print(f"\n=== {tool}({list(kwargs.keys())}) ===", flush=True)
    res = await session.call_tool(tool, arguments={"params": kwargs} if kwargs else {})
    text = res.content[0].text if res.content else ""
    if res.isError or "Error" in text:
        if not expect_error:
            raise RuntimeError(f"{tool} failed unexpectedly:\n{text[:400]}")
    return text


def extract_diagnostics(text: str) -> list[dict]:
    m = DIAG_BLOCK_RE.search(text)
    if not m:
        raise AssertionError(
            "No `--- diagnostics (JSON) ---` block found in tool output.\n"
            f"--- output head ---\n{text[:600]}\n--- output tail ---\n{text[-400:]}"
        )
    return json.loads(m.group(1))


def assert_diag_keys_complete(diags: list[dict]) -> None:
    required = {"severity", "file", "line", "column", "tool", "code", "message", "suggestion"}
    for d in diags:
        missing = required - d.keys()
        assert not missing, f"diagnostic missing keys {missing}: {d}"
        assert d["severity"] in ("error", "warning", "info"), d
        assert d["tool"] in ("gcc", "moc", "uic", "rcc", "qmake", "ld"), d
        assert d["suggestion"], f"empty suggestion: {d}"


def print_diagnostics(label: str, diags: list[dict]) -> None:
    print(f"  -> {label}: {len(diags)} diagnostic(s)")
    for d in diags:
        loc = f"{d.get('file') or '<none>'}:{d.get('line')}:{d.get('column')}"
        print(f"     [{d['severity']:7}] {d['tool']:8} {loc}: {d['message'][:70]}")


async def main():
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    work = TMP_ROOT / f"e2e_diag_{uuid.uuid4().hex[:8]}"
    work.mkdir(parents=True, exist_ok=True)
    print(f"Workdir: {work}")

    projA = work / "projA_gcc"   # warning + g++ error
    projB = work / "projB_moc"   # moc error only

    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    try:
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()

                # ---- 1) Scaffold ProjA (g++ errors) ----
                print("\n# ---- scaffold ProjA ----", flush=True)
                t = await call(s, "qt_scaffold", name="demo", template="widget", output_dir=str(projA))
                assert "Scaffolded" in t, t
                # Class name is "Demo" (template uses name.capitalize()).
                (projA / "demowindow.cpp").write_text(textwrap.dedent("""\
                    #include "demowindow.h"
                    #include "ui_demowindow.h"

                    Demo::Demo(QWidget* parent)
                        : QWidget(parent)
                        , ui(new Ui::Demo)
                    {
                        ui->setupUi(this);
                        int unused_local = 42;  // -Wunused-variable
                        int x = undeclared_symbol;  // intentional error
                    }
                    Demo::~Demo() { delete ui; }
                """), encoding="utf-8")

                # ---- 2) Build ProjA (expect failure) ----
                print("\n# ---- qt_build ProjA ----", flush=True)
                t = await call(s, "qt_build", expect_error=True,
                               project_dir=str(projA), build_type="debug", jobs=2)
                assert "Build failed" in t, f"expected failure, got:\n{t[:300]}"
                assert "Category:" in t, "Category hint block should still be present"

                diagsA = extract_diagnostics(t)
                print_diagnostics("ProjA", diagsA)
                assert_diag_keys_complete(diagsA)
                assert len(diagsA) >= 3, f"expected >= 3 diagnostics, got {len(diagsA)}"

                # At least one g++ warning with -W code
                gcc_warnings = [d for d in diagsA if d["tool"] == "gcc" and d["severity"] == "warning"]
                assert gcc_warnings, "expected at least one g++ warning"
                wdiag = gcc_warnings[0]
                assert wdiag["code"] and wdiag["code"].startswith("-W"), wdiag
                assert wdiag["file"] and wdiag["line"] is not None and wdiag["column"] is not None, wdiag
                assert wdiag["file"].startswith(str(projA)), f"file should be absolute: {wdiag['file']}"

                # At least one g++ error
                gcc_errors = [d for d in diagsA if d["tool"] == "gcc" and d["severity"] == "error"]
                assert gcc_errors, "expected at least one g++ error"
                ediag = gcc_errors[0]
                assert "undeclared" in ediag["message"].lower(), ediag

                # ---- 3) Scaffold ProjB (moc error only) ----
                print("\n# ---- scaffold ProjB ----", flush=True)
                t = await call(s, "qt_scaffold", name="projb", template="widget", output_dir=str(projB))
                assert "Scaffolded" in t, t
                bad_h = projB / "badheader.h"
                bad_h.write_text(textwrap.dedent("""\
                    #pragma once
                    #include <QObject>
                    class BadEmitter : public QObject {
                        Q_OBJECT
                    signals:
                        void this is not valid;  // moc will choke on the method name
                    };
                """), encoding="utf-8")
                pro_text = (projB / "projb.pro").read_text(encoding="utf-8")
                if "badheader.h" not in pro_text:
                    pro_text = pro_text.replace(
                        "HEADERS += projbwindow.h",
                        "HEADERS += projbwindow.h \\\n           badheader.h",
                    )
                    (projB / "projb.pro").write_text(pro_text, encoding="utf-8")

                # ---- 4) Build ProjB (expect failure) ----
                print("\n# ---- qt_build ProjB ----", flush=True)
                t = await call(s, "qt_build", expect_error=True,
                               project_dir=str(projB), build_type="debug", jobs=2)
                assert "Build failed" in t, f"expected failure, got:\n{t[:300]}"

                diagsB = extract_diagnostics(t)
                print_diagnostics("ProjB", diagsB)
                assert_diag_keys_complete(diagsB)
                moc_diags = [d for d in diagsB if d["tool"] == "moc"]
                assert moc_diags, (
                    f"expected at least one moc error, got tools={ {d['tool'] for d in diagsB} }\n"
                    f"messages: {[d['message'] for d in diagsB]}"
                )
                mdiag = moc_diags[0]
                assert mdiag["severity"] == "error", mdiag
                # moc 5.14+ newer format reports the original .h file (not moc_xxx.cpp).
                assert mdiag["file"] and mdiag["file"].endswith((".cpp", ".h")), mdiag
                assert mdiag["line"] is not None, mdiag
                assert mdiag["suggestion"], mdiag
                # Message should mention the moc-specific wording
                assert any(
                    kw in mdiag["message"].lower()
                    for kw in ("signal", "slot", "q_object", "class")
                ), f"unexpected moc message: {mdiag['message']}"

                # ---- 5) Sidecar log was written for ProjA ----
                logA = projA / ".qt_mcp_last_build.log"
                assert logA.is_file(), f"sidecar log missing: {logA}"
                assert logA.stat().st_size > 0, "sidecar log is empty"
                print(f"  -> sidecar log: {logA} ({logA.stat().st_size} bytes)")

                # ---- 6) qt_build_diagnostics (no recompile) returns same as ProjA ----
                print("\n# ---- qt_build_diagnostics ProjA ----", flush=True)
                t = await call(s, "qt_build_diagnostics", project_dir=str(projA))
                assert "diagnostic(s)" in t, t
                diagsA2 = extract_diagnostics(t)
                print_diagnostics("ProjA re-parsed", diagsA2)
                # Same set of (tool, message) pairs
                a = sorted((d["tool"], d["message"]) for d in diagsA)
                b = sorted((d["tool"], d["message"]) for d in diagsA2)
                assert a == b, (
                    f"diagnostic mismatch:\n qt_build embedded: {a}\n qt_build_diagnostics: {b}"
                )

                # ---- 7) Explicit build_log override path ----
                print("\n# ---- qt_build_diagnostics with explicit log path ----", flush=True)
                t = await call(s, "qt_build_diagnostics",
                               project_dir=str(projA), build_log=str(logA))
                diagsA3 = extract_diagnostics(t)
                assert len(diagsA3) == len(diagsA), "override path mismatch"

                # ---- 8) Sandbox rejection ----
                print("\n# ---- sandbox rejection ----", flush=True)
                t = await call(s, "qt_build_diagnostics", expect_error=True,
                               project_dir=r"D:\outside\foo")
                assert "sandbox" in t.lower() or "outside" in t.lower(), t

                # ---- 9) Missing log error path ----
                print("\n# ---- missing log error path ----", flush=True)
                fresh = work / "fresh"
                fresh.mkdir()
                (fresh / "x.pro").write_text("TEMPLATE = app\nSOURCES = main.cpp\n", encoding="utf-8")
                t = await call(s, "qt_build_diagnostics", expect_error=True,
                               project_dir=str(fresh))
                assert "no saved build log" in t.lower(), t
                assert "Run qt_build first" in t, t

                # ---- 10) Successful build should NOT embed a diagnostics block ----
                print("\n# ---- success build has no diagnostics block ----", flush=True)
                good = work / "good"
                await call(s, "qt_scaffold", name="good", template="widget", output_dir=str(good))
                t = await call(s, "qt_build", project_dir=str(good), build_type="debug", jobs=2)
                assert "Build OK" in t
                assert "--- diagnostics (JSON) ---" not in t, "success should not include diagnostics block"

        print("\n=== STRUCTURED DIAGNOSTICS E2E PASSED ===")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
