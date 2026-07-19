"""e2e for v17 new tool (v0.3.1): qt_signal_lint_fix.

Run: python e2e_new_tools_v17.py
"""

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import server
from server import QtSignalLintFixInput, SANDBOX_TMP

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


# ---------- qt_signal_lint_fix ----------

async def test_signal_fix_unique_connection():
    print("\n[1] qt_signal_lint_fix -- unique_connection adds Qt::UniqueConnection")
    d = fresh_dir(SANDBOX_TMP, "v17_signal_unique")
    cpp = d / "widget.cpp"
    # 5-arg connect with Qt::DirectConnection: rule OR's in UniqueConnection
    cpp.write_text(
        "#include \"widget.h\"\n"
        "void Widget::setup() {\n"
        "    connect(button, SIGNAL(clicked()), this, SLOT(onClick()), Qt::DirectConnection);\n"
        "    connect(button, SIGNAL(clicked()), this, SLOT(onClick()), Qt::DirectConnection);\n"  # duplicate
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_signal_lint_fix(QtSignalLintFixInput(
        source_files=[str(cpp)],
        rules=["unique_connection"],
        apply=False,
    ))
    check("returns header", "qt_signal_lint_fix" in out)
    check("reports unique_connection applied", "unique_connection: +" in out)
    check("diff contains Qt::UniqueConnection", "Qt::UniqueConnection" in out)
    check("did NOT modify file (apply=False)", "Qt::UniqueConnection" not in cpp.read_text(encoding="utf-8"))


async def test_signal_fix_apply_writes_bak():
    print("\n[2] qt_signal_lint_fix -- apply=True writes .bak + modifies source")
    d = fresh_dir(SANDBOX_TMP, "v17_signal_apply")
    cpp = d / "widget.cpp"
    # Use 5-arg connect so unique_connection actually fires
    cpp.write_text(
        "#include \"widget.h\"\n"
        "void Widget::setup() {\n"
        "    connect(button, SIGNAL(clicked()), this, SLOT(onClick()), Qt::DirectConnection);\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_signal_lint_fix(QtSignalLintFixInput(
        source_files=[str(cpp)],
        rules=["unique_connection"],
        apply=True,
    ))
    check("Files written in report", "Files written" in out)
    bak_path = d / "widget.cpp.bak"
    check(".bak file created", bak_path.exists())
    check("source file modified (has UniqueConnection)", "Qt::UniqueConnection" in cpp.read_text(encoding="utf-8"))
    check(".bak preserves original (no UniqueConnection)", "Qt::UniqueConnection" not in bak_path.read_text(encoding="utf-8"))


async def test_signal_fix_functor_to_pointer():
    print("\n[3] qt_signal_lint_fix -- functor_to_pointer converts SIGNAL/SLOT macros to PMF")
    d = fresh_dir(SANDBOX_TMP, "v17_signal_pmf")
    cpp = d / "modern.cpp"
    cpp.write_text(
        "#include \"modern.h\"\n"
        "void Modern::setup() {\n"
        "    connect(button, SIGNAL(Modern::sig()), this, SLOT(Modern::slot()));\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_signal_lint_fix(QtSignalLintFixInput(
        source_files=[str(cpp)],
        rules=["functor_to_pointer"],
        apply=False,
    ))
    check("reports functor_to_pointer applied", "functor_to_pointer: +" in out)
    check("diff has &Modern::sig", "&Modern::sig" in out)


async def test_signal_fix_queued_connection_with_marker():
    print("\n[4] qt_signal_lint_fix -- queued_connection adds QueuedConnection when @thread marker present")
    d = fresh_dir(SANDBOX_TMP, "v17_signal_queued")
    cpp = d / "threaded.cpp"
    cpp.write_text(
        "#include \"threaded.h\"\n"
        "// @thread:main\n"
        "class Worker { /* runs in worker thread */ };\n"
        "void Manager::setup() {\n"
        "    Worker* w = new Worker();\n"
        "    connect(w, SIGNAL(progressUpdated()), this, SLOT(onProgress()));\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_signal_lint_fix(QtSignalLintFixInput(
        source_files=[str(cpp)],
        rules=["queued_connection"],
        apply=False,
    ))
    check("reports queued_connection applied", "queued_connection: +" in out)
    check("diff has Qt::QueuedConnection", "Qt::QueuedConnection" in out)


async def test_signal_fix_queued_connection_no_marker():
    print("\n[5] qt_signal_lint_fix -- queued_connection does NOT add without @thread marker")
    d = fresh_dir(SANDBOX_TMP, "v17_signal_queued_nomarker")
    cpp = d / "plain.cpp"
    cpp.write_text(
        "#include \"plain.h\"\n"
        "void Plain::setup() {\n"
        "    connect(sender, SIGNAL(ping()), this, SLOT(onPing()));\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_signal_lint_fix(QtSignalLintFixInput(
        source_files=[str(cpp)],
        rules=["queued_connection"],
        apply=False,
    ))
    check("queued_connection NOT applied (no fix rule line)", "queued_connection: +" not in out)
    check("no diff generated", "no fixable" in out.lower())


async def test_signal_fix_orphan_slot_stub():
    print("\n[6] qt_signal_lint_fix -- orphan_slot_stub adds empty implementations")
    d = fresh_dir(SANDBOX_TMP, "v17_signal_orphan")
    cpp = d / "orphan.cpp"
    cpp.write_text(
        "#include \"orphan.h\"\n"
        "class Worker : public QObject {\n"
        "    Q_OBJECT\n"
        "public slots:\n"
        "    void onTick();\n"
        "    void onStop();\n"
        "};\n"
        "void Worker::setup() {\n"
        "    connect(timer, SIGNAL(timeout()), this, SLOT(onTick()));\n"
        "    // onStop is never connected\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_signal_lint_fix(QtSignalLintFixInput(
        source_files=[str(cpp)],
        rules=["orphan_slot_stub"],
        apply=False,
    ))
    check("reports orphan_slot_stub applied", "orphan_slot_stub: +" in out)
    check("diff mentions onStop stub", "onStop" in out)
    check("diff has qWarning", "qWarning" in out)


async def test_signal_fix_multiple_rules_combined():
    print("\n[7] qt_signal_lint_fix -- multiple rules combined in single pass")
    d = fresh_dir(SANDBOX_TMP, "v17_signal_combined")
    cpp = d / "combo.cpp"
    cpp.write_text(
        "#include \"combo.h\"\n"
        "void Combo::setup() {\n"
        "    connect(button, SIGNAL(Combo::sig()), this, SLOT(Combo::slot()));\n"
        "    connect(button, SIGNAL(clicked()), this, SLOT(onClick()));\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_signal_lint_fix(QtSignalLintFixInput(
        source_files=[str(cpp)],
        rules=["unique_connection", "functor_to_pointer"],
        apply=False,
    ))
    check("reports both rules applied", "unique_connection" in out and "functor_to_pointer" in out)


async def test_signal_fix_no_rules_match():
    print("\n[8] qt_signal_lint_fix -- clean file produces no diff")
    d = fresh_dir(SANDBOX_TMP, "v17_signal_clean")
    cpp = d / "clean.cpp"
    cpp.write_text(
        "#include \"clean.h\"\n"
        "void Clean::setup() {\n"
        "    int x = 42;\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_signal_lint_fix(QtSignalLintFixInput(
        source_files=[str(cpp)],
        rules=["unique_connection", "queued_connection", "functor_to_pointer"],
        apply=False,
    ))
    check("reports no fixable issues", "no fixable" in out.lower())
    check("no diff section", "--- " not in out)


async def test_signal_fix_invalid_rule():
    print("\n[9] qt_signal_lint_fix -- invalid rule name returns Error")
    d = fresh_dir(SANDBOX_TMP, "v17_signal_badrule")
    cpp = d / "x.cpp"
    cpp.write_text("void f() {}", encoding="utf-8")
    out = await server.qt_signal_lint_fix(QtSignalLintFixInput(
        source_files=[str(cpp)],
        rules=["unique_connection", "made_up_rule"],
    ))
    check("returns Error:", "Error:" in out)
    check("mentions invalid rule", "made_up_rule" in out or "unknown" in out.lower())


async def test_signal_fix_empty_files():
    print("\n[10] qt_signal_lint_fix -- empty source_files rejected")
    out = await server.qt_signal_lint_fix(QtSignalLintFixInput(
        source_files=[],
    ))
    check("returns Error:", "Error:" in out)


async def test_signal_fix_sandbox_rejection():
    print("\n[11] qt_signal_lint_fix -- sandbox rejection on outside path")
    out = await server.qt_signal_lint_fix(QtSignalLintFixInput(
        source_files=[r"C:\Windows\System32\drivers\etc\hosts"],
        rules=["unique_connection"],
    ))
    check("returns Error:", "Error:" in out)
    check("mentions sandbox", "sandbox" in out.lower())


async def test_signal_fix_idempotent_unique_connection():
    print("\n[12] qt_signal_lint_fix -- unique_connection is idempotent (already has it)")
    d = fresh_dir(SANDBOX_TMP, "v17_signal_idempotent")
    cpp = d / "idem.cpp"
    cpp.write_text(
        "#include \"idem.h\"\n"
        "void Ider::setup() {\n"
        "    connect(button, SIGNAL(clicked()), this, SLOT(onClick()), Qt::UniqueConnection);\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_signal_lint_fix(QtSignalLintFixInput(
        source_files=[str(cpp)],
        rules=["unique_connection"],
        apply=False,
    ))
    check("reports no fixable (idempotent)", "no fixable" in out.lower() or "0 rule" in out.lower())


# ---------- tool count ----------

async def test_tool_count():
    print("\n[13] tool count -- v0.3.1 should be >= 85")
    tools = await server.mcp.list_tools()
    check(f"tool count >= 85 (got {len(tools)})", len(tools) >= 85)


ALL_TESTS = [
    test_signal_fix_unique_connection,
    test_signal_fix_apply_writes_bak,
    test_signal_fix_functor_to_pointer,
    test_signal_fix_queued_connection_with_marker,
    test_signal_fix_queued_connection_no_marker,
    test_signal_fix_orphan_slot_stub,
    test_signal_fix_multiple_rules_combined,
    test_signal_fix_no_rules_match,
    test_signal_fix_invalid_rule,
    test_signal_fix_empty_files,
    test_signal_fix_sandbox_rejection,
    test_signal_fix_idempotent_unique_connection,
    test_tool_count,
]


async def main():
    print("=" * 60)
    print("qt-mcp v0.3.1 e2e (qt_signal_lint_fix)")
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