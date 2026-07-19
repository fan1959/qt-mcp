# 架构

qt-mcp 是一个单文件 FastMCP stdio 服务器，封装 Qt 5.14.2 + MinGW 工具链，让 AI 助手可以端到端驱动 Qt C++ 项目。

## 进程与 I/O

```
+--------------------+    stdio JSON-RPC    +-------------------------+
|   MCP 客户端       | <------------------> |   server.py (FastMCP)   |
|  (Claude Code,     |     一请求一响应     |   ~150 个 @mcp.tool    |
|   Claude Desktop)  |                     +------------+------------+
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
                                                  |  你的 .exe    |
                                                  |  (Qt 应用)    |
                                                  +---------------+
```

每个工具都是一层薄薄的 async 包装器，调用 Windows subprocess。server 收集 stdout / stderr，解析错误（`_parse_diagnostics`），默认返回纯文本。设 `QT_MCP_JSON=1` 可让每个工具末尾加机器可读的 JSON 段。

## server.py 内的模块分布

| 区段 | 行号 | 内容 |
|---|---|---|
| 模块 docstring + imports | 1-40 | `__future__`、标准库、mcp、pydantic、`templates_game_framework` |
| `__version__` + Qt 环境 | 50-95 | `QT_ROOT`、`QT_32_ROOT`、`MINGW_BIN_DIR`、`SANDBOX_ROOT`——均通过 `_env_path()` 允许环境变量覆盖 |
| 路径沙箱 | 100-110 | `_in_sandbox`、`_require_sandbox` |
| subprocess 管道 | 115-145 | `_qt_env`、`_check_paths`、`_pe_bits`、`_clean_artifacts`、`_run`、`_is_pid_alive`、`_guess_missing_dll`、`_tail`、`_json_footer`、`main` |
| `.pro` 解析器 | 175-265 | `_pro_strip_comments`、`_pro_parse`、`_pro_serialize`、`_pro_tokenize`、`_pro_set` |
| 辅助 dataclass + enum | 270-790 | `@dataclass _ScaffoldFile`、`ScaffoldTemplate` enum |
| 脚手架文件生成器 | 800-1620 | 每个模板一个函数；`qt_scaffold` 编排器 |
| Pydantic Input 模型 | 1650-1880 | 每个工具一个类 |
| 工具实现 | 1885-末 | 所有 `@mcp.tool` 函数 |
| 入口 | 末 5 行 | `if __name__ == "__main__": sys.exit(main())` |

## 六大逻辑模块（不是分文件，是 server.py 的分区）

| 模块 | 职责 | 代表工具 |
|---|---|---|
| **env** | 检测 Qt / MinGW 路径、验证沙箱、跑健康检查 | `qt_env`、`qt_diagnose_env` |
| **scaffold** | 生成可运行的项目骨架 | `qt_scaffold`、`qt_class_wizard`、`qt_gen_qrc`、`qt_pro_edit` |
| **build** | 跑 qmake + mingw32-make，分类错误，持久化日志 | `qt_build`、`qt_build_diagnostics`、`qt_clean`、`qt_moc_check` |
| **run** | 启动 .exe（同步 / 后台），捕获输出，追踪，smoke-test | `qt_run`、`qt_run_trace`、`qt_kill_exe`、`qt_smoke_test` |
| **validate** | 检查项目文件正确性 | `qt_validate`、`qt_resources`、`qt_docs_search`、`qt_grep`、`qt_deps` |
| **creator** | 驱动 Qt Creator IDE 本身（IDE 内打开 + 构建 + 运行） | `qt_creator_open`、`qt_creator_run`、`qt_ui_action`、`qt_designer` |

跨模块 helpers（`_in_sandbox`、`_qt_env`、`_json_footer`、`_pe_bits`、`_clean_artifacts`）放在文件顶部，所有模块共用。

## 为什么是单文件？

- `server.py` 接近 3 万行，但**没有单个工具超过 ~250 行**——每个 `@mcp.tool` 函数都是自洽的 async 包装
- 拆成包（`qt_mcp/tools/build.py` 等）需要约 50 行 `__init__.py` 胶水代码，对一个启动一次永不重载的 stdio 服务器没收益
- FastMCP 装饰器模式（顶层工具）在所有工具一个文件时读起来更顺——Claude 或人翻文件，单次滚动能看到所有工具签名

## 并发

`mcp.run()` 是 async；所有工具都是 `async def`。subprocess 调用走 `_run(cmd, cwd, timeout, env=None)`，底层用 `asyncio.create_subprocess_exec`。无线程池，工具调用之间无共享状态——每次工具调用是独立的 async 协程。

## `qt_smoke_test` 数据流

```
qt_smoke_test (project_dir, build_type, run_seconds, build_timeout)
   │
   ├─► _clean_artifacts(proj_dir)         ← 与 qt_clean 共用
   │
   ├─► qt_build(QtBuildInput(...))        ← 调 qmake + mingw32-make
   │     └─► 成功/失败都写 .qt_mcp_last_build.log
   │
   ├─► 定位 <proj>/debug/*.exe
   │
   └─► qt_run(QtRunInput(detach=True))    ← fork .exe
         └─► run_seconds 后 qt_kill_exe()
```

## 错误处理理念

- 每个工具都返回**字符串**（不是类型化响应）——保持 MCP 协议简单，调用方可把输出 pipe 给 `tee`、`grep` 等
- 错误一律以 `"Error: "` 开头，单次 grep 即可找全
- `_parse_diagnostics` 在 `qt_build` 失败后追加结构化的 `--- diagnostics (JSON) ---` 块，便于程序消费
- 可选的 `--- json ---\n{ok, data|error}` 段（在 `QT_MCP_JSON=1` 下）作为统一的机器可读契约

## 路径沙箱

所有用户提供的路径都走 `_require_sandbox(path, what)`：

1. `path.resolve()` 求绝对路径
2. 解析后不在 `SANDBOX_ROOT` 下 → 返回错误字符串，工具短路
3. `SANDBOX_ROOT` 默认 `E:\Download_tools\QT`，可通过 `QT_MCP_SANDBOX` 覆盖（CI / 多机部署有用）

强制在 **Python 层**，不在 OS 层。理论上调用方可以 `os.chdir()` 跳出沙箱，但当前没有任何工具这么做。

## 环境变量覆盖

`server.py` 内所有文件系统路径走 `_env_path(var, default)`。在另一台机器跑同一个 `server.py`：

```bash
export QT_MCP_QT_ROOT=/opt/Qt/5.14.2/gcc_64
export QT_MCP_MINGW_BIN=/opt/mingw64/bin
export QT_MCP_SANDBOX=/home/me/qt-projects
python server.py
```

也可在 MCP 客户端的 `.mcp.json` 的 `env` 块里设。