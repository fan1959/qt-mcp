# Demo screenshots

This directory holds PNGs from real `qt-mcp` runs.

The screenshots in this directory are produced by re-running the walkthrough
in [`../README.md`](../README.md). Each one is captured by:

```python
await server.qt_ui_action(QtUIActionInput(
    action="screenshot",
    output_path="docs/demo/screenshots/step_N_name.png",
))
```

The tool uses `pywinauto.capture_as_image()` (Windows `PrintWindow`) so the
PNG is a true capture of the Qt window — even when other windows occlude it.

## What each screenshot shows (canonical run)

| File | What it shows | How it was produced |
|---|---|---|
| `step_1_diagnose.png` | `qt_diagnose_env deep=true` text output | (terminal screenshot) |
| `step_2_scaffold.png` | Files written by `qt_scaffold mainwindow` | (file explorer or terminal `tree`) |
| `step_3_class_wizard.png` | Generated `Counter` class files | (terminal `ls`) |
| `step_4_build_ok.png` | `qt_build` tail with "Build OK" | (terminal screenshot) |
| `step_5_counter_running.png` | The Counter window, mid-tick, with `Count: 33` | `qt_ui_action screenshot` |
| `step_6_smoke_pass.png` | `qt_smoke_test` final verdict | (terminal screenshot) |

## Existing reference screenshots

Real screenshots from the Jul 8 development session are kept in
`E:\Download_tools\QT\Files\qt_mcp_demo\` for historical reference. They are
not bundled with the qt-mcp source tree because they reference the user's
local Qt install path.

## Re-capturing

```bash
# Terminal 1
python -m server

# Terminal 2 (Claude Code or raw MCP client)
qt_scaffold(template="mainwindow", output_dir="...")
qt_build(project_dir="...")
qt_run(executable="...", detach=True)
qt_ui_action(action="screenshot", output_path="docs/demo/screenshots/step_5.png")
qt_kill_exe(image_name="...")
```