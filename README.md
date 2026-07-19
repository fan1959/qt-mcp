# qt-mcp

> **A Model Context Protocol (MCP) server that wraps the Qt 5.14.2 + MinGW toolchain on Windows.**
> Give Claude (or any MCP-compatible client) the ability to scaffold, build, run, test, format, lint, deploy, validate, trace, and inspect Qt C++ projects — without leaving the conversation.

**概述：** 一个本地 stdio MCP 服务器，把 Qt 5.14.2 工具链（qmake / mingw32-make / windeployqt / moc / lupdate / qmllint / clang-format）封装成 **147 个工具**，让 Claude 可以在对话内直接搭建、构建、运行、测试、格式化、部署、跟踪调试 Qt C++ 项目。MIT 协议。版本 `v0.4.3`。

[![Python](https://img.shields.io/badge/python-≥3.10-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.4.3-orange)](CHANGELOG.md)
[![MCP](https://img.shields.io/badge/MCP-1.28%2B-purple)](https://modelcontextprotocol.io)

---

## Features

- **147 tools** covering the full Qt C++ lifecycle — v0.4.2 baseline (143) + v0.4.3 runtime + DB-perf + signal-monitor + u""-literal additions:
  - **`qt_db_perf_index`** — SQLite index advisor (EXPLAIN QUERY PLAN per column, missing-index recommendations, ready-to-paste `CREATE INDEX` SQL).
  - **`qt_qobject_invoke_connect_monitor`** — static connect-call hot-list heatmap (top senders / receivers / signals / slots / files).
  - **`qt_modernize_qt6_string_literal`** — `tr("literal")` → `tr(u"literal")` + non-ASCII literal `u""` prefix migration. Complements `qt_modernize_qt5_to_qt6` (v0.3.6) which already wraps `QString("...")` → `QStringLiteral("...")`.
  - **`qt_qobject_invocation_history`** — runtime Q_INVOKABLE invocation log parser (per-method call counts + duration + caller heatmap + recent timeline).
  Previous increment (v0.4.2) added 4 tools + 1 upgrade:
  - **`qt_qtquick_3d_setup`** — Qt 3D project skeleton (cube/sphere/scene/model_loader templates, qmake or CMake).
  - **`qt_qobject_invoke_metadata`** — static QObject introspection (Q_PROPERTY / signals / slots / Q_INVOKABLE from .h/.cpp).
  - **`qt_qobject_invoke_property_diff`** — diff two header sets for API drift (added / removed / changed).
  - **`qt_qobject_invocation_count`** — static count of `.invokeMethod(` call sites per method.
  - **`qt_signature_batch`** upgrade: `error_strategy` enum (`continue_all` / `fail_fast` / `continue_n:N`) + `csv_report` parameter.
  V0.4.1 added 3 release-rite tools (`qt_asan_runtime_report` / `qt_template_scaffold` / `qt_deploy_bundle`).
- **Local FTS5 full-text search** over the entire Qt 5.14.2 documentation (6,613 pages, indexed, 53 MB).
- **AI-friendly diagnostics**: `qt_build` parses compiler / moc / uic / linker output into structured JSON with one-line fix suggestions.
- **Drive a running Qt app** from Claude via UI automation (`qt_ui_action`).
- **Drive Qt Creator** itself: open a `.pro` in the IDE, build with Ctrl+B, run the .exe (`qt_creator_open` / `qt_creator_run`).
- **Optional JSON trailers** for every tool — set `QT_MCP_JSON=1` and every response gets a machine-readable `--- json ---\n{ok,data|error}` block appended. Off by default so existing e2e string contracts are preserved.
- **Path sandbox**: every input / output must resolve under a configurable root — no accidental writes outside the project tree. Override with `QT_MCP_SANDBOX`.
- **9 scaffold templates** including `widget`, `mainwindow`, `qml_app`, `console_app`, and full game-framework skeletons (cards / chess / generic).
- **Windows-native**: uses the MinGW toolchain and `windeployqt` to produce self-contained deployable folders.
- **Env-overridable paths**: `QT_MCP_QT_ROOT` / `QT_MCP_QT_32_ROOT` / `QT_MCP_MINGW_BIN` / `QT_MCP_QTCREATOR` / `QT_MCP_SANDBOX` — the same `server.py` runs on any machine with Qt 5.14.2 installed.

## Quick start (5 minutes)

### 1. Prerequisites (Windows)

- Windows 10 / 11
- Python ≥ 3.10
- Qt 5.14.2 SDK with MinGW (e.g. `E:\Qt\5.14.2\mingw73_64`)
- A directory of `.qrc` / `.pro` / source files you want to work on (the **sandbox root**)

### 2. Install

```bash
git clone https://github.com/<your-account>/qt-mcp.git
cd qt-mcp
pip install -r requirements.txt
```

### 3. Register with your MCP client

Add to your Claude Desktop / Claude Code `mcp.json`:

```json
{
  "mcpServers": {
    "qt": {
      "command": "python",
      "args": ["<absolute path>\\qt-mcp\\server.py"],
      "transport": "stdio"
    }
  }
}
```

If your Qt install is not at the default `E:\Download_tools\QT\5.14.2\mingw73_64`, set:

```json
{
  "mcpServers": {
    "qt": {
      "command": "python",
      "args": ["<path>\\server.py"],
      "transport": "stdio",
      "env": {
        "QT_MCP_QT_ROOT":     "C:\\Qt\\5.14.2\\mingw73_64",
        "QT_MCP_MINGW_BIN":   "C:\\Qt\\Tools\\mingw730_64\\bin",
        "QT_MCP_SANDBOX":     "C:\\path\\to\\your\\projects"
      }
    }
  }
}
```

### 4. Try it

Ask Claude:

> "Scaffold a new main-window Qt project at `C:\Users\you\projects\hello` and build it."

Claude will call `qt_scaffold` → `qt_build` → `qt_run` in sequence, and you have a running Qt window.

## The 147 tools

| # | Tool | Purpose |
|---|---|---|
| 1 | `qt_env` | Show Qt / MinGW installation paths and versions |
| 2 | `qt_scaffold` | Create a runnable project skeleton (9 templates) |
| 3 | `qt_build` | Run `qmake` + `mingw32-make` and return structured diagnostics on failure |
| 4 | `qt_build_diagnostics` | Re-parse a saved build log into JSON (no recompile) |
| 5 | `qt_run` | Launch the built `.exe` (foreground or detached GUI) |
| 6 | `qt_kill_exe` | Terminate a running Qt process by image name |
| 7 | `qt_deploy` | Bundle the `.exe` with its Qt DLLs / QML / plugins (windeployqt) |
| 8 | `qt_clean` | Remove `debug/` / `release/` / `build-*/` / `Makefile` / `moc_*.cpp` / etc. |
| 9 | `qt_gen_qrc` | Scan an image directory and emit a `.qrc` |
| 10 | `qt_pro_edit` | Read / write `.pro` variables (list, get, set, append, remove) |
| 11 | `qt_moc_check` | Run `moc` on a single header to validate `Q_OBJECT` |
| 12 | `qt_deps` | List DLL dependencies of a built binary (objdump) |
| 13 | `qt_ui_action` | Drive a running Qt app via UI automation (click, type, screenshot) |
| 14 | `qt_docs_search` | Full-text search the local Qt 5.14.2 documentation (FTS5) |
| 15 | `qt_grep` | C++-aware regex search across `.h` / `.cpp` / `.ui` / `.qrc` |
| 16 | `qt_class_wizard` | Generate a `.h` / `.cpp` / `.ui` trio for a new QObject class |
| 17 | `qt_translate` | Run `lupdate` + `lrelease` (`.ts` → `.qm`) |
| 18 | `qt_qml_lint` | Lint `.qml` files with `qmllint` |
| 19 | `qt_qml_test` | Run Qt Quick Test cases via `qmltestrunner` |
| 20 | `qt_designer` | Launch Qt Designer on a `.ui` file |
| 21 | `qt_test` | Run a Qt C++ test executable (QTestLIB) and parse the output |
| 22 | `qt_format` | Run `clang-format` on files / directories (in-place or check-only) |
| 23 | `qt_resources` | List / add / remove / validate entries in a `.qrc` file |
| 24 | `qt_diagnose_env` | Health-check the Qt / MinGW toolchain (16+ binaries, PATH, 32/64-bit) |
| 25 | `qt_creator_open` | Open a `.pro` directly in Qt Creator (skip New Project wizard) |
| 26 | `qt_creator_run` | Build + run a project inside Qt Creator (Ctrl+B + launch) |
| 27 | `qt_validate` | Walk a `.pro` and verify every SOURCES / HEADERS / FORMS / RESOURCES / TRANSLATIONS reference exists |
| 28 | `qt_run_trace` | Launch a `.exe` with `QT_LOGGING_RULES` and capture trace logs (signal/slot, QML, plugin loading) |
| 29 | `qt_smoke_test` | End-to-end health check: clean → build → briefly launch the `.exe` |
| 30 | **`qt_diff`** | Compare two `.pro` projects (variables + sources + content SHA1) |
| 31 | **`qt_pkg`** | List / inspect installed Qt 5 modules (headers, libs, version, plugins) |
| 32 | **`qt_log`** | Filter / analyze a Qt log file (build log or qt_run_trace output) by level + category |
| 33 | **`qt_state`** | QSettings wrapper: save/load/list/delete/clear persistent app state (board-game saves) |
| 34 | **`qt_assets`** | Scan an assets directory and emit a `.qrc` + optional `Q_INIT_RESOURCE` helper |
| 35 | **`qt_watch`** | Watch a Qt project and auto-rebuild on file change (1.5s debounce) |
| 36 | **`qt_signature`** | Sign / verify Windows executables via signtool.exe |
| 37 | **`qt_save`** | Save / load / inspect / list / delete JSON game-state files (portable, alternative to QSettings) |
| 38 | **`qt_audio`** | List / probe / generate QSoundEffect snippets for audio files |
| 39 | **`qt_anim`** | Generate QPropertyAnimation code (fade / move / scale / rotate / color / sequence) |
| 40 | **`qt_network`** | Generate QTcpSocket / QTcpServer / QUdpSocket / QWebSocket C++ class pairs |
| 41 | **`qt_coverage`** | Run gcov + lcov to collect C++ code coverage and emit an HTML report |
| 42 | **`qt_cheatsheet`** | Print a categorized quick reference of all qt-mcp tools |
| 43 | **`qt_score`** | Track and rank player scores for board games (leaderboard) |
| 44 | **`qt_timer`** | Start / stop / pause / resume named timers (game clock, turn timer) |
| 45 | **`qt_replay`** | Record / save / load / play back game replays (step-by-step) |
| 46 | **`qt_lint`** | Run cpplint + qmllint + clang-tidy in one shot |
| 47 | **`qt_analyze`** | Run clang-tidy on a Qt project with custom checks (bugprone / performance / modernize) |
| 48 | **`qt_input`** | Generate keyboard / mouse / gamepad input handling code for Qt games |
| 49 | **`qt_cmake`** | Generate a CMakeLists.txt for a Qt project (qmake alternative) |
| 50 | **`qt_docs_gen`** | Generate and run Doxygen documentation for a Qt project |
| 51 | **`qt_achievement`** | Manage game achievements / medals (define / grant / list / progress) |
| 52 | **`qt_undo`** | Push / undo / redo game-state snapshots (per-project undo stack) |
| 53 | **`qt_leaderboard_ui`** | Generate a leaderboard QWidget (table or cards style) for a board game |
| 54 | **`qt_pkg_install`** | Install / list / uninstall Qt SDKs via aqtinstall |
| 55 | **`qt_release_notes`** | Auto-generate or manually edit CHANGELOG.md from git log |
| 56 | **`qt_copyright`** | Add a license / copyright header to all source files in a project |
| 57 | **`qt_model_gen`** | Generate a QAbstractListModel or QAbstractTableModel subclass for board-game data |
| 58 | **`qt_theme_gen`** | Generate a QSS stylesheet (light / dark theme) for a Qt Widgets app |
| 59 | **`qt_ico_create`** | Bundle one or more PNGs into a multi-resolution Windows `.ico` file |
| 60 | **`qt_screenshot_diff`** | Compare two screenshots pixel-by-pixel for visual regression testing |
| 61 | **`qt_clazy_check`** | Regex-based Qt anti-pattern checker (no clazy binary required) |
| 62 | **`qt_signal_slot_trace`** | Parse C++ source to extract signal/slot declarations and `connect()` calls |
| 63 | **`qt_input_recorder`** | Record or playback mouse / keyboard input events (pyautogui-based) |
| 64 | **`qt_translation_validate`** | Parse `.ts` files and report translation coverage per language |
| 65 | **`qt_git_init`** | Initialize a git repository for a Qt project (.gitignore + README + initial commit) |
| 66 | **`qt_installer_gen`** | Generate a Windows installer script (NSIS `.nsi` or Inno Setup `.iss`) + build batch |
| 67 | **`qt_qml_component_gen`** | Generate reusable QML components for board-game UIs (card / board / player / hand / deck / tile) |
| 68 | **`qt_db_seed`** | Create a SQLite database from a schema definition + insert seed data + emit CRUD examples |
| 69 | **`qt_high_dpi_test`** | Launch a `.exe` at multiple `QT_SCALE_FACTOR` values + screenshot + (optionally) compare to baseline |
| 70 | **`qt_property_browser`** | Extract all `Q_PROPERTY` declarations from a Qt header and render as a markdown / html / json table |
| 71 | **`qt_env_diff`** | Compare two Qt SDK environments (qmake version, modules, libs, missing components) |
| 72 | **`qt_dll_search_path`** | Analyze DLL search path for a Qt `.exe` and report missing Qt5\*.dll (the classic "wrong-bitness" symptom) |
| 73 | **`qt_audio_convert`** | Convert audio files via ffmpeg (mp3 / opus / wav / ogg / flac / m4a / aac) — batch board-game sound prep |
| 74 | **`qt_qss_inspect`** | Parse a `.qss` file and report selector count, duplicates, color/font summary |
| 75 | **`qt_svg_to_png`** | Convert `.svg` files to `.png` at multiple widths (cairosvg → ImageMagick fallback) |
| 76 | **`qt_qml_property_linter`** | Static analysis of QML properties (unused, shadowed ids, type mismatch) |
| 77 | **`qt_accessibility_check`** | Scan Qt C++ sources for a11y issues (missing `setAccessibleName`, `setObjectName`, `Q_DISABLE_COPY`) |
| 78 | **`qt_pro_project_graph`** | Emit a Graphviz DOT dependency graph for a `.pro` project (sources/headers/forms/resources + include edges + cycle detection) |
| 79 | **`qt_build_cache`** | Detect ccache / sccache, inject a compiler-launcher line into the `.pro`, report cache hit rate — 5-10× speedup on incremental builds |
| 80 | **`qt_steamworks_init`** | Generate Steamworks SDK integration (SteamAPI_Init / RunCallbacks / Achievement helpers + `steam_appid.txt` + STEAMWORKS.md) for distributing a Qt game on Steam |
| 81 | **`qt_itch_butler`** | Generate `.itch.toml` + per-channel push scripts for distributing a Qt game on itch.io via the official `butler` CLI (dry-run by default) |
| 82 | **`qt_documentation_lint`** | Check doxygen comment coverage on `.h` / `.cpp` / `.qml` files (missing `@brief` / `@param` / `@return`) — companion to `qt_docs_gen` |
| 83 | **`qt_documentation_auto_fill`** | Use an LLM to auto-fill missing doxygen comments (calls Anthropic Claude / OpenAI GPT, dry-run diff preview by default) — companion to `qt_documentation_lint` |
| 84 | **`qt_translation_auto_fill`** | Use an LLM to fill unfinished entries in `.ts` files (batched, dry-run diff preview by default) — companion to `qt_translation_validate` |
| 85 | **`qt_signal_lint_fix`** | Auto-fix common signal/slot anti-patterns (`Qt::UniqueConnection` / `Qt::QueuedConnection` / Qt5 SIGNAL/SLOT → Qt6 PMF / orphan slot stubs) — companion to `qt_signal_slot_trace` |
| 86 | **`qt_translation_sync`** | Find divergences between `tr()` calls in source and entries in a `.ts` file (missing / orphan); `apply=True` appends `<message>` stubs for missing strings (with `.bak`) — closes the i18n loop: `validate` → `sync` → `auto_fill` |
| 87 | **`qt_async_await_lint`** | Static analysis of Qt async anti-patterns (QtConcurrent::blockingMapped on GUI thread, `QFuture::waitForFinished`, `QThread` subclass without event loop, `moveToThread` after `connect`, `QRunnable` auto-delete policy, `QFutureWatcher` never wired) — text + json, filter by `min_severity` |
| 88 | **`qt_hotreload_check`** | Validate Q_PROPERTY declarations: missing NOTIFY, missing READ, CONSTANT+WRITE contradiction, MEMBER/READ redundancy, NOTIFY signal / MEMBER variable / WRITE setter not declared — companion to `qt_property_browser` (browser *renders*; this tool *validates*) |
| 89 | **`qt_perf_budget`** | CI startup-time gate: launch `.exe`, measure spawn→first-CPU + spawn→first-window (via `pywinauto`), compare to `budget_ms` (default 2000), report `PASS`/`FAIL`, kill the process — companion to `qt_smoke_test` (smoke = "does it run"; perf = "does it run fast") |
| 90 | **`qt_format_check`** | Audit `.h`/`.cpp`/`.cc`/`.cxx` via `clang-format --output-replacements-xml`, aggregate per-file pass/fail into a single CI-friendly report; with `init_clang_format=True` generate a template `.clang-format` from one of 6 built-in styles (llvm / google / chromium / mozilla / webkit / **qt** — derived from Qt 6's `qt.git/.clang-format`); never overwrites existing file — companion to `qt_format` |
| 91 | **`qt_widget_introspect`** | Inspect a *running* Qt app's widget tree via `pywinauto` + UI Automation. Three actions in one tool: `snapshot` (full tree as nested JSON, configurable `max_depth`), `find` (search by `name_contains` / `type_contains` / `text_contains`, AND-combined), `details` (full properties for a widget by `auto_id` — the Qt `setObjectName` exposed as UI Automation's `AutomationId`). Either attach to a running `process_id` or auto-launch `executable`. Always kills spawned processes. Inspired by `0xCarbon/qt-mcp` |
| 92 | **`qt_layout_check`** | Static check of `.ui` files (XML parsed via ElementTree) for layout anti-patterns. Rules: `widget_no_layout_parent` (direct `<widget>` child of a `<widget>` with no enclosing `<layout>` — warning), `deep_nesting` (layout nested > 5 levels — warning), `duplicated_object_name` (two widgets share the same `name` — warning, breaks `findChild`/UI Automation), `layout_no_stretch` (QBoxLayout with ≥2 widgets but no stretch hint — info, usually a missing sizePolicy), `fixed_size_in_expanding_layout` (info). Inspired by `0xCarbon/qt-mcp`'s runtime `qt_layout_check`, runs statically (no app launch required) |
| 93 | **`qt_cppcheck`** | Run `cppcheck --json --library=qt` (or any `--library=...` you choose) on a directory or single file, parse the JSON output defensively (cppcheck sometimes emits multiple top-level objects, one per file), aggregate per-severity counts (`error`/`warning`/`style`/`performance`/`portability`/`information`) into a CI-friendly report. Auto-resolves `cppcheck` via `QT_CPPCHECK_EXE` env var → `PATH`; explicit `cppcheck_exe` overrides both. Severity filter via comma-sep list. text + json output |
| 94 | **`qt_thread_affinity_check`** | Static analysis of **QObject signal/slot cross-thread mistakes** that `qt_async_await_lint` doesn't catch. Rules: `direct_connection_cross_thread` (Qt::DirectConnection used in a file that calls `moveToThread()` → slot runs on emitter's thread, should be QueuedConnection — warning), `emit_without_queued_connection` (emit() in a file with `moveToThread()` — verify thread correctness, info), `qthread_run_without_exec` (QThread subclass whose `run()` override doesn't call `exec()` — warning, no event loop = no signal dispatch), `qobject_constructed_in_worker_thread` (`new QObject()` inside `QThread::run()` / `QRunnable::run()` — info). Each rule has a `requires` precondition so files without threading primitives don't get flagged (filters false positives) |
| 95 | **`qt_sanitizer_run`** | Build a Qt project with a sanitizer flag (`-fsanitize=address` / `address,undefined` / `undefined` / `thread`), then run it briefly and capture sanitizer diagnostics. Workflow: copy project to `sanitizer-<type>-<buildtype>/`, patch `.pro` with `QMAKE_CXXFLAGS += <flag>` + `QMAKE_LFLAGS += <flag>` (idempotent — skips if marker present), `qmake` + `mingw32-make`, spawn `.exe` for `run_seconds` with `ASAN_OPTIONS=halt_on_error=1` / `UBSAN_OPTIONS=print_stacktrace=1` / `TSAN_OPTIONS=second_deadlock_stack=1`, parse output for known sanitizer error markers (`==ERROR: AddressSanitizer`, `runtime error:`, `WARNING: ThreadSanitizer`, `SUMMARY: AddressSanitizer`), report `PASS` / `FAIL`, always `distclean` unless `keep_sanitizer_build=True`. MinGW-compatible (ASan+UBSan combo works on both MinGW and MSVC). Companion to `qt_smoke_test` (smoke = does it run) + `qt_perf_budget` (perf = does it run fast) — this checks *does it crash on common memory / UB errors* |
| 96 | **`qt_perf_compare`** | Reads a baseline JSON (`first_cpu_ms` + `first_window_ms`, from `qt_perf_budget` or prior `qt_perf_compare`), spawns the `.exe`, measures fresh `first_cpu_ms` + `first_window_ms` via the same helpers `qt_perf_budget` uses (`_perf_first_cpu_active` via psutil + `_perf_find_window_for_pid` via pywinauto), compares against baseline, reports `PASS` if either delta is below `regression_ms` (default 200ms), `FAIL` otherwise, always kills the spawned process before returning. CI gate for "did this release get slower?" — companion to `qt_perf_budget` |
| 97 | **`qt_resource_validate`** | Deep-validate a `.qrc` file beyond what `qt_resources validate` checks. Eight rules: `naming_convention` (filename must match `^[a-z0-9_-/.]+$` — no spaces, no uppercase, no special chars), `case_collision` (two entries differing only in case — collide on Windows/macOS), `path_too_deep` (> `max_path_depth` default 8), `file_too_large` (> `max_file_size_kb` default 512 KB — slows resource load), `prefix_conflict` (two `<qresource prefix>` blocks with overlapping sub-paths), `duplicate_entry`, `missing_on_disk`, `unusual_extension` (`.exe/.dll/.so/.bat/.cmd/.sh/.ps1/.msi`). text + json output. CI gate for resource hygiene |
| 98 | **`qt_test_coverage_diff`** | Compares two lcov `.info` files (baseline vs current) to detect coverage regressions. Custom lcov parser (`_lcov_parse`, three regexes for `SF:` / `LF:` / `LH:` blocks) extracts `{filename: (LF, LH)}` per file. Per-file delta, overall delta, lists regressions (delta < −`regression_threshold` default 2%) and improvements. `result` is `FAIL` if any per-file drop > threshold or overall coverage dropped. `source_filter` substring lets you scope to `src/`. text + json output. CI gate against coverage regression — companion to `qt_coverage` |
| 99 | **`qt_screenshot_baseline_capture`** | Captures baseline PNG screenshots across multiple `QT_SCALE_FACTOR` values (`scale_factors` default `[1.0, 1.5, 2.0]`): for each factor spawn `.exe`, set `QT_SCALE_FACTOR`, sleep `wait_seconds`, capture via `pywinauto.capture_as_image()`, save as `baseline_<scale>x.png`, compute sha1, always kill. Writes `manifest.json` with `{label, executable, captured_at, scale_factors}` for traceability. CI workflow: capture baseline → change code → diff current vs baseline via `qt_screenshot_diff` |
| 100 | **`qt_console_messages`** | Captures console-like messages from a *running* Qt app's widget tree (via pywinauto + UI Automation). Unlike `qt_log` (parsed log files) and `qt_run_trace` (env vars at spawn), this tool attaches to a process (or spawns one) and reads text widgets (`QPlainTextEdit` / `QTextEdit` / `QLabel` / `QStatusBar`). Filters via `level_filter` (default `debug\|warning\|critical\|fatal`, `\|`-separated substring tokens), truncates to `max_messages` (default 500), optional `auto_id_contains` substring filter on objectName. Always kills spawned process. Inspired by `0xCarbon/qt-mcp`'s `qt_messages` |
| 101 | **`qt_complexity_lint`** | McCabe-style cyclomatic complexity per C++ function. Walks `.cpp`/`.cc`/`.cxx`/`.h` files, regex-extracts function signatures and brace-matches each body, strips comments + string/char literals (so `if (s == "if")` doesn't count), counts branch keywords (`if`/`else if`/`while`/`for`/`case`/`catch`) + short-circuit operators (`&&`/`\|\|`) + ternary (`?:`). McCabe complexity = 1 + count. Flags functions whose complexity ≥ `threshold` (default 12, rule of thumb "10±2"). Closes the per-function-complexity axis that cppcheck/clazy/qmllint don't cover. text + json output + avg + verdict (PASS/FAIL). Zero new dependencies — pure regex. Companion to `qt_cppcheck` (real C++ static analysis), `qt_clazy_check` (anti-patterns), `qt_signal_slot_trace` (signal graph), `qt_format_check` (style) |
| 102 | **`qt_git_audit`** | Companion to `qt_git_init` (v0.3.0 — which only initialises the repo). Audits an existing repo's history for project-governance signals no Qt tool usually surfaces: **hot files** (top-N by commit count, signals refactor/extract candidates), **bus factor** (top contributor's share of commits; >60% = high risk, >40% = elevated), **churn** (LOC added/removed + density LOC/day in the last `since_days` window), **stale branches** (no commit in `stale_days`), **biggest commit** (largest single-commit files-changed, catches "drive-by mega commits"). Subprocess `git log --pretty=format --numstat` + `git for-each-ref --format`. text + json output |
| 103 | **`qt_appx`** | Companion to `qt_installer_gen` (v0.2.8 — NSIS/Inno for local distribution). Generates the Microsoft Store artifacts: `AppxManifest.xml` (with `runFullTrust` capability — required for Qt apps), `build_appx.bat` (runs `makeappx.exe pack` + `signtool sign` in sequence), `appx_logos.md` (documents the four required PNG logo sizes 50/44/150/310). Like `qt_installer_gen`, only generates — does not invoke Windows SDK tools because they're not part of Qt 5.14 SDK. `architecture` ∈ {`x86`, `x64`, `arm64`} |
| 104 | **`qt_test_fuzz`** | Companion to `qt_sanitizer_run` (memory safety), `qt_smoke_test` (smoke), `qt_perf_budget` (perf), `qt_test` (unit tests). Closes the "fuzzing" leg of the quality-gate quad (smoke / perf / correctness / crash-with-malformed-input). Generates a libFuzzer harness (`LLVMFuzzerTestOneInput` + `LLVMFuzzerRunMain` main when `__has_libfuzzer`) wrapping the user-specified `target_function` (a `Q_INVOKABLE`), a `.pro` patch snippet (`QMAKE_CXXFLAGS += -fsanitize=fuzzer-no-link -fno-omit-frame-pointer`), and a `fuzz_README.md` documenting MinGW-vs-Clang compatibility + 4-step usage. MinGW's bundled GCC 7.x does not ship libFuzzer; the README recommends `compiler='clang++'` for full support. Generates only — does not auto-build, so the user can read instructions first |
| 105 | **`qt_ide_metadata`** | Companion to `qt_creator_open` (which only targets Qt Creator). Generates IDE metadata so you can debug your Qt project from **VSCode** or **CLion** without Qt Creator. `.vscode/launch.json` (gdb debug config, auto-selects mingw32/64), `tasks.json` (qmake / build / run / clean), `c_cpp_properties.json` (includePath + defines extracted via `_pro_parse` from the project's `.pro`), `extensions.json` (recommended: `ms-vscode.cpptools` + `cmake-tools` + `jbenden.c-cpp-flyclang` + `gitlens`). With `ide='both'`, also writes `.idea/workspace.xml` for CLion. Auto-detects the `.exe` from `build-debug/debug/*.exe` etc. if `launch_exe` is empty |
| 106 | **`qt_runtime_props`** | Companion to `qt_widget_introspect` (which shows the widget tree *shape*). Reads each widget's **live accessible properties** from a *running* Qt app via `pywinauto` + UI Automation (mapped from Qt `setAccessibleName` / `setAccessibleDescription` + `setObjectName`). Either attach to running `process_id` or auto-spawn `executable` (always killed before returning). Snapshots every widget with an `objectName` + text in the tree. For full `QMetaObject::property()` values, the user must compile a helper `.exe` into their project — a ready-to-paste hint is printed at the bottom of every output. Borrowed from `0xCarbon/qt-mcp`'s `qt_props` concept |
| 107 | **`qt_conanfile_gen`** | Companion to `qt_pkg_install` (which installs Qt via aqtinstall) and `qt_cmake` (which emits CMakeLists.txt). Closes the cross-platform dependency-management gap: many Qt projects ship to Windows + Linux + macOS with different system Qt packages, and Conan is the de-facto way to pin a reproducible Qt build across all three. Generates both `conanfile.py` (full Python recipe with requires + generators + env_info) and `conanfile.txt` (minimal deps list), plus a `BUILD_README.md` with step-by-step instructions. With `emit_profile='auto'`, also writes `profiles/windows` + `profiles/linux` + `profiles/macos` (compiler.version configurable). Supports `use_system_qt=True` to skip the Conan Qt package and document setting `QTDIR` manually instead |
| 108 | **`qt_module_split_init`** | Companion to `qt_scaffold` (which creates new projects) and `qt_cmake` (which emits CMakeLists.txt). Closes the gap when a flat Qt project grows past ~1k lines: re-organizing into a reusable library + thin app speeds rebuilds, lets multiple apps link the same code, and makes the library self-contained for tests. With `plan_only=True` (default) emits `module_split_plan.json` describing which files go into `lib/src/` + `lib/include/<libname>/` + `app/`. With `plan_only=False`, actually executes the moves (with `.qt_module_split_backup/` safety copy) + writes `lib/lib.pro` (TEMPLATE=lib) + `app/app.pro` (links lib) + rewrites the root `.pro` as `TEMPLATE=subdirs` |
| 109 | **`qt_modernize_qt5_to_qt6`** | Companion to `qt_clazy_check` (which *flags* modern-cpp anti-patterns): this tool actually rewrites the source. Catches the most common Qt 5 → Qt 6 chokepoints so a release upgrade compiles without 30 minutes of find-and-replace. Rules: `qregexp_to_qregularexpression` (QRegExp → QRegularExpression), `q_nullptr_to_nullptr` (Q_NULLPTR[CONSTEXPR] → nullptr), `q_foreach_to_range_for` (Q_FOREACH/foreach → range-based for), `qvector_to_qlist` (QVector<T> → QList<T>), `remove_aa_usehighdpipixmaps` (drop AA_UseHighDpiPixmaps setAttribute — default in Qt 6), `qtextcodec_to_qstringconverter` (QTextCodec → QStringConverter). `apply=False` (default) emits a per-file dry-run preview; `apply=True` writes `.bak` copies + applies the rewrites |
| 110 | **`qt_signal_disconnect_check`** | Companion to `qt_signal_slot_trace` (which maps *all* wires): this tool exposes *missing teardown*. A common lifetime bug: a `QObject` connects to a sender it should explicitly disconnect from in its destructor, but the developer forgets. Walks `.cpp` + `.cc` + `.cxx`, extracts every `connect(...)` first arg and every `disconnect(...)` first arg, lists connect sites whose sender is never disconnected. Output is text or JSON per file:line:sender. `ignore_self_disconnect=True` (default) skips `disconnect(this, …)` patterns (Qt handles those automatically) |
| 111 | **`qt_qml_perf_lint`** | Companion to `qt_qml_lint` (which covers syntax + type-correctness + a few caching rules): this tool focuses on *runtime performance* in QML-heavy UIs. Rules: `inline_js_too_long` (function body > 50 lines, move to .js), `image_synchronous_load` (asynchronous: false), `transparent_mousearea` (visible:false without enabled:false), `loader_frequent_sourcechange` (source URL changes per frame), `deep_component_nesting` (> 5 levels of nesting), `createobject_in_repeater` (createObject inside Repeater delegate — frequent allocation per item). text + json, severity info vs warning, `rule_ids` filter, `file_patterns` configurability |

**New in v0.2.0–v0.4.3** (bold): all 147 tools, env-overridable paths, JSON trailers on every string-return, comprehensive Args/Returns/Raises docstrings on all 147 tools, the `def main()` entry point. See [CHANGELOG.md](CHANGELOG.md).

## 9 scaffold templates

`widget` · `mainwindow` · `dialog` · `qml_app` · **`console_app`** · `cards_game` · `chess_game` · `generic_game` · `game_framework`

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `QT_MCP_QT_ROOT` | `E:\Download_tools\QT\5.14.2\mingw73_64` | Qt 5.14.2 installation root |
| `QT_MCP_QT_32_ROOT` | `E:\Download_tools\QT\5.14.2\mingw73_32` | Qt 5.14.2 32-bit install (used when running 32-bit .exe) |
| `QT_MCP_MINGW_BIN` | `E:\Download_tools\QT\Tools\mingw730_64\bin` | 64-bit MinGW `bin/` |
| `QT_MCP_QTCREATOR` | `E:\Download_tools\QT\Tools\QtCreator\bin\qtcreator.exe` | Qt Creator path (qt_creator_open / qt_creator_run) |
| `QT_MCP_SANDBOX` | `E:\Download_tools\QT` | All paths must resolve under this |
| `QT_MCP_QT_VERSION` | `5.14.2` | Qt version string (error messages only) |
| `QT_MCP_JSON` | (unset) | If set to `1`, every tool appends a `--- json ---\n{ok,data|error}` block to its output for programmatic parsing |
| `QT_FORMAT_EXE` | (none) | Path to `clang-format.exe` (consumed by `qt_format`) |

## Architecture (in one diagram)

```
+--------------------+      stdio JSON-RPC      +-----------------------+
|   MCP client       | <----------------------->|   server.py (FastMCP)  |
|   (Claude Code,    |                          |   26 @mcp.tool funcs   |
|    Claude Desktop) |                          +-----------+-----------+
+--------------------+                                      |
                                                            | subprocess
                                                            v
                          +-------+-------+-------+-------+-------+-------+
                          | qmake  | mingw-| moc  | qmllint | windeployqt |
                          |  .exe  | make  | .exe |  .exe   |   .exe      |
                          +--------+-------+-------+--------+------------+
                                                            |
                                                            v
                                                     +----------+
                                                     | your .exe|
                                                     | (Qt app) |
                                                     +----------+
```

## Documentation index (`qt_docs_search`)

`qt_docs_search` runs against a 53 MB SQLite FTS5 index of the Qt 5.14.2 HTML docs. **The index is gitignored** (too large for git). To rebuild it on a fresh machine:

```bash
python build_docs_index.py
# writes docs_data/qt_5_14_2_docs.db
```

Search supports FTS5 syntax: `QPushButton AND click`, `"signal slot"`, `QList NOT foreach`, etc.

## Development

### Run the test suites

Tests are organized into two tiers via directory + pytest markers:

- `tests/light/` — pure-python tests (parsers, helpers, sandbox rejection). No Qt SDK needed.
- `tests/full/` — tests that build / run Qt projects. Require Qt 5.14.2 + MinGW on PATH (or via `QT_MCP_*` env vars).

```bash
# Run only the light tests (CI-friendly, <5s)
pytest -m light -v

# Run the full suite (needs Qt SDK)
pytest -m full -v

# Run everything
pytest -v
```

Or run the e2e scripts directly (each is a standalone `python e2e_xxx.py` script):

```bash
python tests/full/e2e_test.py            # scaffold → build → run a smoke project
python tests/full/audit_test.py          # sandbox rejection + error paths
python tests/full/e2e_new_tools.py       # qt_pro_edit / qt_moc_check / qt_deps
python tests/full/e2e_new_tools_v2.py    # qt_docs_search / qt_grep / qt_class_wizard (11 tests)
python tests/full/e2e_new_tools_v3.py    # translate / qml_lint / qml_test / designer / test (13 tests)
python tests/full/e2e_new_tools_v4.py    # qt_format / qt_resources / qt_diagnose_env (14 tests)
python tests/full/e2e_new_tools_v5.py    # qt_validate / qt_run_trace / qt_smoke_test (25 tests)
python tests/light/e2e_new_tools_v6.py   # qt_diff (light, 11 tests)
python tests/full/e2e_structured_diagnostics.py
python tests/full/e2e_fixes.py
python tests/light/e2e_gf.py             # game-framework template smoke (light)
python tests/full/e2e_creator_tools.py   # opt-in — needs live Qt Creator
```

### CI / GitHub Actions

`.github/workflows/ci.yml` runs `pytest -m light` on every PR (fast, no SDK).
The full Qt-SDK job is opt-in via `workflow_dispatch` — it installs Qt 5.14.2
via `jurplel/install-qt-action@v4` and runs the full suite (~30s).

## Programmatic output (JSON trailers)

When `QT_MCP_JSON=1` is set, every tool appends a machine-readable trailer:

```
qt_scaffold output here

--- json ---
{
  "ok": true,
  "data": {
    "project_dir": "C:/.../hello",
    "template": "mainwindow"
  }
}
```

Failures look like `{"ok": false, "error": "..."}`. Off by default — the default
text output preserves every existing e2e string-match contract.

## License

MIT — see [LICENSE](LICENSE).
