# Changelog

All notable changes to **qt-mcp** are documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.3] — 2026-07-19

### Added (4 new tools — 147 total)

v0.4.3 focuses on **runtime + DB-perf + signal-monitor + Qt 6 literal migration** — closing the gap between static analysis and runtime introspection, plus the final Qt 6 string-literal migration rules.

- **`qt_db_perf_index`** — SQLite index advisor. Runs `EXPLAIN QUERY PLAN SELECT rowid FROM {table} WHERE {col} = 0` per column; flags columns whose plan shows `SCAN` (full table scan); generates ready-to-paste `CREATE INDEX idx_{table}_{col} ON {table}({col});` SQL. Auto-detects `INTEGER PRIMARY KEY` columns (already implicitly indexed via rowid alias) and skips them. text + json output.
- **`qt_qobject_invoke_connect_monitor`** — Static connect-call topology heatmap. Walks the project for both PMF-style (`connect(sender, &Class::signal, receiver, &Class::slot)`) and old `SIGNAL/SLOT` style connects. Reports top-N senders / receivers / signals (`Class::signal`) / slots (`Class::slot`) / files by connect count. Companion to `qt_signal_slot_trace` (v0.2.7) which maps every wire; this one surfaces the hot-entity heatmap.
- **`qt_modernize_qt6_string_literal`** — Adds the C++14 `u""` prefix to `tr("literal")` calls and to raw string literals containing non-ASCII characters (CJK / emoji / accented Latin). Three rules: `tr_u_prefix`, `literal_u_prefix_nonascii`, `literal_u_prefix_concat` (drops `QString::fromUtf8("中文")` wrapper when literal already has non-ASCII). Skips already-wrapped literals (`u""`, `L""`, `QStringLiteral`, `QByteArrayLiteral`, `QLatin1String`). Complements `qt_modernize_qt5_to_qt6` (v0.3.6) which already wraps `QString("...")` → `QStringLiteral("...")`.
- **`qt_qobject_invocation_history`** — Runtime counterpart to `qt_qobject_invocation_count` (v0.4.2, static). Parses JSON-lines log files (one record per line: `{ts, method, args, caller, duration_ms}`) written by a running helper .exe (built via `qt_invoke_helper_gen`). Reports per-method call count + total/avg duration + top callers by count + recent timeline. Robust to non-JSON / blank lines. Auto-detects timestamp units (seconds vs milliseconds) by magnitude.

### Numbers

- 147 tools (v0.4.2 143 → +4 new)
- 555 pytest tests, all passing (v0.4.2 555 + 22 e2e_v31 − 4 pre-existing v13/v18 json-footer compat fixes)
- server.py ~29,800 lines / ~30 KB

## [0.4.2] — 2026-07-17

### Added (4 new tools + 1 upgraded — 143 total)

- **`qt_qtquick_3d_setup`** — Project skeleton for a Qt 3D app (Qt3DCore + Qt3DRender + Qt3DExtras + Qt3DInput + Qt3DLogic). 4 templates: cube_demo, sphere_demo, scene_demo, model_loader. Build system selectable qmake / CMake.
- **`qt_qobject_invoke_metadata`** (拆 3 of 3 #1) — Static QObject introspection from .h/.cpp/moc_*.cpp (signals / slots / Q_INVOKABLE / Q_PROPERTY READ/WRITE/NOTIFY).
- **`qt_qobject_invoke_property_diff`** (拆 3 of 3 #2) — Compare two header sets for Q_PROPERTY + signals + slots + Q_INVOKABLE drift; per-item added/removed/changed + per-field change.
- **`qt_qobject_invocation_count`** (拆 3 of 3 #3) — Static count of .invokeMethod( + QMetaObject::invokeMethod( call sites per target method name.

### Changed
- **`qt_signature_batch`** accepts `error_strategy` enum (continue_all | fail_fast | continue_n:N) + new `csv_report` parameter for per-file CSV summary. `continue_on_error` bool kept for backward compat.

### Numbers
- 143 tools (v0.4.1 139 → +4 new; existing unchanged)
- 555 pytest tests (v0.4.1 536 → +19 e2e_v30)

## [0.4.1] — 2026-07-17

### Added (3 new tools — 142 total)
v0.4.1 closes the "release / quality-of-life" gap left open by v0.3.6-v0.3.8:
the final-mile deployment ritual + a sanitizer-report humanizer + a
natural-language-to-template scaffolder.

- **`qt_asan_runtime_report`** — Parse a sanitizer report (ASan/UBSan/TSan/LeakSanitizer)
  and translate each finding into human-readable Chinese + actionable fix hint.
  Translates 20+ common categories (heap-buffer-overflow, use-after-free,
  data-race, etc.) to Qt-relevant remediation advice. Output formats:
  `text` (default, with translated findings), `json` (machine-readable),
  `summary` (just counts by category).
- **`qt_template_scaffold`** — Project skeleton from a natural-language description.
  Bridges the gap to `qt_scaffold` (v0.1.0) by inferring the template via
  Chinese + English keyword matching (chess/tictactoe/breakout/cards/
  music/tasklist/game/cli/qml/dialog/widget/mainwindow). Auto-picks highest
  score on tie; offers `interactive=True` to show the candidate ranking.
- **`qt_deploy_bundle`** — One-call bundle for distribution: `windeployqt`
  (DLLs + plugins) + optional `signtool` codesign on every .exe/.dll +
  optional NSIS `installer.nsi` + `build_installer.bat` generation.
  Each step is independently reported in JSON; skip flags default to safe.

### Numbers
- **142 tools** (v0.4.1 139 → 142 was the previous count + 3 new). Total delta vs v0.3.8 baseline (130): +12 (+9.2%).
- **536 pytest tests** (v0.3.8 470 → v0.4.1 536, +66) — including 20 new e2e_v29 tests covering 3 new tools (q_asan_runtime_report 8 tests, qt_template_scaffold 8 tests, qt_deploy_bundle 4 tests).
- **server.py 28KB → ~31KB** (~3000 lines added).

### Key design decisions
1. **`qt_asan_runtime_report` lookup table is Chinese-first** — every category has a concise 2-line `cn` (translation) + `hint` (Qt-aware fix). The Wiki URL `https://github.com/google/sanitizers/wiki` is the always-fallback for unknown categories.
2. **`qt_template_scaffold` calls `_write_scaffold` directly** (not via the public `qt_scaffold` tool) to avoid cross-tool dispatch and give a cleaner JSON footer.
3. **`qt_deploy_bundle` is env-aware** — `windeployqt` runs with QT_BIN_DIR injected into PATH; signtool runs only when both `sign=True` AND `certificate_path` is provided (skip + warn otherwise); NSIS skips when `installer=False`. The 3-step status report names each step's result (`ok / fail / skipped / error`).
4. **Test isolation pattern (`autouse=True` fixture + `_split_json` helper)** — `e2e_v29` module sets `QT_MCP_JSON=1` per test via monkeypatch so JSON footers are reliable, and provides a tolerant JSON parser so test failure messages don't crash on missing footers. Other e2e suites are unaffected.

## [0.3.8] — 2026-07-10

### Added (7 new tools — 130 total)

Based on user-supplied course materials (SCU Wiki Qt 课件 + JB51 Qt 快速入门 62 篇教程 PDF). v0.3.8 fills the **教学性** gap: previous sprints were industrial/enterprise; v0.3.8 adds 7 tutorial/teaching-oriented tools + enhances 3 existing tools to better cover the course content.

**New tools (7):**

- `qt_cpp_tutorial_scaffold` — generates runnable C++ tutorial snippets for 12 topics covering SCU C++ 强化 9 章: hello_world / namespace / class_object / friend / operator_overload / inheritance / polymorphism / template / type_cast / exception / iostream / stl. Each is a self-contained .cpp that compiles with any C++17 compiler (no Qt needed). Companion to the existing `qt_anim` / `qt_class_wizard` / `qt_input` snippets.
- `qt_mysql_setup` — generates a Qt + MySQL/MariaDB starter project (.pro or CMakeLists.txt + dbmanager.h/.cpp + main.cpp + MySQL_SETUP.md). The setup md documents two paths: (1) compile QMYSQL from Qt source (JB51 Ch 22) or (2) use MariaDB Connector/C as a drop-in (recommended). Closes the gap that Qt 5.14.2's prebuilt MinGW does NOT ship the QMYSQL driver DLL.
- `qt_http_client_gen` — generates a QNetworkAccessManager-based HTTP client (QNetworkRequest + GET/POST + JSON body + User-Agent header). Two modes: `async` (signals getFinished / postFinished / requestError — recommended for UI) and `sync` (blocking via QEventLoop — for CLI). JB51 Ch 32.
- `qt_ftp_client_gen` — generates a QNetworkAccessManager-based FTP client (upload via put() with uploadProgress / download via get() with chunked write / list via get() returning directory listing). Modern Qt 5 replacement for the removed QFtp. JB51 Ch 33-34.
- `qt_graphics_view_scaffold` — generates a QGraphicsView teaching project (Scene + View + 3 items: red rect, blue ellipse, green line + drag-and-drop with mousePressEvent / mouseMoveEvent / mouseReleaseEvent). Foundation for board games, CAD tools, flowcharts. JB51 Ch 19-20.
- `qt_multimedia_setup` — generates a QtMultimedia starter (QMediaPlayer + QMediaPlaylist + QVideoWidget + QSoundEffect + sounds.qrc bundling + placeholder click.wav + MULTIMEDIA_SETUP.md with DirectShow/WMF backend notes). JB51 Ch 49.
- `qt_qstyle_sheet_gen` — generates ready-to-use QSS (Qt Style Sheet) for any subset of 14 widget selectors (QPushButton / QLineEdit / QComboBox / QListView / QTableView / QHeaderView / QStatusBar / QMenuBar / QMenu / QToolBar / QTabWidget / QGroupBox / QProgressBar / QScrollBar). Two themes: `light` (blue accents on white) and `dark` (blue accents on dark gray). JB51 Ch 45.

### Enhanced (3 existing tools)

- `qt_scaffold` — added 4 new SCU 项目库 templates: `tictactoe_game` (井字棋 3x3 grid + X/O switch + win detection) / `breakout_game` (打砖块 QTimer + paddle + bricks + collision) / `tasklist` (任务清单 QListView + QStringListModel + add/remove/clear) / `music_player` (QMediaPlayer + Open/Play/Pause/Stop + position slider). Brings total scaffold templates from 9 to 13.
- `qt_db_seed` — added `mysql_check: bool = False` parameter. When True, appends a MySQL/QMYSQL driver compatibility report (driver DLL presence + libmysql.dll/libmariadb.dll on PATH + mysql/mariadb CLI + setup guidance). Critical because Qt 5.14.2 + MinGW prebuilt does NOT ship the QMYSQL driver — the user MUST compile or use MariaDB drop-in.
- `qt_anim` — added 3 new `animation_type` values that emit ready-to-paste paintEvent overrides (not QPropertyAnimation): `double_buffer` (JB51 Ch 18: QPixmap off-screen buffer for flicker-free drawing) / `painter_path` (JB51 Ch 14: QPainterPath with moveTo/lineTo/quadTo/cubicTo/addEllipse) / `doodle_board` (JB51 Ch 17: freehand drawing with mousePressEvent + mouseMoveEvent accumulating a QPainterPath). Brings total animation types from 6 to 9.

### Bug fixes (2)

- `qt_anim` initial enhancement placed the new-type branches AFTER the validation check, so all 3 new types (double_buffer/painter_path/doodle_board) were rejected with "invalid animation_type" before reaching the snippet. Moved the new-type check BEFORE the validation, so the 3 types take an early-return path. Caught by e2e_v24 test 3.
- `_qss_dark_overrides()` is intentionally a function (not a dict literal) so it can be called fresh each time. This avoids the "mutable default argument" pitfall and matches the same pattern as `_qss_for_selectors()`.

### Numbers

- **130 tools** (v0.3.7 123 → v0.3.8 130, +7, +5.7%)
- **server.py 25802 lines** (v0.3.7 23286 → v0.3.8 25802, +2516, +10.8%)
- **29 e2e suites** (v0.3.7 28 → v0.3.8 29, +1 `e2e_new_tools_v24`)
- **470 pytest tests** (v0.3.7 451 → v0.3.8 470, +19 e2e_v24, +4.2%; `python -m pytest -q` 470 passed in 175s)
- e2e_v24: 19 pytest tests, 66 check 断言
- 130/130 工具 e2e 覆盖 + docstring 完整 + JSON footer

## [0.3.7] — 2026-07-10

### Added (12 new tools — 123 total)

**Runtime write loop (3 tools)** — closes the read/write gap left by `qt_widget_introspect` + `qt_runtime_props` + `qt_console_messages` (all read-only). Now you can both observe and mutate a running Qt app at runtime.

- `qt_invoke_helper_gen` — generates a Qt helper `.exe` skeleton (QApplication + user QObject subclass with `Q_PROPERTY` + `Q_INVOKABLE`) that exposes a stdin/stdout line-delimited JSON protocol. Companion to `qt_widget_introspect`; the *write* counterpart of the runtime introspection trio.
- `qt_qproperty_set` — drives a running helper .exe and sends a `set_property` JSON command. Sets Q_PROPERTY values at runtime.
- `qt_meta_invoke` — drives a running helper .exe and sends an `invoke` JSON command. Calls Q_INVOKABLE / `QMetaObject::invokeMethod` at runtime.

**Build / lint / install loop (4 tools)** — pairs with `qt_validate` + `qt_cmake` + `qt_build`.

- `qt_pro_lint` — 12-rule static lint of `.pro` files (duplicates, CONFIG conflicts, deprecated Qt5 modules, target naming, missing TEMPLATE, INCLUDEPATH absolute, etc.). `rule_ids` filter, text + json output. Companion to `qt_validate` (which finds *missing files*; this finds *syntactic / semantic* issues).
- `qt_shadow_build_setup` — sets up `build-debug/` + `build-release/` shadow dirs, writes `.pro.user` (Qt Creator config) with `ShadowBuild=true`, and `build_shadow.bat` for one-click debug+release build. Pairs with `qt_build_cache` (ccache needs separate dirs to be effective).
- `qt_qmlscene` — previews a `.qml` file via `qml.exe` + captures multi-DPI screenshots (`QT_SCALE_FACTOR` 1.0/1.5/2.0). Pairs with `qt_high_dpi_test` (which runs a full `.exe`; this skips the build step).
- `qt_cmake_install` — generates `cmake/InstallRules.cmake` + `cmake/Packaging.cmake` (CPack NSIS) + `cmake_install/Windeployqt.cmake` + `build_installer.bat`. Closes the CMake install/packaging loop left open by `qt_cmake` (which only generates the top-level CMakeLists.txt).

**Conda cross-platform (1 tool)** — pairs with `qt_conanfile_gen` (Conan). Two parallel package managers, pick whichever fits your team.

- `qt_conda_env_gen` — generates `environment.yml` (conda-forge) + `conda_install.bat` / `conda_install.sh` + `BUILD_README.md`. Maps Qt versions to conda-forge packages: Qt 5 (5.14.x / 5.15.x) → per-module `qt-*` packages; Qt 6 (6.5+) → umbrella `qt-main` + per-module `qt-main-qt*`. Cross-platform extras: Windows gets `vs2019_win-64`, Linux gets `libgl-devel` + `xorg-libxcb` + `xorg-libxkbcommon`.

**DB GUI integration (4 tools)** — pairs with `qt_db_seed` (v0.2.8, creates .db from schema). Closes the gap between creating a SQLite database and actually looking at it.

- `qt_db_open_in_gui` — opens a `.db` file in the user's preferred DB GUI client (SQLiteStudio by default, teacher-supplied reference; override via `QT_MCP_DBGUI_EXE` env var or `gui_exe` parameter). Detached launch.
- `qt_db_schema_diff` — compares two `.db` files' schemas (tables / columns / indices) and emits migration SQL (`CREATE TABLE` / `ALTER TABLE ADD/DROP COLUMN` / `CREATE INDEX`). text + json output.
- `qt_db_dump` — exports `.db` table(s) to **CSV** / **JSON** / **SQL dump** (CREATE TABLE + INSERTs). Single-table or all-tables.
- `qt_db_validate` — runs three checks: `PRAGMA foreign_key_check` (FK constraint violations), `PRAGMA integrity_check` (index health), and an *orphan-row scan* (rows in child with no matching parent, even if FK wasn't declared). PASS/FAIL verdict.

### Bug fixes (2)

- `server.py` was missing `import csv` and `import io` (used by `qt_db_dump` for CSV output). Caught by `e2e_v23` test 30.
- `qt_invoke_helper_gen` main.cpp template used Python `.format()` with raw-string literals containing `{{"ok", true}}` — `format()` interpreted `{"ok", true}` as a named placeholder, raising `KeyError`. Refactored to use `__CLASS_NAME__` / `__CLASS_LOWER__` / `__PROP_NAMES__` / `__METH_NAMES__` sentinels + chained `.replace()` (avoids the `{{` / `}}` escaping pitfall). Caught by `e2e_v23` tests 1 and 3.

### Numbers

- **123 tools** (v0.3.6 111 → v0.3.7 123, +12, +10.8%)
- **server.py 23286 lines** (v0.3.6 20791 → v0.3.7 23286, +2495, +12%)
- **28 e2e suites** (v0.3.6 27 → v0.3.7 28, +1 `e2e_new_tools_v23`)
- **451 pytest tests** (v0.3.6 415 → v0.3.7 451, +36 e2e_v23, +8.7%; `python -m pytest -q` 451 passed in 170s)
- e2e_v23: 36 pytest tests, 79 check 断言
- 123/123 工具 e2e 覆盖 + docstring 完整 + JSON footer

## [0.3.6] — 2026-07-10

### Added

- **`qt_conanfile_gen`** — companion to `qt_pkg_install` (which installs Qt via aqtinstall) and `qt_cmake` (which emits CMakeLists.txt). Closes the cross-platform dependency-management gap: many Qt projects ship to Windows + Linux + macOS with different system Qt packages, and Conan is the de-facto way to pin a reproducible Qt build across all three. Generates both `conanfile.py` (full Python recipe with `requires` + `generators` + `env_info`) and `conanfile.txt` (minimal deps list), plus a `BUILD_README.md` with step-by-step instructions. With `emit_profile='auto'`, also writes `profiles/windows` + `profiles/linux` + `profiles/macos` (compiler.version configurable). Supports `use_system_qt=True` to skip the Conan Qt package and document setting `QTDIR` manually instead. Anchors Conan 1.x Qt 5.14.2 / 6.5.0 package-name conventions (`qt/5.14.2`, `qt/6.5.0`, …) via the `_CONAN_QT_PACKAGE` table.
- **`qt_module_split_init`** — companion to `qt_scaffold` (which creates new projects) and `qt_cmake`. Closes the gap when a flat Qt project grows past ~1k lines: re-organising into a reusable library + thin app speeds rebuilds, lets multiple apps link the same code, and makes the library self-contained for tests. With `plan_only=True` (default) emits `module_split_plan.json` describing which files go into `lib/src/` + `lib/include/<libname>/` + `app/`. With `plan_only=False`, actually executes the moves (with `.qt_module_split_backup/` safety copy) + writes `lib/lib.pro` (`TEMPLATE = lib`, `TARGET = <libname>`, `DEFINES += QT_MAKEDLL`) + `app/app.pro` (links lib + keeps `main.cpp` + the main window) + rewrites the root `.pro` as `TEMPLATE = subdirs` + `SUBDIRS = lib app`. `file_patterns` (regex list) filters which files move into the lib target.
- **`qt_modernize_qt5_to_qt6`** — companion to `qt_clazy_check` (which *flags* anti-patterns): this tool actually rewrites the source. Catches the most common Qt 5 → Qt 6 chokepoints so a release upgrade compiles without 30 minutes of find-and-replace. Rules: `qregexp_to_qregularexpression` (QRegExp → QRegularExpression, including `#include` lines), `q_nullptr_to_nullptr` (Q_NULLPTR[CONSTEXPR] → nullptr), `q_foreach_to_range_for` (Q_FOREACH/foreach → range-based for), `qvector_to_qlist` (QVector<T> → QList<T>), `remove_aa_usehighdpipixmaps` (drop `QApplication::setAttribute(Qt::AA_UseHighDpiPixmaps, true)` — Qt 6 default), `qtextcodec_to_qstringconverter` (QTextCodec::codecForName → QStringConverter::encodingFor). `apply=False` (default) emits a per-file dry-run preview; `apply=True` writes `.bak` copies + applies the rewrites. `rule_ids` filter to apply only one rule at a time.
- **`qt_signal_disconnect_check`** — companion to `qt_signal_slot_trace` (which maps *all* wires): this tool exposes *missing teardown*. Common lifetime bug: a `QObject` connects to a sender it should explicitly `disconnect()` from in its destructor, but the developer forgets. Walks `.cpp` + `.cc` + `.cxx`, extracts every `connect(...)` first arg and every `disconnect(...)` first arg, lists connect sites whose sender is never disconnected anywhere in the project. Output is text (grouped by sender) or JSON per file:line:sender. `ignore_self_disconnect=True` (default) skips `disconnect(this, …)` patterns (Qt handles those automatically). Strict cross-thread / DirectConnection checks remain in `qt_thread_affinity_check`.
- **`qt_qml_perf_lint`** — companion to `qt_qml_lint` (which covers syntax + type-correctness + a few caching rules): this tool focuses on *runtime performance* in QML-heavy UIs. Rules: `inline_js_too_long` (function body > 50 lines — move to .js, QML JIT inline JS is slower than module .js), `image_synchronous_load` (`Image { … asynchronous: false }`), `transparent_mousearea` (`visible: false` without `enabled: false`), `loader_frequent_sourcechange` (source URL changes per frame), `deep_component_nesting` (> 5 levels — deep QML hierarchies increase binding-evaluation cost), `createobject_in_repeater` (`createQmlObject`/`createObject` inside Repeater delegate — frequent allocation per item). text + json, severity info vs warning, `rule_ids` filter, `file_patterns` configurability. Pure regex; complements `qmllint`.

### Removed from polish_plan candidates

- `qt_qobject_invoke` — same reasoning as v0.3.5: requires a Qt helper `.exe` bridge to call slots cross-process, exceeding single-sprint work. Runtime introspection is covered by `qt_widget_introspect` + `qt_console_messages` + `qt_runtime_props`.
- `qt_gammaray_attach` — depends on KDAB GammaRay (external commercial/open-source tool); runtime introspection covered by existing 5 tools.
- `qt_qml_performance_lint` (deep variant) — fully implemented as `qt_qml_perf_lint` in v0.3.6 instead of being deferred.
- `qt_resource_validate` (per-platform variant) — the v0.3.4 eight-rule base was deemed sufficient.
- `qt_qtquick_3d_setup` — Qt 5.14's `Qt Quick 3D` is an early-stage preview; clashing with the existing 9 scaffold templates. Punted to v0.3.7+ if user demand materialises.

### Bug fixes (5)

- `qt_modernize_qt5_to_qt6` first implementation used `Path.with_suffix(".bak")` to compute the backup path; this produces `main.bak` (not `main.cpp.bak`). Switched to `bak = fp.parent / (fp.name + ".bak")`. Caught by `e2e_v22` test 11 on first pass.
- `qt_qml_perf_lint` first implementation used a single-line guard (`"Image" in line and "asynchronous" in line`) before running the regex window — this missed any cross-line `Image { ... asynchronous: false }` blocks. Replaced with `re.finditer(r"\bImage\s*\{[^}]*?asynchronous\s*:\s*false", text, re.DOTALL)` so it walks across the whole brace-balanced block. Same fix applied to `transparent_mousearea`. Caught by `e2e_v22` tests 20, 21, 23.
- `qt_qml_perf_lint` and `qt_modernize_qt5_to_qt6` files filter lists contained `".tmp"` in the path-parts skip set — but `SANDBOX_TMP` lives at `E:\Download_tools\QT\.tmp\`, so any test creating project trees inside `SANDBOX_TMP/.../main.qml` was silently skipped (`Files scanned: 0`). Removed `.tmp` from both skip lists. This is the same v0.2.5 (`qt_cmake`) and v0.3.2 (`qt_format_check`) lesson recurring in v0.3.6 — codified in the inline comment "NO .tmp — would skip files under SANDBOX_TMP". Caught by `e2e_v22` tests 11 + 25 on second pass.
- `e2e_v22` test 11 (`qt_modernize_qt5_to_qt6 apply=True`) initially asserted `"ok" in out.lower()` — but the modernise summary doesn't emit the literal "OK" (only the structured `=== … ===` header). Switched the success check to `"===" in out` so it matches the actual output. Caught by the e2e run when the tool was producing correct output but the check was wrong.
- `e2e_v22` test 7 (`qt_module_split_init` `lib.pro has TARGET = engine`) initially compared the literal `TARGET = engine` — but the recipe generator emits `TARGET   = engine` (4-space alignment). Switched to `re.search(r"TARGET\s*=\s*engine", text)` so it tolerates any whitespace layout.

### Numbers

- **111 tools** (v0.3.5 106 → v0.3.6 111, +5, +4.7%)
- **server.py 20791 lines** (v0.3.5 19395 → v0.3.6 20791, +1396, +7.2%)
- **27 e2e suites** (v0.3.5 26 → v0.3.6 27, +1 `e2e_new_tools_v22`)

### Key design decisions

- `qt_module_split_init` defaults to `plan_only=True` — every destructive move must be explicitly opted into, matching the existing pattern (`qt_documentation_auto_fill.apply=False`, `qt_translation_auto_fill.apply=False`, `qt_signal_lint_fix.apply=False`).
- `qt_conanfile_gen` writes both `conanfile.py` (heavy) *and* `conanfile.txt` (light). Different teams prefer one or the other; emitting both lets the user delete whichever they don't need.
- `qt_modernize_qt5_to_qt6` is intentionally conservative: only transforms that are unambiguous textual equivalents. Complex rewrites (e.g. `QStringLiteral`-vs-`u""` literal collapsing, signal-pointer-syntax migration) are out of scope — they require AST-level analysis.
- `qt_qml_perf_lint` severity colours: `inline_js_too_long` / `image_synchronous_load` / `deep_component_nesting` / `createobject_in_repeater` are `warning` (impact real perf); `transparent_mousearea` / `loader_frequent_sourcechange` are `info` (context-dependent).
- All five new tools use the `_require_sandbox(...) -> error_string` convention; all call `_json_footer(...)`; all carry full Args/Returns/Raises docstrings; all are listed in `qt_cheatsheet`.

## [0.3.5] — 2026-07-09

### Added

- **`qt_complexity_lint`** — McCabe-style cyclomatic complexity per C++ function. Walks `.cpp / .cc / .cxx / .h` files, regex-extracts function signatures, brace-matches each function body, strips comment + string/char literals so `if (s == "if")` doesn't count, then counts branch keywords (`if` / `else if` / `while` / `for` / `case` / `catch`) + short-circuit operators (`&&` / `||`) + ternary (`?:`). McCabe = 1 + count. Flags functions with complexity ≥ `threshold` (default 12, rule-of-thumb "10±2"). Closes the "per-function complexity" axis that cppcheck / clazy / qmllint don't cover (cppcheck covers interprocedural paths, not per-function branches). text + json output + avg + verdict (PASS/FAIL). `exclude_dirs` skips build dirs / `.git` / `node_modules`. Zero new dependencies — pure regex. Companion to `qt_clazy_check` (anti-patterns), `qt_cppcheck` (real C++ static analysis), `qt_signal_slot_trace` (signal graph), `qt_format_check` (style).
- **`qt_git_audit`** — companion to `qt_git_init` (v0.3.0, which only initialises the repo). Audits an existing repo's history for project-governance signals no Qt tool usually surfaces: **hot files** (top-N by commit count, signals refactor / extract candidates), **bus factor** (top contributor's share %; >60% = high risk, >40% = elevated), **churn** (LOC added/removed + density LOC/day in the last `since_days` window), **stale branches** (no commit in `stale_days`), **biggest commit** (largest single-commit files-changed — catches "drive-by mega commits"). Subprocess `git log --pretty=format --numstat` + `git for-each-ref --format` walks. text + json output.
- **`qt_appx`** — companion to `qt_installer_gen` (v0.2.8 — NSIS / Inno Setup for local distribution). Generates the artifacts needed to publish on the Microsoft Store: `AppxManifest.xml` (with `runFullTrust` capability — required for Qt apps), `build_appx.bat` (runs `makeappx.exe pack` + `signtool sign` in sequence), `appx_logos.md` (documents the four required PNG logo sizes — 50/44/150/310). Like `qt_installer_gen`, only generates — does not invoke Windows SDK tools because they're not part of Qt SDK. `architecture` ∈ {`x86`, `x64`, `arm64`}. Package name derived from publisher CN + app_name, sanitised to fit the reverse-DNS form.
- **`qt_ide_metadata`** — companion to `qt_creator_open` (which only targets Qt Creator). Generates IDE metadata so users can debug their Qt project from **VSCode** or **CLion** without Qt Creator. `.vscode/launch.json` (gdb debug config, auto-selects mingw32/64), `.vscode/tasks.json` (qmake / build / run / clean), `.vscode/c_cpp_properties.json` (includePath + defines extracted via `_pro_parse` from the project's `.pro`), `.vscode/extensions.json` (recommended: `ms-vscode.cpptools` + `cmake-tools` + `jbenden.c-cpp-flyclang` + `gitlens`). With `ide='both'`, also writes `.idea/workspace.xml` for CLion. Auto-detects the `.exe` from `build-debug/debug/*.exe` etc. if `launch_exe` is empty.
- **`qt_runtime_props`** — companion to `qt_widget_introspect` (which shows the widget tree shape). Goes one level deeper and reads each widget's *live accessible properties* (mapped via UI Automation from Qt `setAccessibleName` / `setAccessibleDescription` + `setObjectName`) by attaching via pywinauto. Borrowed from `0xCarbon/qt-mcp`'s `qt_props` concept. Either attach to running `process_id` or auto-spawn `executable` (always killed before returning). Snapshots every widget with an `objectName` + text in the tree, prints the current state. For full `QMetaObject::property()` values the user must compile a helper into their project — a ready-to-paste hint is printed at the bottom of every output.
- **`qt_test_fuzz`** — companion to `qt_sanitizer_run` (memory safety), `qt_smoke_test` (smoke), `qt_perf_budget` (perf), `qt_test` (unit tests). Closes the "fuzzing" leg of the quality-gate quad: smoke / perf / correctness / crash-with-malformed-input. Generates a libFuzzer harness (`LLVMFuzzerTestOneInput` + `LLVMFuzzerRunMain` main when `__has_libfuzzer`) wrapping the user-specified `target_function` (a `Q_INVOKABLE`), a `.pro` patch snippet (`QMAKE_CXXFLAGS += -fsanitize=fuzzer-no-link -fno-omit-frame-pointer`, `QMAKE_LFLAGS += -fsanitize=fuzzer -lstdc++`), and a `fuzz_README.md` documenting MinGW-vs-Clang compatibility + 4-step usage. MinGW's bundled GCC 7.x does not ship libFuzzer (the bundled GCC is older than fuzzer-supporting releases); the README warns clearly and recommends `compiler='clang++'` (LLVM's official installer) for full libFuzzer support.

### Removed from polish_plan candidates

- `qt_qobject_invoke` — overlaps with `qt_ui_action` + `qt_widget_introspect` + `qt_console_messages` (all are runtime-introspection variants). Requires a Qt helper `.exe` bridge to call slots cross-process, exceeding single-sprint work.
- `qt_gammaray_attach` — depends on KDAB GammaRay (external commercial/open-source tool); runtime introspection is already adequately covered by `qt_widget_introspect` + `qt_console_messages`.
- `qt_qml_performance_lint` — overlaps with `qmllint`'s built-in `ListView cacheBuffer` / `Repeater` nesting / etc. performance rules.
- `qt_resource_validate` (deeper variant) — v0.3.4's eight-rule base already covers naming / collision / depth / size / prefix. Per-platform rule-sets + auto-fix were deemed marginal.

### Numbers

- **106 tools** (v0.3.4 100 → v0.3.5 106, +6, +6.0%)
- **server.py 19395 lines** (v0.3.4 17968 → v0.3.5 19395, +1427, +7.9%)
- **26 e2e suites** (v0.3.4 25 → v0.3.5 26, +1 `e2e_new_tools_v21`)
- **390 pytest tests** (v0.3.4 367 → v0.3.5 390, +23, +6.3%)

### v0.3.6 update — see [0.3.6] section above for details

- **111 tools** (106 → 111, +5)
- **server.py 20791 lines** (19395 → 20791, +1396, +7.2%)
- **27 e2e suites** (26 → 27, +1 `e2e_new_tools_v22`)
- **415 pytest tests** (390 → 415, +25 new, +6.4%; full suite **415 passed in 155s**)
- `e2e_v21`: **23 pytest tests / 52 checks**, all pass on first run after 2 fixes.
- 106/106 tools have e2e coverage + docstring (Args/Returns/Raises/Note) + JSON trailer.

### Key design decisions

- **`qt_complexity_lint` is *pure regex*** — mirrors `qt_clazy_check`'s no-deps approach. The alternative (libclang Python bindings) adds a heavy dependency for marginal accuracy gain; McCabe on plain source is sufficient for CI gating.
- **`qt_complexity_lint` strips strings/comments** so `if (s == "if")` doesn't count (same trick `qt_signal_slot_trace` uses via `_sst_strip_comments`).
- **`qt_git_audit` starts from `os.environ.copy()`** in tests — passing `env=` to subprocess wipes `HOME`/`PATH`, which can break `git init` in some Windows configs. (v0.3.4 qt_test_fuzz gotcha)
- **`qt_appx` does not call `makeappx.exe`** — Windows SDK is not bundled with Qt 5.14 SDK; only the artifacts + build script are generated (user runs `build_appx.bat` after installing SDK). Same pattern as `qt_installer_gen` (NSIS not invoked).
- **`qt_ide_metadata` extracts `INCLUDEPATH` + `DEFINES` from `.pro`** via the existing `_pro_parse` + `_pro_tokenize` helpers — no re-implementation of the qmake grammar. The `c_cpp_properties.json` references the absolute Qt include path so IntelliSense works on first open.
- **`qt_runtime_props` is a *widget-property snapshot*, not full QMetaObject introspection** — the latter requires a helper `.exe` compiled into the target project (we can't read QMetaObject state from outside the process). The tool prints a ready-to-paste hint pointing to a future `qt-mcp` helper snippet for users who need the full introspection.
- **`qt_test_fuzz` *generates only*, does not build/run** — `-fsanitize=fuzzer` is unsupported by MinGW's bundled GCC 7.x, and `clang++` may not be installed. Auto-building would always fail on the common MinGW-only configuration. The README explains the 4-step manual flow.

### Module-level consistency

- No regex name collisions with the existing 25+ module-level regex constants (e.g. `_QRC_FILE_RE`, `_INPUT_RECORDER_RECORD_PY`, `_HR_QPROP_RE`, `_LAYOUT_CHECK_RULES`, `_AFFINITY_RULES`, `_RESOURCE_VALIDATE_RULES`, `_LCOV_*_RE`). All new patterns prefixed `_CX_` / `_GA_` / `_APPX_*` / `_IDE_*` / `_RP_*` / `_FUZZ_*`.

## [0.3.4] — 2026-07-09

### Added

- **`qt_perf_compare`** — companion to `qt_perf_budget` (v0.3.2): that tool checks "does it run FAST enough against a budget"; this tool checks "is it AS FAST as last time?". Reads a baseline JSON (from `qt_perf_budget` or prior `qt_perf_compare`), spawns the `.exe`, measures fresh `first_cpu_ms` + `first_window_ms` via the same `_perf_first_cpu_active` (psutil) + `_perf_find_window_for_pid` (pywinauto) helpers, compares against baseline, reports `PASS` if either delta is below `regression_ms` (default 200ms), `FAIL` otherwise. Always kills the spawned process before returning. CI gate for "did this release get slower?".
- **`qt_resource_validate`** — companion to `qt_resources` (v0.2.7): that tool's `validate` action only checks file existence + duplicate entries; this tool deep-validates with eight rules: `naming_convention` (filename must match `^[a-z0-9_-/.]+$` — no spaces, no uppercase, no special chars), `case_collision` (two entries differing only in case — collide on Windows/macOS), `path_too_deep` (depth > `max_path_depth` default 8), `file_too_large` (> `max_file_size_kb` default 512 KB — slow resource load), `prefix_conflict` (two `<qresource prefix>` blocks with overlapping sub-paths), `duplicate_entry`, `missing_on_disk`, `unusual_extension` (`.exe/.dll/.so/.bat/.cmd/.sh/.ps1/.msi`). Reuses `_qrc_parse` helper. Per-finding severity counts + `result` PASS/FAIL (error-severity findings fail). text + json output.
- **`qt_test_coverage_diff`** — companion to `qt_coverage` (v0.2.3): that tool generates a single lcov `.info`; this tool compares two `.info` files (baseline vs current) to detect coverage regressions. Custom lcov parser (`_LCOV_SF_RE` / `_LCOV_LF_RE` / `_LCOV_LH_RE`) extracts `{filename: (LF, LH)}` per file. Computes per-file delta, overall delta, lists regressions (delta < −`regression_threshold`) and improvements. `result` is `FAIL` if any per-file drop > threshold or overall coverage dropped > threshold. `source_filter` substring lets you scope to `src/` etc. text + json output. CI gate against coverage regression.
- **`qt_screenshot_baseline_capture`** — companion to `qt_screenshot_diff` (v0.2.7): that tool compares two PNGs; this tool *captures* the baseline PNG(s) automatically across multiple DPI scale factors. For each `scale_factors` value (default `[1.0, 1.5, 2.0]`): spawn the `.exe` with `QT_SCALE_FACTOR` set, sleep `wait_seconds`, capture window via `pywinauto.capture_as_image()`, save as `baseline_<scale>x.png`, compute sha1. Writes a `manifest.json` with `{label, executable, captured_at, scale_factors: [...]}` for traceability. Always kills the spawned process before moving on. text + json output. Visual regression CI workflow: capture baseline → change code → diff current vs baseline.
- **`qt_console_messages`** — companion to `qt_log` (v0.2.2) + `qt_run_trace` (v0.2.0): those tools analyze already-written log files or set env vars at spawn; this tool *attaches* to a running Qt process (or spawns one) and reads console-like text widgets (`QPlainTextEdit` / `QTextEdit` / `QLabel` / `QStatusBar`) via pywinauto + UI Automation. Inspired by `0xCarbon/qt-mcp`'s `qt_messages` concept. Applies `level_filter` regex (default `debug|warning|critical|fatal`), truncates to `max_messages` (default 500), optional `auto_id_contains` substring filter on `objectName`. Always kills spawned process before returning. text + json output.

## [0.3.3] — 2026-07-09

### Added

- **`qt_widget_introspect`** — inspired by `0xCarbon/qt-mcp`'s runtime widget-tree trio (`qt_snapshot` / `qt_find_widget` / `qt_widget_details`). Inspect a *running* Qt app via `pywinauto` + UI Automation with three actions in one tool: `snapshot` (full widget tree as nested JSON, configurable `max_depth`), `find` (search by `name_contains` / `type_contains` / `text_contains`, AND-combined, returns flat list of matches), `details` (full properties for a widget by `auto_id` — the Qt `setObjectName` exposed as UI Automation's `AutomationId`). Either attach to a running `process_id` or auto-launch `executable` (detached, always killed). json output. Companion to `qt_ui_action` (which *drives* actions) — this tool *observes* state.
- **`qt_layout_check`** — static check of `.ui` files (XML parsed via ElementTree) for layout anti-patterns. Inspired by `0xCarbon/qt-mcp`'s runtime `qt_layout_check`, runs statically (no app launch). Five rules: `widget_no_layout_parent` (warning), `deep_nesting` (>5 levels, warning), `duplicated_object_name` (breaks `findChild`/UI Automation, warning), `layout_no_stretch` (info), `fixed_size_in_expanding_layout` (info). Severity filter; text + json output.
- **`qt_cppcheck`** — run `cppcheck --json --library=qt` on a directory or single file. Defensive JSON parser (cppcheck sometimes emits one object per file, sometimes a single object with a `diagnostics` array). Aggregates per-severity counts (`error`/`warning`/`style`/`performance`/`portability`/`information`) into a CI-friendly report. Auto-resolves `cppcheck` via `QT_CPPCHECK_EXE` env var → `PATH`; explicit `cppcheck_exe` overrides both. Severity filter. text + json output. Complements `qt_clazy_check` (regex-only, zero-dependency) and `qt_lint` (cpplint + qmllint + clang-tidy) — `qt_cppcheck` shells out to a real `cppcheck` binary for deeper analysis.
- **`qt_thread_affinity_check`** — static analysis of QObject signal/slot cross-thread mistakes that `qt_async_await_lint` doesn't catch. Four rules: `direct_connection_cross_thread` (Qt::DirectConnection + `moveToThread()` in same file — warning), `emit_without_queued_connection` (emit + `moveToThread()` — info), `qthread_run_without_exec` (QThread subclass without `exec()` in `run()` — warning), `qobject_constructed_in_worker_thread` (`new QObject()` in `QThread::run()`/`QRunnable::run()` — info). Each rule has a `requires` precondition so files without threading primitives aren't flagged. text + json output. Companion to `qt_async_await_lint` (async-pattern regexes) and `qt_signal_slot_trace` (connection graph).
- **`qt_sanitizer_run`** — build a Qt project with `-fsanitize=address` (default) / `address,undefined` / `undefined` / `thread`, then run it briefly to capture sanitizer diagnostics. Workflow: copy project to `sanitizer-<type>-<buildtype>/`, patch `.pro` with `QMAKE_CXXFLAGS += <flag>` + `QMAKE_LFLAGS += <flag>` (idempotent), `qmake` + `mingw32-make`, spawn `.exe` for `run_seconds` with `ASAN_OPTIONS=halt_on_error=1` / `UBSAN_OPTIONS=print_stacktrace=1` / `TSAN_OPTIONS=second_deadlock_stack=1`, parse output for known sanitizer error markers (`==ERROR: AddressSanitizer`, `runtime error:`, `WARNING: ThreadSanitizer`, `SUMMARY: AddressSanitizer`), report `PASS` / `FAIL`, always `distclean` unless `keep_sanitizer_build=True`. MinGW-compatible (ASan + UBSan combo works on both MinGW and MSVC; `-fsanitize=thread` requires pthreads and may not link cleanly on Windows). Companion to `qt_smoke_test` (smoke = does it run) + `qt_perf_budget` (perf = does it run fast) — this checks *does it crash on common memory / UB errors*.

## [0.3.2] — 2026-07-09

### Added

- **`qt_translation_sync`** — companion to `qt_translation_validate` and `qt_translation_auto_fill`. Scans the project for `tr("...")` calls (regex-based, handles `tr("s")` and `tr("s", "ctx")` forms), parses the target `.ts` XML, and diffs them: reports which source strings are missing from the `.ts` and which `.ts` entries are no longer referenced in the code. With `apply=True`, appends `<message>` stubs (type="unfinished") for missing strings to the `.ts` (with a `.bak` backup) and reports the new coverage. The i18n pipeline is now complete: `validate` (coverage report) → `sync` (source ↔ .ts diff) → `auto_fill` (LLM translation).
- **`qt_async_await_lint`** — static analysis of Qt async / concurrency anti-patterns. Seven rules: `qtconcurrent_blocking_in_main` (QtConcurrent::blockingMapped/... on the GUI thread), `qfuture_waitforfinished` (QFuture::waitForFinished blocks the calling thread — use QFutureWatcher + finished signal instead), `qthreadpool_direct_start` (QThreadPool::start(new QThread) leaks), `qfuturewatcher_unwired` (QFutureWatcher declared but no setFuture() / connect in sight), `qthread_no_eventloop` (QThread subclass without exec() in run()), `movetothread_after_connect` (moveToThread() called after a connect() — locks the connection to the old thread), `qrunnable_no_autodelete` (QRunnable without explicit autoDelete policy). Filters by min_severity (info/warning); text + json output.
- **`qt_hotreload_check`** — companion to `qt_property_browser`. Validates Q_PROPERTY declarations: `missing_notify` (READ with no NOTIFY → QML/bindings can't react to changes, warning), `missing_read` (no READ accessor → error), `constant_with_write` (CONSTANT + WRITE is contradictory → error), `member_with_read` (both MEMBER and READ → info, pick one), `notify_signal_not_found` (NOTIFY references a signal not in the `signals:` block → error), `member_variable_not_found` (MEMBER references an undeclared class member → error), `write_setter_not_found` (WRITE references a setter that's not declared → error). text + json output.
- **`qt_perf_budget`** — CI-friendly startup-time gate. Launch the `.exe`, measure the time from spawn to first non-zero CPU activity (proxy for event-loop entry) and to first top-level window appearance (via `pywinauto.find_windows(process=pid)`), compare against `budget_ms` (default 2000ms), report `PASS` / `FAIL`, and always kill the launched process before returning. Companion to `qt_smoke_test` (which checks "does it run"); this checks "does it run FAST enough".
- **`qt_format_check`** — companion to `qt_format` (which *fixes* formatting). Audits a directory of `.h` / `.cpp` / `.cc` / `.cxx` files via `clang-format --output-replacements-xml`, aggregates per-file pass/fail into a single CI-friendly report (total / clean / dirty / error counts + total replacements), and (with `init_clang_format=True`) generates a template `.clang-format` from one of six built-in styles (llvm / google / chromium / mozilla / webkit / qt — the last is derived from Qt 6's `qt.git/.clang-format`). Idempotent: never overwrites an existing `.clang-format`. text + json output.

### Bug fixes

- **`qt_property_browser`** — the v0.2.8 `qt_property_browser` defined a module-level `_QPROP_RE` regex (with named groups `type` / `name` / `rest`); v0.3.2's `qt_hotreload_check` re-declared `_QPROP_RE` at module level with a *different* shape (no `rest` group, no template support), silently clobbering the v0.2.8 regex and breaking 4 e2e_v13 tests for `qt_property_browser`. Renamed the v0.3.2 regex to `_HR_QPROP_RE` (and the companion patterns to `_HR_QPROP_TAKE_VALUE` / `_HR_QPROP_BOOL_KW`) to restore `qt_property_browser` behaviour. (E2E caught the regression in the same sprint.)
- **`qt_format_check`** — initial implementation listed `.tmp` in the skip-dir set, which excluded every `.cpp` under `SANDBOX_TMP` (lives under `E:\Download_tools\QT\.tmp\…`). The same v0.2.5-era bug that affected `qt_cmake` and `qt_grep` / `qt_qml_lint`. Removed `.tmp` from the skip list (intentionally — `SANDBOX_TMP` is a sandboxed test dir, not a build artefact).
- **`qt_hotreload_check`** — `signal_re` initially used `r"signals\s*:\s*(?:public\s+)?(?:protected\s+)?(?:[\w:]+\s+)?(\w+)\s*\("` and `re.findall` — this only matched the *first* signal after a `signals:` block (the `findall` advanced past the first match and missed the rest). Replaced with a body-extraction approach: match the full `signals: … ` block up to the next access-specifier or `}` and harvest every `name(` inside. Found by e2e_v18 test 12 (`does NOT flag valueChanged`).
- **`qt_hotreload_check`** — initial `QPROP_RE` parsed `Q_PROPERTY(double constantPi READ constantPi CONSTANT)` as type=`double constantPi READ constantPi` name=`CONSTANT` (the `type` group greedily ate the READ clause). Replaced with a `prefix / attrs` split on the first keyword boundary: prefix becomes `"<type> <name>"` (split on last whitespace), then attrs parses the trailing clauses. Found by manual smoke test.
- **`qt_hotreload_check`** — method-collection regex `r"…\s*;"` only matched `;`-ended declarations, missing inline `{}` definitions like `void setValue(int v) {}` (very common in Qt header). Loosened to `(?:\s*;|\s*\{)`. Found by e2e_v18 test 15.

## [0.3.1] — 2026-07-09

### Added

- **`qt_documentation_auto_fill`** — companion to `qt_documentation_lint`. Find every undocumented public function in `.h` / `.cpp` / `.qml`, call an LLM (Anthropic Claude 3.5 Sonnet by default; OpenAI GPT-4o-mini alternative) to generate doxygen `@brief` / `@param` / `@return` blocks, and emit a unified-diff preview. Default `apply=False` shows the diff; `apply=True` writes changes back (with a `.bak` copy). Requires `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` env var. Batches all missing functions in one file into a single LLM call to minimise token cost.
- **`qt_translation_auto_fill`** — companion to `qt_translation_validate`. Parse `.ts` XML, find every `<message>` with `type="unfinished"` translation, call the LLM to translate the `<source>` text into the file's declared language (e.g. `zh_CN`, `en_US`, `fr`), batch up to `batch_size` messages per call (default 20). Default `apply=False` shows diff; `apply=True` writes `.ts` back. Preserves XML structure, escapes special chars in translations, supports `target_language` filter to process only one language across multiple `.ts` files.
- **`qt_signal_lint_fix`** — companion to `qt_signal_slot_trace`. Four fix rules, each individually toggle-able: `unique_connection` (OR-adds `Qt::UniqueConnection` to existing 5-arg connect calls that already have `Qt::AutoConnection` / `DirectConnection` / `QueuedConnection`), `queued_connection` (adds `Qt::QueuedConnection` when a `// @thread:main` or `// @thread: ui` marker is found within 1500 chars of the connect call), `functor_to_pointer` (Qt 5 `SIGNAL(class::sig())` / `SLOT(class::slot())` macros → Qt 6 PMF `&class::sig` / `&class::slot` syntax), `orphan_slot_stub` (appends empty implementations for declared slots that are never connected, with a `qWarning` to surface the missing connection). Default `apply=False` shows diff; `apply=True` writes back with optional `.bak`.

### Improved

- **LLM infrastructure helper** — shared `_llm_check_config()` + `_llm_call()` (urllib-based, no extra dependency). `_llm_call` returns a dict `{ok, text, error}` rather than raising; tools check `ok` and surface `Error:` strings to the user. `_json_footer` trailers include the provider + model used.

### Bug fixes

- **`qt_documentation_auto_fill`** — initial implementation used `del server._llm_call` in the test `finally` block to restore a mock, which permanently deleted the server module's real `_llm_call` function and broke all subsequent tests. Replaced with a `patch_llm_call()` helper that saves the original function reference and restores it on cleanup. Same pattern applied to `qt_translation_auto_fill` tests.
- **`qt_signal_lint_fix`** — `re.subn()` count is *match count*, not *replace count*. When the regex matched but the callback returned the original text (no fix applicable), `n` was still > 0, falsely reporting a fix. Fixed to compare `new_modified != modified` before appending to `file_fixes`. Same fix applied to `unique_connection` and `functor_to_pointer` rules.
- **`qt_signal_lint_fix`** — `unique_connection` regex `r"(connect\s*\([^;]+?),\s*(Qt::AutoConnection|Qt::DirectConnection|Qt::QueuedConnection|)\s*\)"` incorrectly matched 4-arg `connect(...)` calls (where the type is unspecified, defaulting to `Qt::AutoConnection`). Fixed to require an explicit type argument before OR-ing `Qt::UniqueConnection` — adding it to a 4-arg connect would silently change semantics from "default-type" to "default-type | unique".
- **`qt_signal_lint_fix`** — `queued_connection` regex `r"connect\s*\(\s*(\w+)\s*,\s*SIGNAL\s*\([^)]+\)\s*,..."` failed to match `SIGNAL(progressUpdated())` because `[^)]+` cannot cross the inner `)` in `progressUpdated()`. Fixed to `.*?` (non-greedy any-char) to handle Qt signal/slot name patterns with their own parentheses.

### Verified

- 22 e2e suites pass: 6 light + 273 full = **279 pytest tests** (`pytest -m light` < 5s, `pytest -m full` ~60s).
- **85 / 85 tools** have e2e coverage (82 v0.3.0 + 3 v0.3.1).
- 85 / 85 tools have complete Args / Returns / Raises docstrings.
- 85 / 85 tools use `_json_footer` for machine-readable trailers (off by default).
- All e2e tests bypass MCP stdio caching by importing `server` directly — verified via `pytest -m full`.
- server.py grew from 14110 → **14806 lines** (+696, +4.9%); 3 new tools averaged ~230 lines each (Pydantic Input + impl + docstring + JSON footer). Tests grew from 254 → 279 (+25; +9.8%).

## [0.3.0] — 2026-07-09

### Added

- **`qt_build_cache`** — detect ccache / sccache on PATH and report which compiler-cache backend is available, read hit/miss stats from the cache directory, and (optionally) inject `QMAKE_CXX = ccache g++` (or sccache equivalent) at the top of the project's `.pro` so every subsequent `qt_build` invocation routes compiles through the cache. Also writes a sidecar `.qt_ccache_env` with the `CCACHE_DIR` / `SCCACHE_DIR` hint. `report_only=True` skips the patch. Typical use: cut incremental rebuild time from 30-60 s to 2-6 s on a 200-400-file board-game project (5-10× speedup).
- **`qt_steamworks_init`** — generate a drop-in Steamworks SDK integration for a Qt project: `steamworks_integration.h/.cpp` wrapping `SteamAPI_Init` / `SteamAPI_Shutdown` / `SteamAPI_RunCallbacks` with a 10 Hz `QTimer` and a `steamCallbacksDispatched` signal; `steam_achievements.h/.cpp` with `grant(apiName)` / `isUnlocked(apiName)` / `storeStats()` calling `SteamUserStats()->SetAchievement`; `steam_appid.txt` next to the .pro so dev mode works without launching through the Steam client; and `STEAMWORKS.md` with a step-by-step checklist (download SDK, add headers to .pro, call `init()`, configure achievements on the partner site). `sdk_path` option emits a `LIBS += -L... -lsteam_api` snippet.
- **`qt_itch_butler`** — generate `.itch.toml` (channel manifest for `butler push`) and per-channel push scripts (`push_windows.bat`, `push_macos.sh`, `push_linux.sh`, `push_html5.bat`, `push_android.bat`) for distributing a Qt game on itch.io. Also writes `BUTLER_README.md` with the first-time setup (install butler, `butler login`, create project page on itch.io dashboard). `dry_run=True` (default) echoes the push command instead of invoking butler, so it's safe to run on a fresh project without needing the butler binary on PATH.
- **`qt_documentation_lint`** — static analysis of doxygen comment completeness on `.h` / `.cpp` / `.qml` files. For every public function found, checks for a preceding doxygen block, `@brief` summary (or first `///` line) of at least `min_brief_chars` characters, `@param` tags for every declared parameter, and `@return` tag for non-void returns. Reports per-file coverage fraction. Supports `text` (human-readable) or `json` (machine-readable) output. `fail_threshold=0.99` makes it CI-friendly — the tool returns `Error:` if coverage drops below the threshold. Companion to `qt_docs_gen` (which *generates* the Doxyfile + runs doxygen); `qt_documentation_lint` *checks* that the source is documented to begin with.

### Improved

- **`qt_cheatsheet` catalog** — needs to be updated to include the 4 v0.3.0 tools (deferred to next minor; same pattern as v0.2.7 / v0.2.9 backfills).

### Verified

- 20 e2e suites pass: 6 light + 254 full = **254 pytest tests** (`pytest -m light` < 5s, `pytest -m full` ~62s).
- **82 / 82 tools** have e2e coverage (78 v0.2.9 + 4 v0.3.0).
- 82 / 82 tools have complete Args / Returns / Raises docstrings.
- 82 / 82 tools use `_json_footer` for machine-readable trailers (off by default).
- All e2e tests bypass MCP stdio caching by importing `server` directly — verified via `pytest -m full`.
- server.py grew from 13273 → **14110 lines** (+837, +6.3%); 4 new tools averaged ~210 lines each (Pydantic Input + impl + docstring + JSON footer). Tests grew from 233 → 254 (+21).

## [0.2.9] — 2026-07-09

### Added

- **`qt_env_diff`** — compare two Qt SDK installations side-by-side. Reports `qmake -v` version, module count (from `<root>/include/Qt*` dirs), lib file count (`.a` / `.dll` / `.lib`), and lists modules that exist only in A or only in B. The classic MinGW32 vs MinGW64 mismatch diagnostic.
- **`qt_dll_search_path`** — analyze the DLL search path for a Qt executable. Uses `objdump -p` to extract the full DLL import list, then walks the standard Windows search order (`.exe` dir → user-supplied dirs → `QT_BIN_DIR` → `QT_32_BIN_DIR` → `PATH`) and reports which DLLs are present and which are missing. Companion to `qt_run` startup-failure diagnostics — when an exe crashes 0.4s after launch, 90% of the time it's a missing or wrong-bitness `Qt5Core.dll`.
- **`qt_audio_convert`** — ffmpeg wrapper for batch audio conversion. Supports `mp3` / `opus` / `wav` / `ogg` / `flac` / `m4a` / `aac` output, configurable bitrate (ignored for lossless). Typical use: prepare card-flip / shuffle / chip-drop sound effects for a board game. ffmpeg path is overridable via `QT_MCP_FFMPEG` (default `E:\Download_tools\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe`).
- **`qt_qss_inspect`** — parse a Qt Style Sheet (`.qss`) and report its structure: selector count, property count, duplicate selectors (e.g. two `QPushButton { ... }` blocks), duplicate properties within a selector, `!important` usage, unique color values, font sizes. Useful for auditing themes generated by `qt_theme_gen` or hand-written stylesheets that have grown unwieldy.
- **`qt_svg_to_png`** — convert `.svg` files to `.png` at multiple widths. Tries `cairosvg` first, then ImageMagick (`magick` / `convert`). Reports which backend was used. Typical use: prepare card art / icon sets / UI mockups from vector sources into PNGs that Qt can bundle in a `.qrc` resource file.
- **`qt_qml_property_linter`** — static analysis of QML files for property issues. Detects: unused `property` declarations, shadowed ids (same `id` defined twice in the same file), type mismatches (string literal assigned to a numeric property). Companion to `qt_qml_lint` (which checks syntax via qmllint) — catches property-level issues that qmllint misses when types aren't declared or ids are reused.
- **`qt_accessibility_check`** — scan Qt C++ source files for a11y issues. Detects: `Q_OBJECT` classes missing `Q_DISABLE_COPY`; interactive widgets (`QPushButton`, `QLabel`, `QLineEdit`, ...) missing `setAccessibleName`; widgets missing `setObjectName`; counts `setTabOrder` / `setAccessibleDescription` usage. Useful for screen-reader and keyboard-navigation QA before release.
- **`qt_pro_project_graph`** — walk a `.pro` file's `SOURCES` / `HEADERS` / `FORMS` / `RESOURCES` lists, scan each file's content for `#include "..."` directives, and emit a Graphviz DOT dependency graph. Colors clusters by file type (sources = blue, headers = green, forms = orange, resources = pink). Detects include cycles via DFS. Optional `output_dot` writes to file for `dot -Tpng foo.dot -o foo.png`.

### Improved

- **`qt_cheatsheet` catalog** — needs to be updated to include the 8 v0.2.9 tools (deferred to next minor; same pattern as v0.2.7 backfill).

### Bug fixes

- **`qt_pro_project_graph`** — initial implementation used `e.get("values", [])` against `_pro_parse` output, but `_pro_parse` returns single `value` strings (not `values` lists), so nodes were always empty. Fixed to `e.get("value", "").split()` to tokenize properly. Caught by e2e_v14 test #22 ("includes main.cpp") which would have silently shipped an empty graph otherwise.

### Verified

- 19 e2e suites pass: 6 light + 25 new v14 full + 208 previous full = **233 pytest tests** (`pytest -m light` < 5s, `pytest -m full` ~58s).
- **78 / 78 tools** have e2e coverage (70 v0.2.8 + 8 v0.2.9).
- 78 / 78 tools have complete Args / Returns / Raises docstrings (audited via `grep -A 50 "@mcp.tool(name=..." server.py`).
- 78 / 78 tools use `_json_footer` for machine-readable trailers (off by default).
- All e2e tests bypass MCP stdio caching by importing `server` directly — verified via `pytest -m full`.
- server.py grew from 12147 → **13273 lines** (+1126, +9.3%); 8 new tools averaged ~140 lines each (Pydantic Input + impl + docstring + JSON footer).

## [0.2.8] — 2026-07-09

### Added

- **`qt_git_init`** — initialize a git repository for a Qt project. Generates a Qt-specific `.gitignore` (build artifacts, moc\_\*, ui\_\*, \*.user, .tmp/, v0.2.8 .qt_mcp cache), optional README.md (inferred from .pro filename), then runs `git init` + `git add .` + `git commit`. Optional `git_user_name` / `git_user_email` set local repo config. Returns initial commit SHA.
- **`qt_installer_gen`** — generate a Windows installer script (NSIS `.nsi` or Inno Setup `.iss`) plus a `build_installer.bat` that runs `windeployqt` then the compiler (makensis or iscc). Pass `app_name`, `app_version`, `vendor`, optional `license_file` (embedded as comment) and `qml_dir` (passed via `--qmldir`). Does NOT invoke makensis / iscc itself — the user runs the batch after installing NSIS / Inno Setup.
- **`qt_qml_component_gen`** — generate reusable QML components for board-game UIs. 6 templates: `card` (single playing card with suit/rank), `board` (grid of clickable tiles), `player` (name/score/active widget), `hand` (overlapping row of cards), `deck` (draw/discard pile with count), `tile` (tile for mahjong/dominoes/scrabble). Each emits a self-contained `.qml` + a top-level `qmldir` for module imports. Supports `dark` / `light` themes.
- **`qt_db_seed`** — create a SQLite database from a schema definition, optionally insert seed rows, and generate a `<db_name>_examples.py` file with CRUD helpers (`select_all_*`, `insert_*`, `delete_*`). Useful for board-game player / leaderboard / move-history persistence as an alternative to `qt_state` / `qt_save`. Schema defined as `tables=[{name, columns:[{name, type, pk, not_null, default}]}]`.
- **`qt_high_dpi_test`** — launch a `.exe` at multiple `QT_SCALE_FACTOR` values (default `[1.0, 1.5, 2.0]`), screenshot the window for each via pywinauto (with pyautogui fallback), and (optionally) compare against baseline screenshots for pixel diff. Critical for board-game UIs that need to render correctly across DPI scales.
- **`qt_property_browser`** — extract all `Q_PROPERTY` declarations from a Qt header file and render them as a table in markdown / html / json. Each property lists its type, READ, WRITE, NOTIFY, MEMBER, CONSTANT clauses. Useful for API documentation, demos, and meta-object auditing.

### Improved

- **`qt_cmake` exclusion list** — confirmed `.tmp` removed (already in v0.2.5 fix; no regression).
- 6 new tools all use `_json_footer` (off by default) for machine-readable output.

### Verified

- 18 e2e suites pass: 6 light + 25 new v13 full + 177 previous full = 208 pytest tests (`pytest -m light` < 5s, `pytest -m full` ~50s).
- 70 / 70 tools have e2e coverage (64 v0.2.7 + 6 v0.2.8).
- 70 / 70 tools have complete Args / Returns / Raises docstrings.
- 70 / 70 tools use `_json_footer` for machine-readable trailers (off by default).
- All e2e tests bypass MCP stdio caching by importing `server` directly — verified via `pytest -m full`.

## [0.2.7] — 2026-07

### Added

- **`qt_model_gen`** — generate a `QAbstractListModel` or `QAbstractTableModel` subclass for board-game data (cards, players, scores). For list models: configurable `item_type` + `addItem` / `removeAt` / `clear` slots. For table models: `columns` (list of `{name, type}` dicts) + `appendRow` / `clear`. Output: drop-in `.h` / `.cpp` with `rowCount` / `data` / `roleNames` (QML-ready) / `headerData` (table only).
- **`qt_theme_gen`** — generate a QSS (Qt Style Sheet) for a Qt Widgets app. Pass `mode` ('light' / 'dark'), `base_color`, `accent_color`, `text_color`, `border_radius`; emits a fully-styled `.qss` covering QWidget / QMainWindow / QMenuBar / QMenu / QPushButton (with hover/pressed/disabled/default states) / QLineEdit / QLabel / QListWidget / QTreeWidget / QTableWidget / QHeaderView / QProgressBar / QSlider / QCheckBox / QRadioButton / QStatusBar / QToolTip / QScrollBar.
- **`qt_ico_create`** — bundle one or more PNGs into a multi-resolution Windows `.ico` (16, 32, 48, 64, 128, 256 default sizes). Required for high-DPI-aware app icons on Windows. Uses Pillow.
- **`qt_screenshot_diff`** — pixel-by-pixel image diff for visual regression testing. Pass two images and a tolerance (0-255 per channel); returns diff count, ratio, and bounding box. Optional `diff_image` writes a red-overlay visualization of the differences. Uses Pillow + numpy.
- **`qt_clazy_check`** — regex-based Qt anti-pattern checker (no clazy binary required). Detects: Q_OBJECT in `.cpp` (should be in `.h`); new QObject without explicit parent; QObject subclass missing `Q_DISABLE_COPY`; QVector (Qt 4 only, use QList in Qt 5+); old-style `SIGNAL()` / `SLOT()` connect; QObject subclass missing Q_OBJECT; implicit `char*` to QString casts. Returns per-check counts and first 20 issues.
- **`qt_signal_slot_trace`** — static analysis of signal / slot wiring. Parses `.h` for `signals:` / `slots:` declarations and QObject subclasses, parses `.cpp` for `QObject::connect` / `connect` / old-style `SIGNAL` / `SLOT` calls. Output formats: 'text' (default), 'json' (machine readable), 'dot' (Graphviz). Reports connections, orphan signals, orphan slots. Optional `output_file` writes the result to disk.
- **`qt_input_recorder`** — record / playback mouse + keyboard events for demos, regression tests, and bug reports. Uses `pyautogui` + `pynput`. Output: portable JSON with `events` array. Actions: 'record' (capture for N seconds), 'playback' (replay a file at given speed), 'info' (show event counts by type). Helpers live in `<SANDBOX>/.tmp/input_recorder_helpers/`.
- **`qt_translation_validate`** — parse Qt `.ts` files and report translation coverage per language. Counts `total` / `finished` / `unfinished` / `empty` / `obsolete` per `<TS language="...">` block. Optional `min_coverage` flag to warn about low-coverage languages. Useful for i18n QA.

### Improved

- **`qt_cheatsheet` catalog backfill** — added 14 tools that were missing from the cheatsheet catalog (qt_lint, qt_analyze, qt_input, qt_cmake, qt_docs_gen, qt_achievement, qt_undo, qt_leaderboard_ui, qt_pkg_install, qt_release_notes, qt_copyright, qt_score, qt_timer, qt_replay) plus the 8 v0.2.7 tools. Catalog now reflects all 64 tools.
- Bug fix: `qt_signal_slot_trace` was double-counting `QObject::connect(...)` lines (matched by both the general `connect(...)` pattern and the `QObject::connect(...)` pattern). Combined into a single optional-prefix regex.

### Verified

- All 17 e2e suites pass: 6 light + 177 full = 183 pytest tests (`pytest -m light` < 5s, `pytest -m full` ~45s).
- 64 / 64 tools have e2e coverage.
- 64 / 64 tools have complete Args / Returns / Raises docstrings.
- 64 / 64 tools use `_json_footer` for machine-readable trailers (off by default).

## [0.2.0] — 2026-07

### Added

- **`qt_validate`** — walk a `.pro` and verify every `SOURCES` / `HEADERS` / `FORMS` / `RESOURCES` / `TRANSLATIONS` reference exists and is readable. Optional `strict=True` also runs XML parse on `.ui` / `.qrc` and detects duplicate entries.
- **`qt_run_trace`** — launch a `.exe` with `QT_LOGGING_RULES` + `QT_LOGGING_TO_CONSOLE=1` and capture stdout/stderr. Use for debugging signal/slot dispatch (`qt.core.signal*=true`), QML loading, or plugin loading.
- **`qt_smoke_test`** — end-to-end health check: clean → build (via `qt_build`) → detach-launch for N seconds → kill. Returns PASS only if all three steps succeed.
- **`qt_diff`** — compare two `.pro` projects. Reports variables (SOURCES, HEADERS, FORMS, RESOURCES, TRANSLATIONS, DEFINES, INCLUDEPATH, LIBS) that differ, source files only in A or only in B, and SHA1 mismatches among common files. `show_identical=True` also lists files with matching SHA1.
- **`qt_pkg`** — list / inspect installed Qt 5 modules. Walks `QT_ROOT/include/Qt*` + `lib/cmake/Qt5*`, reports headers/libs/version for a single module, lists all 76+ modules in default mode, and enumerates plugins under `QT_ROOT/plugins/`.
- **`qt_log`** — filter / analyze a Qt log file. Counts lines by level (debug / warning / critical / fatal / info), extracts `qt.*` category counts, supports `category_filter` and `level_filter` substring matching, and caps output via `max_lines`.
- **`qt_state`** — QSettings wrapper for persistent app state. `save` / `load` / `delete` / `list` / `clear` actions on a per-organization / per-application basis. Writes to OS-native QSettings location (APPDATA on Windows, `~/.config` on Linux). Useful for board-game save/load, settings persistence, replay data.
- **`qt_assets`** — scan a directory of asset files (images, audio) and emit a `.qrc` + optional `qrc_<name>.cpp` with `Q_INIT_RESOURCE`. Supports recursive scan, exclude patterns, custom extensions, and per-subdirectory grouping in the .qrc output.
- **`qt_watch`** — auto-rebuild on file change. Uses the `watchdog` library to subscribe to filesystem events, debounces rapid changes (default 1.5s), and calls `qt_build` on each batch. Returns the PID of the watcher process; use `qt_kill_exe` to stop.
- **`qt_signature`** — sign / verify Windows executables via signtool.exe. Actions: 'info' (locate signtool), 'sign' (apply Authenticode + RFC 3161 timestamp), 'verify' (check existing signature), 'timestamp' (re-timestamp an already-signed file). Auto-discovers signtool.exe under `C:\Program Files\Windows Kits\10\bin\*\x64\`.
- **`qt_save`** — save / load / list / delete / inspect JSON save files for board-game portability. Different from `qt_state` (QSettings native format): `qt_save` writes plain JSON, easy to inspect with `cat save.json | jq` and sync across machines.
- **`qt_audio`** — list / probe / play sound-effect files. Reports QtMultimedia availability, scans audio directories, identifies format from file header, and emits a QSoundEffect / QMediaPlayer C++ snippet ready to drop in your game.
- **`qt_anim`** — generate QPropertyAnimation code (fade / move / scale / rotate / color / sequence). Output is a ready-to-paste C++ snippet with start / end values, duration, easing curve, optional loop.
- **`qt_network`** — generate a `.h` / `.cpp` pair for a Qt network class (QTcpSocket client / QTcpServer / QUdpSocket peer / QWebSocket client). Configure host, port, and class name; output goes to your `output_dir` ready to add to the .pro.
- **`qt_coverage`** — collect code coverage via gcov + lcov. Injects `--coverage` flags into the .pro, builds, (optionally) runs tests, then runs `lcov --capture` + `genhtml`. Restores the .pro on exit. Produces an HTML report at `<output>/html/index.html`.
- **`qt_cheatsheet`** — print a categorized quick reference of all qt-mcp tools (env / scaffold / build / run / validate / creator / analysis). Pass `tool_name` for detailed help on one tool, or `category` to filter.
- **`qt_score`** — track and rank player scores for board games. add / list / leaderboard (top-N ranked) / reset / import / export. Backed by `<SANDBOX>/.scores/scores.json`.
- **`qt_timer`** — start / stop / pause / resume named timers (game clock, turn timer, total game time). State persisted to `<SANDBOX>/.timers/timers.json`. Useful for time-controlled turn-based games.
- **`qt_replay`** — step-by-step game replay system. record / save / load / list / play / delete. Each step has `n` / `type` / `data` / `ts`. Backed by per-session JSON in `<SANDBOX>/.replays/`.
- **`qt_lint`** — unified lint wrapper. Run cpplint + qmllint + clang-tidy over a project. Returns `LINT PASS` / `LINT FAIL` with per-linter summary.
- **`qt_analyze`** — clang-tidy deep analysis with custom check selection (e.g. `bugprone-*,performance-*`). Supports `text` / `json` output.
- **`qt_input`** — generate keyboard / mouse / gamepad input handling code. 'keyboard' emits QShortcut + QKeySequence + slot declaration. 'mouse' emits mousePressEvent / mouseMoveEvent / mouseReleaseEvent overrides. 'gamepad' emits a QGamepad wrapper (with Qt6 SDL2 fallback note). 'focus' emits tab order / focus chain. 'mapping' writes a JSON bindings file.
- **`qt_cmake`** — generate a CMakeLists.txt for a Qt project. Supports find_package(Qt5) or find_package(Qt6), AUTOMOC / AUTORCC / AUTOUIC, C++17, templates for `app` / `library` / `console`. Migrates projects from qmake to CMake.
- **`qt_docs_gen`** — generate a Doxyfile for a Qt project and (optionally) run doxygen to produce HTML docs. Defaults to EXTRACT_ALL, source browser, call graphs. Useful for keeping API documentation in sync with code.
- **`qt_achievement`** — manage game achievements / medals. 'define' (add an achievement to the catalog), 'grant' (mark as earned), 'list' (show all achievements with current progress for a player), 'progress' (update current count for multi-step achievements), 'reset' (clear all earned for a player), 'catalog' (show all defined).
- **`qt_undo`** — push / undo / redo game-state snapshots per project. Stack persisted to JSON, max depth configurable. Returns state in JSON trailer for programmatic use.
- **`qt_leaderboard_ui`** — generate a leaderboard widget (.h + .cpp + .ui trio). Two styles: 'table' (QTableView with sort/filter) and 'cards' (QListView with card delegate). Reads from `<SANDBOX>/.scores/scores.json` (produced by qt_score).
- **`qt_pkg_install`** — wrapper around `aqt` (https://github.com/miurahr/aqtinstall) for installing / listing / uninstalling Qt SDKs. Supports Qt 5.14.2 / 6.x on windows / linux / mac.
- **`qt_release_notes`** — auto-generate a CHANGELOG.md section from `git log` (conventional-commits prefix detection) or manually add bullets under Unreleased.
- **`qt_copyright`** — prepend a license header (default MIT) to every source file in a project. Skips files with existing SPDX markers, supports dry_run.
- **56 tools total** (was 26 in v0.1.0). All 56 have full Args/Returns/Raises docstrings. All 56 are covered by e2e tests.
- **`__version__ = "0.2.0"`** on the module.
- **`def main() -> int`** entry point. `python -m server` and the `qt-mcp` console script both work.
- **`_json_footer(obj)`** helper + `QT_MCP_JSON=1` env-var gate: when set, every tool appends a `--- json ---\n{ok,data|error}` trailer. Applied to **all 34 tools** (141 string-return statements wrapped across single + multi-line returns); preserved e2e string contracts because the helper returns `""` by default. Off by default.
- **Env-overridable paths**: `QT_MCP_QT_ROOT`, `QT_MCP_QT_32_ROOT`, `QT_MCP_MINGW_BIN`, `QT_MCP_QTCREATOR`, `QT_MCP_SANDBOX`, `QT_MCP_QT_VERSION`. Defaults preserve the original Windows layout.
- **`pytest.ini`** — discover every `e2e_*.py` in `tests/light/` and `tests/full/` as a pytest test module. Auto-marks tests by directory: `light` = no Qt SDK needed, `full` = Qt SDK required. CI runs `pytest -m light` for fast PR gating. No pytest required for the e2e scripts (each calls `sys.exit(0 | 1)`).
- **`pyproject.toml`** — installable via `pip install .`, exposes the `qt-mcp` console script.
- **`.github/workflows/ci.yml`** — Windows-latest CI that runs `pytest -v` against the lightweight test subset. Heavyweight Qt-SDK tests are excluded from CI (they need the full 5 GB Qt install).
- **`.github/ISSUE_TEMPLATE/`** (bug + feature) and **`PULL_REQUEST_TEMPLATE.md`**.
- **`tests/light/` + `tests/full/`** — e2e scripts split into "no Qt SDK" (parsers, helpers, sandbox rejection) and "needs Qt SDK" (build/run) tiers. Conftest.py auto-marks by directory.
- **`examples/minimal/`** — minimal runnable example (console_app template + a `.mcp.json` that points at it).
- **`docs_data/README.md`** — explains how to rebuild the 53 MB FTS5 docs index.

### Changed

- **`qt_clean`** now delegates to a new `_clean_artifacts(proj)` helper so `qt_smoke_test` can reuse the cleanup logic.
- **`qt_test`** now uses a new `_pe_bits(exe)` helper to pick 32-bit vs 64-bit Qt bin dir. The helper is also used by `qt_run_trace` and `qt_smoke_test` — single source of truth for the PE-header heuristic.
- **README.md** rewritten: 29-tool table, badges, expanded environment variables table, programmatic output (JSON trailers) section, Development section.

### Fixed

- e2e `e2e_new_tools_v3.py` hard-coded `len(tools) == 23`; loosened to `>= 23` so adding v4 / v5 tools does not break the test.

## [0.1.0] — 2026-07 (initial)

- 26 MCP tools covering the full Qt C++ lifecycle.
- 9 scaffold templates (widget / mainwindow / dialog / qml_app / console_app / cards_game / chess_game / generic_game / game_framework).
- 8 e2e test suites, all passing.
- Local FTS5 docs index (`docs_data/qt_5_14_2_docs.db`, 53 MB, gitignored).
- AI-friendly structured build diagnostics with one-line fix suggestions.
- UI automation (`qt_ui_action`) and Qt Creator driving (`qt_creator_open` / `qt_creator_run`).