"""e2e for v16 new tools (v0.3.1): qt_documentation_auto_fill, qt_translation_auto_fill.

Run: python e2e_new_tools_v16.py
"""

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import server
from server import (
    QtDocumentationAutoFillInput, QtTranslationAutoFillInput,
    SANDBOX_TMP,
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


def make_mock_llm_call(text: str = "/// @brief mock summary\n/// @param x input\n/// @return result\n"):
    """Returns a coroutine that mimics _llm_call with a canned response."""
    async def _mock(provider, model, system_prompt, user_prompt, timeout=30.0):
        return {"ok": True, "text": text, "error": ""}
    return _mock


def patch_llm_call(text: str):
    """Monkeypatch server._llm_call with a mock that returns ``text``.
    Returns a restore function to put the original back. Critical: never
    ``del`` server._llm_call — the test framework depends on it existing
    for subsequent tests.
    """
    original = getattr(server, "_llm_call", None)
    server._llm_call = make_mock_llm_call(text)

    def restore():
        if original is not None:
            server._llm_call = original
        elif hasattr(server, "_llm_call"):
            del server._llm_call
    return restore


# ---------- qt_documentation_auto_fill ----------

async def test_doc_auto_fill_dry_run():
    print("\n[1] qt_documentation_auto_fill -- dry_run (apply=False) does NOT write")
    d = fresh_dir(SANDBOX_TMP, "v16_doc_auto_dry")
    header = d / "demo.h"
    header.write_text(
        "#pragma once\n"
        "#include <QWidget>\n"
        "class Demo : public QWidget {\n"
        "    Q_OBJECT\n"
        "public:\n"
        "    // no doxygen block\n"
        "    explicit Demo();\n"
        "    int compute(int x) const;\n"
        "};\n",
        encoding="utf-8",
    )
    original = header.read_text(encoding="utf-8")
    # Monkeypatch _llm_call so we don't burn real API tokens
    restore = patch_llm_call(
        "/// @brief mock Demo constructor.\n\n"
        "/// @brief mock compute.\n/// @param x input value\n/// @return result\n"
    )
    try:
        out = await server.qt_documentation_auto_fill(QtDocumentationAutoFillInput(
            source_files=[str(header)],
            apply=False,
        ))
    finally:
        restore()
    check("returns header", "qt_documentation_auto_fill" in out)
    check("reports 2 undocumented functions", "2 undocumented" in out or "Total undocumented functions: 2" in out)
    check("diff preview present (--- demo.h)", "--- demo.h" in out or "demo.h" in out)
    check("did NOT modify file (apply=False)", header.read_text(encoding="utf-8") == original)


async def test_doc_auto_fill_no_api_key():
    print("\n[2] qt_documentation_auto_fill -- no API key returns Error")
    d = fresh_dir(SANDBOX_TMP, "v16_doc_auto_nokey")
    header = d / "demo.h"
    header.write_text(
        "#pragma once\n"
        "class Demo {\n"
        "public:\n"
        "    void f();\n"
        "};\n",
        encoding="utf-8",
    )
    # Ensure neither key is set
    import os
    saved_a = os.environ.pop("ANTHROPIC_API_KEY", None)
    saved_o = os.environ.pop("OPENAI_API_KEY", None)
    try:
        out = await server.qt_documentation_auto_fill(QtDocumentationAutoFillInput(
            source_files=[str(header)],
            apply=False,
        ))
    finally:
        if saved_a:
            os.environ["ANTHROPIC_API_KEY"] = saved_a
        if saved_o:
            os.environ["OPENAI_API_KEY"] = saved_o
    check("returns Error:", "Error:" in out)
    check("mentions API key", "API key" in out or "API_KEY" in out)


async def test_doc_auto_fill_empty_files():
    print("\n[3] qt_documentation_auto_fill -- empty source_files rejected")
    out = await server.qt_documentation_auto_fill(QtDocumentationAutoFillInput(
        source_files=[],
    ))
    check("returns Error:", "Error:" in out)


async def test_doc_auto_fill_apply_writes_bak():
    print("\n[4] qt_documentation_auto_fill -- apply=True writes .bak + modifies source")
    d = fresh_dir(SANDBOX_TMP, "v16_doc_auto_apply")
    header = d / "demo.h"
    header.write_text(
        "#pragma once\n"
        "class Demo {\n"
        "public:\n"
        "    void f();\n"
        "};\n",
        encoding="utf-8",
    )
    # Set a fake key so we pass the key check
    import os
    os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
    restore = patch_llm_call("/// @brief mock f.\n")
    try:
        out = await server.qt_documentation_auto_fill(QtDocumentationAutoFillInput(
            source_files=[str(header)],
            apply=True,
        ))
    finally:
        restore()
        # don't leave a fake key
        if os.environ.get("ANTHROPIC_API_KEY") == "test-key-not-real":
            del os.environ["ANTHROPIC_API_KEY"]
    check("Files written in report", "Files written" in out)
    bak_path = d / "demo.h.bak"
    check(".bak file created", bak_path.exists())
    check("source file modified (different from bak)", header.read_text(encoding="utf-8") != bak_path.read_text(encoding="utf-8"))


async def test_doc_auto_fill_fully_documented():
    print("\n[5] qt_documentation_auto_fill -- well-documented file emits no diff")
    d = fresh_dir(SANDBOX_TMP, "v16_doc_auto_clean")
    header = d / "good.h"
    header.write_text(
        "#pragma once\n"
        "class Good {\n"
        "public:\n"
        "    /// @brief Already documented function with sufficient length.\n"
        "    /// @return nothing\n"
        "    void f();\n"
        "};\n",
        encoding="utf-8",
    )
    # Need a key + mock so the tool passes the LLM check and runs through the
    # 'find undocumented functions' path; with no undocumented functions it
    # never actually calls the mock LLM.
    import os
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    restore = patch_llm_call("/// @brief unused\n")
    try:
        out = await server.qt_documentation_auto_fill(QtDocumentationAutoFillInput(
            source_files=[str(header)],
            apply=False,
        ))
    finally:
        restore()
        if os.environ.get("ANTHROPIC_API_KEY") == "test-key":
            del os.environ["ANTHROPIC_API_KEY"]
    check("reports fully documented", "fully documented" in out or "no undocumented" in out.lower())
    check("0 undocumented", "Total undocumented functions: 0" in out)


# ---------- qt_translation_auto_fill ----------

async def test_translation_auto_fill_dry_run():
    print("\n[6] qt_translation_auto_fill -- dry_run generates diff preview")
    d = fresh_dir(SANDBOX_TMP, "v16_trans_auto_dry")
    ts = d / "zh_CN.ts"
    ts.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<!DOCTYPE TS>\n'
        '<TS version="2.1" language="zh_CN">\n'
        '<context>\n'
        '  <message>\n'
        '    <location filename="../main.cpp" line="10"/>\n'
        '    <source>Hello</source>\n'
        '    <translation type="unfinished"></translation>\n'
        '  </message>\n'
        '  <message>\n'
        '    <location filename="../main.cpp" line="20"/>\n'
        '    <source>World</source>\n'
        '    <translation type="unfinished"></translation>\n'
        '  </message>\n'
        '</context>\n'
        '</TS>\n',
        encoding="utf-8",
    )
    original = ts.read_text(encoding="utf-8")
    import os
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    restore = patch_llm_call("[1] 你好\n[2] 世界\n")
    try:
        out = await server.qt_translation_auto_fill(QtTranslationAutoFillInput(
            ts_files=[str(ts)],
            apply=False,
        ))
    finally:
        restore()
        if os.environ.get("ANTHROPIC_API_KEY") == "test-key":
            del os.environ["ANTHROPIC_API_KEY"]
    check("returns header", "qt_translation_auto_fill" in out)
    check("reports 2 unfinished", "2 entries" in out)
    check("diff preview present", "--- " in out)
    check("did NOT modify .ts file (apply=False)", ts.read_text(encoding="utf-8") == original)


async def test_translation_auto_fill_no_api_key():
    print("\n[7] qt_translation_auto_fill -- no API key returns Error")
    d = fresh_dir(SANDBOX_TMP, "v16_trans_auto_nokey")
    ts = d / "x.ts"
    ts.write_text(
        '<?xml version="1.0"?>\n'
        '<TS version="2.1" language="en_US">\n'
        '<context><message><location/>'
        '<source>Hi</source><translation type="unfinished"></translation>'
        '</message></context></TS>\n',
        encoding="utf-8",
    )
    import os
    saved_a = os.environ.pop("ANTHROPIC_API_KEY", None)
    saved_o = os.environ.pop("OPENAI_API_KEY", None)
    try:
        out = await server.qt_translation_auto_fill(QtTranslationAutoFillInput(
            ts_files=[str(ts)],
            apply=False,
        ))
    finally:
        if saved_a:
            os.environ["ANTHROPIC_API_KEY"] = saved_a
        if saved_o:
            os.environ["OPENAI_API_KEY"] = saved_o
    check("returns Error:", "Error:" in out)


async def test_translation_auto_fill_empty():
    print("\n[8] qt_translation_auto_fill -- empty ts_files rejected")
    out = await server.qt_translation_auto_fill(QtTranslationAutoFillInput(
        ts_files=[],
    ))
    check("returns Error:", "Error:" in out)


async def test_translation_auto_fill_target_lang_filter():
    print("\n[9] qt_translation_auto_fill -- target_language filter skips non-matching .ts")
    d = fresh_dir(SANDBOX_TMP, "v16_trans_auto_filter")
    ts_en = d / "en_US.ts"
    ts_en.write_text(
        '<?xml version="1.0"?>\n'
        '<TS version="2.1" language="en_US">\n'
        '<context><message><location/>'
        '<source>Hi</source><translation type="unfinished"></translation>'
        '</message></context></TS>\n',
        encoding="utf-8",
    )
    # Ask for zh_CN only — the en_US .ts should be skipped entirely
    import os
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    try:
        out = await server.qt_translation_auto_fill(QtTranslationAutoFillInput(
            ts_files=[str(ts_en)],
            target_language="zh_CN",
            apply=False,
        ))
    finally:
        if os.environ.get("ANTHROPIC_API_KEY") == "test-key":
            del os.environ["ANTHROPIC_API_KEY"]
    # No diff means file was filtered out (correct behavior)
    check("skipped non-matching language (0 unfinished)", "Total unfinished entries: 0" in out)
    check("file unchanged", ts_en.read_text(encoding="utf-8").count("type=\"unfinished\"") == 1)


async def test_translation_auto_fill_apply_writes_bak():
    print("\n[10] qt_translation_auto_fill -- apply=True writes .bak + modifies .ts")
    d = fresh_dir(SANDBOX_TMP, "v16_trans_auto_apply")
    ts = d / "fr.ts"
    ts.write_text(
        '<?xml version="1.0"?>\n'
        '<TS version="2.1" language="fr">\n'
        '<context><message><location/>'
        '<source>Hello</source><translation type="unfinished"></translation>'
        '</message></context></TS>\n',
        encoding="utf-8",
    )
    import os
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    restore = patch_llm_call("[1] Bonjour\n")
    try:
        out = await server.qt_translation_auto_fill(QtTranslationAutoFillInput(
            ts_files=[str(ts)],
            apply=True,
        ))
    finally:
        restore()
        if os.environ.get("ANTHROPIC_API_KEY") == "test-key":
            del os.environ["ANTHROPIC_API_KEY"]
    check("Files written in report", "Files written" in out)
    bak_path = d / "fr.ts.bak"
    check(".bak file created", bak_path.exists())
    new_text = ts.read_text(encoding="utf-8")
    check(".ts contains new translation", "Bonjour" in new_text)
    check(".ts no longer has unfinished", "type=\"unfinished\"" not in new_text)


# ---------- sandbox + tool count ----------

async def test_doc_auto_fill_sandbox_rejection():
    print("\n[11] qt_documentation_auto_fill -- sandbox rejection on outside path")
    # Set a fake key so we pass the LLM check and reach the per-file sandbox check
    import os
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    try:
        out = await server.qt_documentation_auto_fill(QtDocumentationAutoFillInput(
            source_files=[r"C:\Windows\System32\drivers\etc\hosts"],
        ))
    finally:
        if os.environ.get("ANTHROPIC_API_KEY") == "test-key":
            del os.environ["ANTHROPIC_API_KEY"]
    check("returns Error:", "Error:" in out)
    check("mentions sandbox", "sandbox" in out.lower())


async def test_tool_count():
    print("\n[12] tool count -- v0.3.1 should be >= 85")
    tools = await server.mcp.list_tools()
    check(f"tool count >= 85 (got {len(tools)})", len(tools) >= 85)


ALL_TESTS = [
    test_doc_auto_fill_dry_run,
    test_doc_auto_fill_no_api_key,
    test_doc_auto_fill_empty_files,
    test_doc_auto_fill_apply_writes_bak,
    test_doc_auto_fill_fully_documented,
    test_translation_auto_fill_dry_run,
    test_translation_auto_fill_no_api_key,
    test_translation_auto_fill_empty,
    test_translation_auto_fill_target_lang_filter,
    test_translation_auto_fill_apply_writes_bak,
    test_doc_auto_fill_sandbox_rejection,
    test_tool_count,
]


async def main():
    print("=" * 60)
    print("qt-mcp v0.3.1 e2e (qt_documentation_auto_fill + qt_translation_auto_fill)")
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