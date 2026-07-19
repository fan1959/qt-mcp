# 最小的 qt-mcp 示例

最小的 Qt + qt-mcp 配置：一个 `console_app` 项目，一个把服务器接入 Claude 的 `.mcp.json`。

## 文件

- `hello.pro` — qmake 项目文件
- `main.cpp` — 一次性 CLI：解析 `--name`，打印问候，退出
- `.mcp.json` — 把 qt-mcp 服务器注册进 Claude Code

## 试一下

1. 在这个目录下，用 MCP 工具构建：

   > "用 qt_scaffold 在 `./hello` 放一个 console_app（会复用这些文件），然后 qt_build 一下。"

2. 或者手动：

   ```bash
   qmake hello.pro
   mingw32-make
   ./debug/hello.exe --name World
   # → Hello, World!
   ```

## 接入 Claude Code

把自带的 `.mcp.json` 放进这个目录（或把它的 `mcpServers` 块合并到你的用户级配置）：

```json
{
  "mcpServers": {
    "qt": {
      "command": "python",
      "args": ["<绝对路径>\\qt-mcp\\server.py"],
      "transport": "stdio",
      "env": {
        "QT_MCP_QT_ROOT":   "E:\\Download_tools\\QT\\5.14.2\\mingw73_64",
        "QT_MCP_MINGW_BIN": "E:\\Download_tools\\QT\\Tools\\mingw730_64\\bin",
        "QT_MCP_SANDBOX":   "<绝对路径>\\qt-mcp\\examples\\minimal"
      }
    }
  }
}
```

然后让 Claude：

> "在这儿搭一个 console_app，构建，跑一下 `--name Qt`。"

Claude 会驱动 `qt_scaffold` → `qt_build` → `qt_run` 并打印结果。