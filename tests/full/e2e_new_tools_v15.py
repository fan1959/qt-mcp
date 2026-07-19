"""e2e for v15 new tools (v0.3.0): qt_build_cache, qt_steamworks_init,
qt_itch_butler, qt_documentation_lint.

Run: python e2e_new_tools_v15.py
"""

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import server
from server import (
    QtBuildCacheInput, QtSteamworksInitInput, QtItchButlerInput,
    QtDocumentationLintInput,
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


def write_minimal_pro(d: Path, name: str = "demo") -> Path:
    """Drop a minimal Qt widget .pro + main.cpp so tools that scan .pro work."""
    (d / f"{name}.pro").write_text(
        "QT       += core gui widgets\n"
        "TARGET   = demo\n"
        "TEMPLATE = app\n"
        "SOURCES += main.cpp\n"
        "HEADERS += demo.h\n",
        encoding="utf-8",
    )
    (d / "main.cpp").write_text(
        '#include "demo.h"\n'
        '#include <QApplication>\n'
        'int main(int argc, char *argv[]) {\n'
        '    QApplication a(argc, argv);\n'
        '    Demo w;\n'
        '    w.show();\n'
        '    return a.exec();\n'
        '}\n',
        encoding="utf-8",
    )
    (d / "demo.h").write_text(
        '#pragma once\n'
        '#include <QWidget>\n'
        'class Demo : public QWidget {\n'
        '    Q_OBJECT\n'
        'public:\n'
        '    explicit Demo(QWidget *parent = nullptr);\n'
        '    int computeScore(int base) const;\n'
        '};\n',
        encoding="utf-8",
    )
    return d / f"{name}.pro"


# ---------- qt_build_cache ----------

async def test_qt_build_cache_report_only():
    print("\n[1] qt_build_cache -- report_only on fresh project")
    d = fresh_dir(SANDBOX_TMP, "v15_build_cache_report")
    write_minimal_pro(d)
    out = await server.qt_build_cache(QtBuildCacheInput(
        project_dir=str(d),
        enable_ccache=True,
        report_only=True,
    ))
    check("returns header", "qt_build_cache:" in out)
    check("mentions backend", "Backend detected" in out)
    check("shows .pro snippet", "recommended .pro snippet" in out)
    # report_only must not patch the .pro
    pro_text = (d / "demo.pro").read_text(encoding="utf-8")
    check("did NOT modify .pro (report_only)", "qt_build_cache:" not in pro_text)


async def test_qt_build_cache_no_pro_file():
    print("\n[2] qt_build_cache -- no .pro rejected")
    d = fresh_dir(SANDBOX_TMP, "v15_build_cache_nopro")
    out = await server.qt_build_cache(QtBuildCacheInput(
        project_dir=str(d),
        enable_ccache=True,
    ))
    check("returns Error:", "Error:" in out)
    check("mentions .pro", ".pro" in out)


async def test_qt_build_cache_missing_dir():
    print("\n[3] qt_build_cache -- missing project_dir")
    out = await server.qt_build_cache(QtBuildCacheInput(
        project_dir=str(SANDBOX_TMP / "does_not_exist_xyz"),
    ))
    check("returns Error:", "Error:" in out)


async def test_qt_build_cache_sandbox_rejection():
    print("\n[4] qt_build_cache -- sandbox rejection")
    out = await server.qt_build_cache(QtBuildCacheInput(
        project_dir=r"C:\Windows\System32",
        enable_ccache=True,
    ))
    check("returns Error: outside sandbox", "Error:" in out and "sandbox" in out.lower())


# ---------- qt_steamworks_init ----------

async def test_qt_steamworks_init_default_appid():
    print("\n[5] qt_steamworks_init -- default app_id 480 (Spacewar)")
    d = fresh_dir(SANDBOX_TMP, "v15_steamworks_default")
    write_minimal_pro(d)
    out = await server.qt_steamworks_init(QtSteamworksInitInput(
        project_dir=str(d),
        app_id=480,
        write_steam_appid_txt=True,
    ))
    check("returns header", "qt_steamworks_init" in out)
    check("writes steamworks_integration.h", "steamworks_integration.h" in out)
    check("writes steamworks_integration.cpp", "steamworks_integration.cpp" in out)
    check("writes steam_achievements.h", "steam_achievements.h" in out)
    check("writes steam_achievements.cpp", "steam_achievements.cpp" in out)
    check("writes STEAMWORKS.md", "STEAMWORKS.md" in out)
    check("writes steam_appid.txt", "steam_appid.txt" in out)
    # verify files actually exist
    check("steamworks_integration.h on disk", (d / "steamworks_integration.h").exists())
    check("steam_appid.txt contains 480", (d / "steam_appid.txt").read_text(encoding="utf-8").strip() == "480")
    # verify content has SteamAPI_Init
    header_text = (d / "steamworks_integration.h").read_text(encoding="utf-8")
    check("header has Q_OBJECT", "Q_OBJECT" in header_text)
    cpp_text = (d / "steamworks_integration.cpp").read_text(encoding="utf-8")
    check("cpp has SteamAPI_Init", "SteamAPI_Init" in cpp_text)
    check("cpp has SteamAPI_RunCallbacks", "SteamAPI_RunCallbacks" in cpp_text)


async def test_qt_steamworks_init_custom_appid():
    print("\n[6] qt_steamworks_init -- custom app_id")
    d = fresh_dir(SANDBOX_TMP, "v15_steamworks_custom")
    write_minimal_pro(d)
    out = await server.qt_steamworks_init(QtSteamworksInitInput(
        project_dir=str(d),
        app_id=123456,
        write_steam_appid_txt=True,
    ))
    check("app_id 123456 in steam_appid.txt", (d / "steam_appid.txt").read_text(encoding="utf-8").strip() == "123456")


async def test_qt_steamworks_init_no_appid_txt():
    print("\n[7] qt_steamworks_init -- write_steam_appid_txt=False")
    d = fresh_dir(SANDBOX_TMP, "v15_steamworks_no_appid")
    write_minimal_pro(d)
    out = await server.qt_steamworks_init(QtSteamworksInitInput(
        project_dir=str(d),
        app_id=480,
        write_steam_appid_txt=False,
    ))
    check("does NOT write steam_appid.txt", not (d / "steam_appid.txt").exists())
    check("still writes STEAMWORKS.md", (d / "STEAMWORKS.md").exists())


async def test_qt_steamworks_init_no_pro():
    print("\n[8] qt_steamworks_init -- no .pro rejected")
    d = fresh_dir(SANDBOX_TMP, "v15_steamworks_nopro")
    out = await server.qt_steamworks_init(QtSteamworksInitInput(
        project_dir=str(d),
        app_id=480,
    ))
    check("returns Error:", "Error:" in out)
    check("mentions .pro", ".pro" in out)


# ---------- qt_itch_butler ----------

async def test_qt_itch_butler_basic():
    print("\n[9] qt_itch_butler -- basic manifest + push scripts (dry_run=True)")
    d = fresh_dir(SANDBOX_TMP, "v15_itch_basic")
    write_minimal_pro(d)
    out = await server.qt_itch_butler(QtItchButlerInput(
        project_dir=str(d),
        itch_user="alice",
        itch_game="mygame",
        channels=["windows", "macos", "linux"],
        dry_run=True,
    ))
    check("returns header", "qt_itch_butler" in out)
    check("target shows alice/mygame", "alice/mygame" in out)
    check("writes .itch.toml", (d / ".itch.toml").exists())
    check("writes push_windows.bat", (d / "push_windows.bat").exists())
    check("writes push_macos.sh", (d / "push_macos.sh").exists())
    check("writes push_linux.sh", (d / "push_linux.sh").exists())
    check("writes BUTLER_README.md", (d / "BUTLER_README.md").exists())
    # verify .itch.toml content
    toml_text = (d / ".itch.toml").read_text(encoding="utf-8")
    check("toml has windows channel", "windows" in toml_text)
    check("toml has macos channel", "macos" in toml_text)
    check("toml has linux channel", "linux" in toml_text)
    # verify push script is dry-run
    ps_text = (d / "push_windows.bat").read_text(encoding="utf-8")
    check("push_windows.bat is dry-run", "[dry-run]" in ps_text)
    check("push_windows.bat has butler push", "butler" in ps_text.lower() and "push" in ps_text.lower())


async def test_qt_itch_butler_actual_run():
    print("\n[10] qt_itch_butler -- dry_run=False strips echo prefix")
    d = fresh_dir(SANDBOX_TMP, "v15_itch_actual")
    write_minimal_pro(d)
    out = await server.qt_itch_butler(QtItchButlerInput(
        project_dir=str(d),
        itch_user="bob",
        itch_game="bobsgame",
        channels=["windows"],
        dry_run=False,
    ))
    check("header present", "qt_itch_butler" in out)
    ps_text = (d / "push_windows.bat").read_text(encoding="utf-8")
    check("push_windows.bat has NO [dry-run]", "[dry-run]" not in ps_text)


async def test_qt_itch_butler_html5_channel():
    print("\n[11] qt_itch_butler -- html5 channel uses .bat (Windows-friendly)")
    d = fresh_dir(SANDBOX_TMP, "v15_itch_html5")
    write_minimal_pro(d)
    out = await server.qt_itch_butler(QtItchButlerInput(
        project_dir=str(d),
        itch_user="alice",
        itch_game="htmlgame",
        channels=["html5"],
        dry_run=True,
    ))
    check("writes push_html5.bat", (d / "push_html5.bat").exists())


async def test_qt_itch_butler_missing_user():
    print("\n[12] qt_itch_butler -- missing itch_user rejected")
    d = fresh_dir(SANDBOX_TMP, "v15_itch_no_user")
    write_minimal_pro(d)
    out = await server.qt_itch_butler(QtItchButlerInput(
        project_dir=str(d),
        itch_user="",
        itch_game="x",
        channels=["windows"],
    ))
    check("returns Error:", "Error:" in out)
    check("mentions user or game", "user" in out.lower() or "game" in out.lower())


async def test_qt_itch_butler_sandbox_rejection():
    print("\n[13] qt_itch_butler -- sandbox rejection")
    out = await server.qt_itch_butler(QtItchButlerInput(
        project_dir=r"C:\Program Files",
        itch_user="x",
        itch_game="y",
        channels=["windows"],
    ))
    check("returns Error: outside sandbox", "Error:" in out and "sandbox" in out.lower())


# ---------- qt_documentation_lint ----------

async def test_qt_documentation_lint_clean():
    print("\n[14] qt_documentation_lint -- well-documented file reports high coverage")
    d = fresh_dir(SANDBOX_TMP, "v15_doc_lint_clean")
    good_header = d / "good.h"
    good_header.write_text(
        "#pragma once\n"
        "#include <QWidget>\n"
        "class GoodWidget : public QWidget {\n"
        "    Q_OBJECT\n"
        "public:\n"
        "    /// @brief Construct a widget with the given name.\n"
        "    /// @param name the display name\n"
        "    explicit GoodWidget(const QString &name);\n"
        "\n"
        "    /// @brief Compute the score.\n"
        "    /// @param base base value\n"
        "    /// @return computed score\n"
        "    int computeScore(int base) const;\n"
        "};\n",
        encoding="utf-8",
    )
    out = await server.qt_documentation_lint(QtDocumentationLintInput(
        source_files=[str(good_header)],
        output_format="text",
    ))
    check("emits header", "qt_documentation_lint" in out)
    check("reports coverage", "Coverage:" in out)
    check("reports 100% coverage (well-documented)", "100.0%" in out)


async def test_qt_documentation_lint_missing_brief():
    print("\n[15] qt_documentation_lint -- file missing @brief is flagged")
    d = fresh_dir(SANDBOX_TMP, "v15_doc_lint_missing")
    bad_header = d / "bad.h"
    bad_header.write_text(
        "#pragma once\n"
        "#include <QWidget>\n"
        "class BadWidget : public QWidget {\n"
        "    Q_OBJECT\n"
        "public:\n"
        "    // no doxygen block at all\n"
        "    explicit BadWidget();\n"
        "\n"
        "    /// @brief undocumented param\n"
        "    /// @return stuff\n"
        "    int computeScore(int base) const;\n"
        "};\n",
        encoding="utf-8",
    )
    out = await server.qt_documentation_lint(QtDocumentationLintInput(
        source_files=[str(bad_header)],
        output_format="text",
    ))
    check("flags missing @brief", "missing @brief" in out or "no doxygen comment" in out)
    check("flags missing @param", "missing @param" in out)


async def test_qt_documentation_lint_json_format():
    print("\n[16] qt_documentation_lint -- JSON output mode")
    d = fresh_dir(SANDBOX_TMP, "v15_doc_lint_json")
    h = d / "demo.h"
    h.write_text(
        "#pragma once\n"
        "class X {\n"
        "public:\n"
        "    /// @brief documented\n"
        "    int f();\n"
        "};\n",
        encoding="utf-8",
    )
    out = await server.qt_documentation_lint(QtDocumentationLintInput(
        source_files=[str(h)],
        output_format="json",
    ))
    check("output is JSON object", out.strip().startswith("{"))
    check("has 'summary' key", "\"summary\"" in out)
    check("has 'coverage' key", "\"coverage\"" in out)


async def test_qt_documentation_lint_threshold_fail():
    print("\n[17] qt_documentation_lint -- fail_threshold returns Error on low coverage")
    d = fresh_dir(SANDBOX_TMP, "v15_doc_lint_threshold")
    h = d / "x.h"
    h.write_text(
        "#pragma once\n"
        "class X {\n"
        "public:\n"
        "    void f();  // no doxygen\n"
        "};\n",
        encoding="utf-8",
    )
    out = await server.qt_documentation_lint(QtDocumentationLintInput(
        source_files=[str(h)],
        fail_threshold=0.99,
    ))
    check("returns Error: below threshold", "Error:" in out and "threshold" in out.lower())


async def test_qt_documentation_lint_empty_files():
    print("\n[18] qt_documentation_lint -- empty source_files rejected")
    out = await server.qt_documentation_lint(QtDocumentationLintInput(
        source_files=[],
    ))
    check("returns Error: empty", "Error:" in out)


async def test_qt_documentation_lint_bad_format():
    print("\n[19] qt_documentation_lint -- bad output_format rejected")
    d = fresh_dir(SANDBOX_TMP, "v15_doc_lint_badfmt")
    h = d / "x.h"
    h.write_text("class X {};", encoding="utf-8")
    out = await server.qt_documentation_lint(QtDocumentationLintInput(
        source_files=[str(h)],
        output_format="xml",
    ))
    check("returns Error: invalid format", "Error:" in out)


async def test_qt_documentation_lint_sandbox_rejection():
    print("\n[20] qt_documentation_lint -- sandbox rejection on outside path")
    out = await server.qt_documentation_lint(QtDocumentationLintInput(
        source_files=[r"C:\Windows\System32\drivers\etc\hosts"],
    ))
    check("rejects outside-sandbox path", "Error:" in out and "sandbox" in out.lower())


# ---------- total tool count ----------

async def test_tool_count():
    print("\n[21] tool count -- v0.3.0 should be >= 82")
    tools = await server.mcp.list_tools()
    check(f"tool count >= 82 (got {len(tools)})", len(tools) >= 82)


ALL_TESTS = [
    test_qt_build_cache_report_only,
    test_qt_build_cache_no_pro_file,
    test_qt_build_cache_missing_dir,
    test_qt_build_cache_sandbox_rejection,
    test_qt_steamworks_init_default_appid,
    test_qt_steamworks_init_custom_appid,
    test_qt_steamworks_init_no_appid_txt,
    test_qt_steamworks_init_no_pro,
    test_qt_itch_butler_basic,
    test_qt_itch_butler_actual_run,
    test_qt_itch_butler_html5_channel,
    test_qt_itch_butler_missing_user,
    test_qt_itch_butler_sandbox_rejection,
    test_qt_documentation_lint_clean,
    test_qt_documentation_lint_missing_brief,
    test_qt_documentation_lint_json_format,
    test_qt_documentation_lint_threshold_fail,
    test_qt_documentation_lint_empty_files,
    test_qt_documentation_lint_bad_format,
    test_qt_documentation_lint_sandbox_rejection,
    test_tool_count,
]


async def main():
    print("=" * 60)
    print("qt-mcp v0.3.0 e2e (4 new tools)")
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