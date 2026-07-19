# Architecture

qt-mcp is a single-file FastMCP stdio server that wraps the Qt 5.14.2 + MinGW
toolchain so an AI assistant can drive a Qt C++ project end-to-end.

## Process & I/O

```
+--------------------+    stdio JSON-RPC    +-------------------------+
|   MCP client       | <------------------> |   server.py (FastMCP)   |
|   (Claude Code,    |     one request      |   29 @mcp.tool funcs    |
|    Claude Desktop) |     one response     +------------+------------+
+--------------------+                                  |
                                                         | subprocess
                                                         v
                  +-------+-------+-------+-------+-------+-------+
                  | qmake  | mingw-| moc  | qmllint | windeployqt |
                  |  .exe  | make  | .exe |  .exe   |   .exe      |
                  +-------+-------+-------+-------+---------------+
                                                         |
                                                         v
                                                  +---------------+
                                                  |  your .exe    |
                                                  |  (Qt app)     |
                                                  +---------------+
```

Every tool is a thin async wrapper around a Windows subprocess. The server
collects stdout / stderr, parses errors (`_parse_diagnostics`), and returns
plain text by default. Set `QT_MCP_JSON=1` for a machine-readable trailer.

## Module layout (in `server.py`)

| Section | Lines | What lives here |
|---|---|---|
| Module docstring + imports | 1-40 | `__future__`, stdlib, mcp, pydantic, `templates_game_framework` |
| `__version__` + Qt environment | 50-95 | `QT_ROOT`, `QT_32_ROOT`, `MINGW_BIN_DIR`, `SANDBOX_ROOT` — all env-overridable via `_env_path()` |
| Path sandbox | 100-110 | `_in_sandbox`, `_require_sandbox` |
| Subprocess plumbing | 115-145 | `_qt_env`, `_check_paths`, `_pe_bits`, `_clean_artifacts`, `_run`, `_is_pid_alive`, `_guess_missing_dll`, `_tail`, `_json_footer`, `main` |
| `.pro` parser | 175-265 | `_pro_strip_comments`, `_pro_parse`, `_pro_serialize`, `_pro_tokenize`, `_pro_set` |
| Helper dataclasses + enums | 270-790 | `@dataclass _ScaffoldFile`, `ScaffoldTemplate` enum (9 entries) |
| Scaffold file emitters | 800-1620 | One function per template; `qt_scaffold` orchestrator |
| Pydantic Input models | 1650-1880 | One class per tool |
| Tool implementations | 1885-end | 29 `@mcp.tool` functions |
| Entrypoint | last 5 lines | `if __name__ == "__main__": sys.exit(main())` |

## Six logical modules (not files — sections of `server.py`)

| Module | Responsibility | Key tools |
|---|---|---|
| **env** | Detect Qt / MinGW paths, validate the sandbox, run health checks. | `qt_env`, `qt_diagnose_env` |
| **scaffold** | Emit runnable project skeletons (9 templates). | `qt_scaffold`, `qt_class_wizard`, `qt_gen_qrc`, `qt_pro_edit` |
| **build** | Run qmake + mingw32-make, classify errors, persist logs. | `qt_build`, `qt_build_diagnostics`, `qt_clean`, `qt_moc_check` |
| **run** | Launch the `.exe` (sync / detach), capture output, trace, smoke-test. | `qt_run`, `qt_run_trace`, `qt_kill_exe`, `qt_smoke_test` |
| **validate** | Inspect project files for correctness. | `qt_validate`, `qt_resources`, `qt_docs_search`, `qt_grep`, `qt_deps` |
| **creator** | Drive Qt Creator IDE itself (open + build + run inside the IDE). | `qt_creator_open`, `qt_creator_run`, `qt_ui_action`, `qt_designer` |

Cross-cutting helpers (`_in_sandbox`, `_qt_env`, `_json_footer`, `_pe_bits`,
`_clean_artifacts`) are at the top of the file and used by every module.

## Why one file?

- `server.py` is ~4700 lines but **no single tool is more than ~250 lines** —
  each `@mcp.tool` function is a self-contained async wrapper.
- Splitting into a package (`qt_mcp/tools/build.py`, etc.) would require
  adding ~50 lines of `__init__.py` plumbing for no real win on a stdio
  server that loads once and never reloads.
- The FastMCP decorator pattern (tool at module top level) reads better when
  all tools are in one place — Claude (or a human skimming the file) can
  see every tool signature within a single scroll.

## Concurrency

`mcp.run()` is async; every tool is `async def`. Subprocess calls go through
`_run(cmd, cwd, timeout, env=None)` which uses `asyncio.create_subprocess_exec`
under the hood. No thread pool, no shared state between tool invocations —
each tool invocation is an independent async coroutine.

## Data flow for `qt_smoke_test`

```
qt_smoke_test (project_dir, build_type, run_seconds, build_timeout)
   │
   ├─► _clean_artifacts(proj_dir)         ← shared with qt_clean
   │
   ├─► qt_build(QtBuildInput(...))        ← calls qmake + mingw32-make
   │     └─► writes .qt_mcp_last_build.log on success/failure
   │
   ├─► Locate <proj>/debug/*.exe
   │
   └─► qt_run(QtRunInput(detach=True))    ← forks the .exe
         └─► qt_kill_exe() after run_seconds
```

## Error handling philosophy

- Every tool returns a **string** (not a typed response). This keeps the MCP
  protocol simple and lets callers pipe the output through `tee`, `grep`, etc.
- Errors always start with `"Error: "` so a single grep can find them all.
- `_parse_diagnostics` adds a structured `--- diagnostics (JSON) ---` block
  after `qt_build` failure for easy programmatic consumption.
- The optional `--- json ---\n{ok, data|error}` trailer (under `QT_MCP_JSON=1`)
  is the unified machine-readable contract going forward.

## Path sandbox

Every user-supplied path resolves through `_require_sandbox(path, what)`:

1. `path.resolve()` is called.
2. If the resolved path is not under `SANDBOX_ROOT`, an error string is
   returned and the tool short-circuits.
3. `SANDBOX_ROOT` defaults to `E:\Download_tools\QT` but can be overridden
   by `QT_MCP_SANDBOX` — useful for CI or multi-machine setups.

This is enforced at the **Python level**, not at the OS level. A determined
caller could `os.chdir()` out of the sandbox, but no current tool does.

## Environment overrides

All filesystem paths in `server.py` are routed through `_env_path(var,
default)`. To run the same `server.py` on a different machine:

```bash
export QT_MCP_QT_ROOT=/opt/Qt/5.14.2/gcc_64
export QT_MCP_MINGW_BIN=/opt/mingw64/bin
export QT_MCP_SANDBOX=/home/me/qt-projects
python server.py
```

Or set them in your MCP client's `.mcp.json` `env` block.