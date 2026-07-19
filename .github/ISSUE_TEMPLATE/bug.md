---
name: Bug report
about: Something broke — qt_build failed, a tool returned a confusing message, etc.
title: "[bug] "
labels: ["bug"]
---

## What happened

<!-- A clear, one-paragraph description of the bug. -->

## Reproduction steps

1. (call this tool with these arguments)
2. (then this tool)
3. (and saw this output)

## Expected output

<!-- What you expected to see instead. -->

## Actual output

```
<paste the tool output here, including any "--- json ---" trailer>
```

## Environment

- Windows version: (e.g. Windows 11 23H2)
- Python version: (`python --version`)
- Qt install path: (`echo %QT_MCP_QT_ROOT%` or your `.mcp.json` `env` block)
- qt-mcp version: (`python -c "import server; print(server.__version__)"`)
- Which tools are involved:

## Logs

If you ran `qt_build` and it failed, please also paste the output of:

```
python -c "import server; print(open(r'<project_dir>\.qt_mcp_last_build.log').read())"
```

## Anything else?

<!-- Add screenshots, links to your project repo, etc. -->