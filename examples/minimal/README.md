# Minimal qt-mcp example

The smallest possible Qt + qt-mcp setup. One `console_app` project, one
`.mcp.json` that wires the server into Claude.

## Files

- `hello.pro` — qmake project file
- `main.cpp` — one-shot CLI: parse `--name`, print greeting, exit
- `.mcp.json` — registers the qt-mcp server with Claude Code

## Try it

1. From this directory, build it with the MCP tools:

   > "Use qt_scaffold to put a console_app at `./hello` (it'll reuse these
   > files) and qt_build it."

2. Or by hand:

   ```bash
   qmake hello.pro
   mingw32-make
   ./debug/hello.exe --name World
   # → Hello, World!
   ```

## Wiring into Claude Code

Drop the included `.mcp.json` into this folder (or merge its `mcpServers`
block into your user-level config):

```json
{
  "mcpServers": {
    "qt": {
      "command": "python",
      "args": ["<absolute path>\\qt-mcp\\server.py"],
      "transport": "stdio",
      "env": {
        "QT_MCP_QT_ROOT":   "E:\\Download_tools\\QT\\5.14.2\\mingw73_64",
        "QT_MCP_MINGW_BIN": "E:\\Download_tools\\QT\\Tools\\mingw730_64\\bin",
        "QT_MCP_SANDBOX":   "<absolute path>\\qt-mcp\\examples\\minimal"
      }
    }
  }
}
```

Then ask Claude:

> "Scaffold a console_app here, build it, run with `--name Qt`."

Claude will drive `qt_scaffold` → `qt_build` → `qt_run` and print the result.