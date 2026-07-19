# qt-mcp demo walkthrough

A 6-step end-to-end demo of the qt-mcp server, from empty directory to a
running Qt MainWindow driven by AI. All steps are runnable from a Claude
Code session once the server is registered.

**What this proves:** the MCP server can scaffold, build, run, drive, and
inspect a Qt project without any human clicking inside the IDE.

---

## Step 1 — `qt_diagnose_env`

Before any project work, confirm the toolchain is healthy.

> "Run `qt_diagnose_env` with deep=True."

Returns a checklist of every required binary, the 32-bit / 64-bit coexistence
report, the PATH order audit, and the sandbox writability test. Catches
"Required Qt tool not found" failures **before** they bite later.

---

## Step 2 — `qt_scaffold`

> "Scaffold a `mainwindow` project at `Files/demo/counter`."

Emits a runnable skeleton:

```
demo/counter/
├── counter.pro
├── main.cpp
├── mainwindow.h
├── mainwindow.cpp
└── mainwindow.ui
```

The 9-template enum (`widget` / `mainwindow` / `dialog` / `qml_app` /
`console_app` / `cards_game` / `chess_game` / `generic_game` / `game_framework`)
covers everything from a CLI tool to a full board-game scaffold.

---

## Step 3 — `qt_pro_edit` + `qt_class_wizard`

Add a Counter QObject to the scaffolded project.

> "Use `qt_class_wizard` to generate a Counter class with `Q_PROPERTY value`
> and a QTimer that ticks every 100 ms."

Writes `counter.h` / `counter.cpp` / `counter.ui`, runs `moc`, runs `uic`,
compiles a transient binary to confirm everything links, and updates the
`.pro` to include the new files.

---

## Step 4 — `qt_build`

> "Run `qt_build` on `Files/demo/counter`."

`qmake` parses the `.pro`, `mingw32-make` runs in parallel (default `-j4`).
On success, the build log is appended to `<project_dir>/.qt_mcp_last_build.log`.
On failure, the log is parsed into a structured `--- diagnostics (JSON) ---`
block: file, line, column, tool, code, message, **suggestion**.

A typical gcc error suggestion: *"Looks like a header is missing. Try
`qt_grep` to confirm the symbol exists, or check your `.pro` INCLUDEPATH."*

---

## Step 5 — `qt_run` (detached) + `qt_ui_action` (driving)

> "Launch the .exe detached, then drive the counter UI."

1. `qt_run(executable=..., detach=True, timeout=0)` forks the `.exe`, returns
   the PID, and the MCP conversation moves on.
2. `qt_ui_action(action="click", click_button="Start")` finds the button by
   its `objectName` and clicks it. The counter's `QTimer` starts ticking.
3. `qt_ui_action(action="screenshot", output_path=...)` saves a PNG of the
   window. `pywinauto`'s `win.capture_as_image()` (PrintWindow) bypasses the
   desktop compositor so even occluded windows come through clean.

```
Count: 33
[Stop] [Reset]
```

This PNG is what `qt_ui_action` produced — see `docs/demo/screenshots/`.

---

## Step 6 — `qt_validate` + `qt_smoke_test`

End the demo with two sanity checks.

> "Validate the project file with `qt_validate`."

Walks the `.pro` and reports each `SOURCES` / `HEADERS` / `FORMS` / `RESOURCES`
reference as `[OK]` / `[MISS]` / `[OOS]` (out of sandbox) / `[BAD]` (XML
parse error). Catches typos and stale entries before the next build.

> "Run `qt_smoke_test` to confirm the project still builds and launches."

`clean → build → run for 5s → kill → verdict: PASS / FAIL`. The smoke test
output includes the tail of each step so you can spot the regression
without scrolling.

---

## What the 6 screenshots show

The 6 PNGs in this directory (`mcp_via_pid_*.png`, `counter_t*.png`,
`desktop.png`) come from a real run of the above walkthrough. They are the
visual proof that the MCP server actually drove the Qt window end-to-end —
no manual UI interaction, no Qt Creator launched, no pre-built binary.

---

## What this demo does NOT cover

- **The Qt Creator GUI path** (`qt_creator_open` / `qt_creator_run`) — those
  tools open a `.pro` in the IDE itself and build with Ctrl+B. Useful when
  you want to see Qt Creator on screen (debugging IDE behavior, teaching,
  visual verification). See [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md).
- **Translation flow** (`qt_translate`) — separate walkthrough: write
  `tr("...")` calls, run `lupdate`, hand-translate the `.ts`, run `lrelease`,
  load the `.qm` via `QTranslator`.
- **CI integration** — see [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
  for the GitHub Actions setup.

---

## Re-running the demo

```bash
cd E:/Download_tools/QT/Tools/qt-mcp
python e2e_test.py     # scaffold → build → run a similar project, screenshot, kill
python e2e_new_tools_v5.py   # qt_validate / qt_run_trace / qt_smoke_test
```

The `e2e_creator_tools.py` suite re-creates the Qt Creator GUI path; it
needs a live Qt Creator instance and is opt-in.