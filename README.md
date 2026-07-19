# qt-mcp

> 一个本地 stdio MCP 服务器，把 Qt 5.14.2 + MinGW 工具链封装成 Python 工具集，让 Claude 或任何 MCP 兼容客户端可以在对话里直接搭建、构建、运行、测试、格式化、部署、检查 Qt C++ 项目。

## 项目简介

qt-mcp 把 Qt SDK 工具链（qmake / mingw32-make / windeployqt / moc / lupdate / qmllint / clang-format 等）变成可调用的 MCP 工具——Claude 调一个 `qt_build` 就等于替用户在终端跑 qmake + make。工具覆盖 Qt C++ 项目完整生命周期，从空目录到带签名的安装包。

- **协议**：MIT
- **依赖**：Python ≥ 3.10
- **平台**：Windows（依赖 pywinauto + Qt 5.14.2 MinGW）
- **实现**：单文件 `server.py`（29,795 行 Python，147 个工具，零 C++ 源码污染）
- **测试**：561 个 pytest（全过），分 light / full 两套

## 核心特点

- **完整覆盖 Qt 项目生命周期**：脚手架、构建、运行、测试、格式化、部署、签名、安装包一条龙
- **本地 FTS5 全文检索**：Qt 5.14.2 自带 6613 页文档建成索引（51 MB），100 ms 内搜到答案
- **AI 友好的诊断信息**：`qt_build` 把编译器 / moc / uic / 链接器输出解析成结构化 JSON，并给出可执行的修复建议
- **路径沙箱保护**：所有工具强制路径必须在 sandbox 根下，跨边界访问直接拒绝（`Error: ...`）
- **零样例代码污染**：所有 Qt 二进制（`*.exe` / `*.dll`）走 subprocess 调真实 Qt SDK，仓库内不引入任何 C++ 源码
- **单文件 server.py**：147 个工具全部在一个文件里（约 3 万行），跨工具共享 helpers 不重复

## 5 分钟上手

### 前置条件

- Windows 10 / Windows 11
- Qt 5.14.2 已装（默认路径 `E:\Download_tools\QT\5.14.2\mingw73_64`）
- MinGW 730_64 已装
- Python ≥ 3.10

### 安装

```bash
git clone https://github.com/fan1959/qt-mcp.git
cd qt-mcp
pip install -e .
```

### 配到 Claude Code

在 `~/.claude.json` 或 MCP 客户端配置里加：

```json
{
  "mcpServers": {
    "qt-mcp": {
      "command": "python",
      "args": ["-m", "server"]
    }
  }
}
```

### 第一次使用

重启 Claude Code，在对话里说：

> 帮我用 Qt 写一个 hello world 项目

Claude 会调 `qt_scaffold` 生成项目骨架，再调 `qt_build` + `qt_run` 编译运行。整个过程你看着终端输出 + Claude 的解释，不用手动跑命令。

### Qt 路径自定义

如果 Qt 不在默认路径，设环境变量：

```bash
set QT_MCP_QT_ROOT=D:\Qt\5.14.2\mingw73_64    # Windows
export QT_MCP_QT_ROOT=/opt/Qt/5.14.2/gcc_64   # Linux
```

## 工具一览（147 个，按 19 个分类）

所有工具都是 Python `async def`，签名见 `server.py`。

| 分类 | 数量 | 工具 |
|---|---|---|
| **项目脚手架** | 13 | `qt_scaffold` / `qt_template_scaffold` / `qt_class_wizard` / `qt_pro_edit` / `qt_pro_lint` / `qt_pro_project_graph` / `qt_module_split_init` / `qt_module_split_cmake` / `qt_qobject_invoke_property_diff` / `qt_gen_qrc` / `qt_assets` / `qt_resources` / `qt_resource_validate` |
| **构建** | 5 | `qt_build` / `qt_clean` / `qt_shadow_build_setup` / `qt_build_cache` / `qt_build_diagnostics` |
| **运行** | 8 | `qt_run` / `qt_run_trace` / `qt_kill_exe` / `qt_perf_budget` / `qt_perf_compare` / `qt_smoke_test` / `qt_dll_search_path` / `qt_diagnose_env` |
| **测试** | 5 | `qt_test` / `qt_qml_test` / `qt_test_fuzz` / `qt_sanitizer_run` / `qt_test_coverage_diff` |
| **静态分析** | 12 | `qt_clazy_check` / `qt_cppcheck` / `qt_complexity_lint` / `qt_lint` / `qt_format_check` / `qt_format` / `qt_analyze` / `qt_async_await_lint` / `qt_thread_affinity_check` / `qt_signal_slot_trace` / `qt_signal_disconnect_check` / `qt_signal_lint_fix` |
| **文档与搜索** | 5 | `qt_docs_search` / `qt_docs_gen` / `qt_documentation_lint` / `qt_documentation_auto_fill` / `qt_translate` |
| **部署与签名** | 8 | `qt_deploy` / `qt_deploy_bundle` / `qt_signature` / `qt_signature_batch` / `qt_installer_gen` / `qt_appx` / `qt_ico_create` / `qt_svg_to_png` |
| **数据库** | 6 | `qt_db_seed` / `qt_db_validate` / `qt_db_dump` / `qt_db_open_in_gui` / `qt_db_schema_diff` / `qt_db_perf_index` |
| **网络** | 4 | `qt_network` / `qt_http_client_gen` / `qt_ftp_client_gen` / `qt_asan_runtime_report` |
| **多媒体** | 2 | `qt_multimedia_setup` / `qt_audio_convert` |
| **QML** | 5 | `qt_qml_lint` / `qt_qml_perf_lint` / `qt_qml_component_gen` / `qt_qmlscene` / `qt_qml_property_linter` |
| **Qt 3D** | 1 | `qt_qtquick_3d_setup` |
| **C++ 重构** | 3 | `qt_modernize_qt5_to_qt6` / `qt_modernize_qt6_string_literal` / `qt_input_recorder` |
| **信号与槽 / QObject** | 8 | `qt_qobject_invocation_count` / `qt_qobject_invocation_history` / `qt_qobject_invoke_metadata` / `qt_qobject_invoke_connect_monitor` / `qt_qproperty_browser` / `qt_hotreload_check` / `qt_property_browser` / `qt_widget_introspect` |
| **教学与示例** | 4 | `qt_cpp_tutorial_scaffold` / `qt_graphics_view_scaffold` / `qt_input` / `qt_anim` |
| **主题与样式** | 4 | `qt_theme_gen` / `qt_qstyle_sheet_gen` / `qt_qss_inspect` / `qt_layout_check` |
| **游戏 / 棋牌** | 1 | `qt_scaffold --template chess_game / tictactoe_game / breakout_game / cards_game / music_player / tasklist / gomoku / gobang` |
| **其他实用** | 8 | `qt_achievement` / `qt_leaderboard_ui` / `qt_replay` / `qt_save` / `qt_state` / `qt_score` / `qt_timer` / `qt_translation_sync` |
| **运行时 UI 自动化** | 5 | `qt_ui_action` / `qt_widget_introspect` / `qt_runtime_props` / `qt_console_messages` / `qt_creator_open` / `qt_creator_run` / `qt_designer` |

完整列表见 [PROJECT_FILES.md](PROJECT_FILES.md)。

## 典型工作流

### 1. 从空目录到可运行 .exe

```text
你 → qt_scaffold(template=mainwindow, output_dir=F:/demo/hi)
    → qt_build(project_dir=F:/demo/hi)
    → qt_run(executable=F:/demo/hi/debug/hi.exe, detach=True)
    → qt_ui_action(action=screenshot, output_path=hi.png)
```

### 2. 加新类 + 改 .pro

```text
你 → qt_class_wizard(class_name=Counter, output_dir=F:/demo/hi)
    → qt_pro_edit(action=append, variable=SOURCES, values=Counter.cpp)
    → qt_build(project_dir=F:/demo/hi)
```

### 3. 调试编译错误

```text
你 → qt_build(project_dir=F:/demo/hi)              # 失败
    → qt_build_diagnostics(project_dir=F:/demo/hi)  # 结构化诊断：file:line + 建议
    → qt_grep(project_dir=F:/demo/hi, pattern=QPushButton)  # 验证符号存在
    → qt_class_wizard(... type=QPushButton ...)     # 一键生成
```

### 4. 部署 + 签名 + 安装包

```text
你 → qt_deploy(executable=F:/demo/hi/release/hi.exe)
    → qt_signature_batch(directory=F:/demo/hi/release, action=sign, certificate_path=cert.pfx)
    → qt_installer_gen(output_dir=F:/demo/hi/installer, exe_path=hi.exe, app_name=hi)
    → 运行 build_installer.bat 生成 .msi
```

## 环境变量

| 变量 | 默认值 | 作用 |
|---|---|---|
| `QT_MCP_QT_ROOT` | `E:\Download_tools\QT\5.14.2\mingw73_64` | Qt 5.14.2 安装根目录 |
| `QT_MCP_QT_32_ROOT` | `E:\Download_tools\QT\5.14.2\mingw73_32` | Qt 32-bit 安装目录（跑 32-bit .exe 时用）|
| `QT_MCP_MINGW_BIN` | `E:\Download_tools\QT\Tools\mingw730_64\bin` | 64-bit MinGW bin/ |
| `QT_MCP_SANDBOX` | `E:\Download_tools\QT` | sandbox 根目录，所有 MCP 输入输出必须在此目录下 |
| `QT_MCP_JSON` | （未设）| 设为 `1` 时每个工具输出末尾追加 JSON footer（调试用）|

## 架构

```
Claude / MCP 客户端
       │ stdio JSON (一行 JSON 一个命令)
       ▼
  server.py (FastMCP)
       │
       ├─ 147 个 @mcp.tool 装饰的 async def qt_xxx(params) → str
       │
       ├─ 共享 helpers
       │   ├─ _json_footer()       # 每个工具结尾加 {ok, data}
       │   ├─ _require_sandbox()   # 拦截 sandbox 外路径
       │   ├─ _strip_comments()    # 静态分析前剥离注释
       │   ├─ _qt_env()            # 拼装 Qt + MinGW 子进程环境
       │   ├─ _pro_parse()         # .pro 文件解析（生成 AST dict）
       │   └─ _run()               # 统一 subprocess 管道
       │
       └─ subprocess 调 Qt SDK 二进制
              ├─ qmake / mingw32-make
              ├─ windeployqt
              ├─ moc / uic / rcc
              ├─ lupdate / lrelease
              ├─ qmllint / qmlscene
              └─ clang-format / cppcheck
```

### server.py 内部分区（按职责）

| 区段 | 行号 | 内容 |
|---|---|---|
| imports + 常量 | 1-100 | stdlib + mcp + pydantic + 模板导入 |
| Qt 环境 + sandbox | 100-150 | `_env_path()` / `_require_sandbox()` / `_pe_bits()` |
| subprocess 管道 | 150-200 | `_qt_env()` / `_run()` / `_clean_artifacts()` / `_json_footer()` |
| `.pro` 解析器 | 200-280 | `_pro_strip_comments()` / `_pro_parse()` / `_pro_serialize()` |
| 模板 / 数据类 | 280-800 | `ScaffoldTemplate` enum + 9 个模板的 `_*_file()` 发射器 |
| Pydantic Input 模型 | 800-17000 | 每个工具一个 `QtXxxInput(BaseModel)` |
| 工具实现 | 17000-29795 | 所有 `@mcp.tool` 函数 |
| 入口 | 末 5 行 | `if __name__ == "__main__": sys.exit(main())` |

详细架构图见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 内部机制

### 路径沙箱（`_require_sandbox`）

每个工具接受的路径参数都过一遍 `_require_sandbox(path, what)`：

1. `path.resolve()` 求绝对路径
2. 若解析后不在 `QT_MCP_SANDBOX` 根下 → 返回 `Error: ... outside sandbox`
3. 工具短路返回

这意味着你不能在 sandbox 外对文件做操作。覆盖范围：

```bash
set QT_MCP_SANDBOX=D:/my_projects   # 限制只在这棵树下
```

### 错误处理哲学

- 每个工具返回**字符串**（不是类型化响应）——保持 MCP 协议简单，输出可 pipe 给 `tee` / `grep`
- 错误一律以 `Error: ` 开头——单次 grep 即可找全
- `qt_build` 失败后追加 `--- diagnostics (JSON) ---` 块，含 file/line/column/tool/code/message/**suggestion**
- `_json_footer(obj)` + `QT_MCP_JSON=1` 提供统一的 `--- json ---\n{ok,data|error}` 段（机器可读）

### 关键 helpers

| Helper | 作用 |
|---|---|
| `_json_footer(obj)` | 给每个工具输出末尾追加 `--- json ---\n{ok, ...}` 段 |
| `_require_sandbox(path, what)` | 强制路径必须在 `QT_MCP_SANDBOX` 内 |
| `_strip_comments(text)` | 静态分析前剥离 C++ / QML 注释（避免 `if (s == "if")` 被误算） |
| `_qt_env()` | 拼装 Qt + MinGW 子进程环境（PATH 注入 Qt bin / MinGW bin） |
| `_pro_parse(pro_file)` | 解析 `.pro` 文件返回 AST dict（变量 + 值列表），`_pro_serialize()` 反向 |
| `_pe_bits(exe_path)` | PE-header heuristic 判 32 / 64-bit，选对应 Qt bin |
| `_run(cmd, cwd, timeout)` | 统一 subprocess 管道，捕获 stdout/stderr/returncode |
| `_docs_index_dir()` | 懒加载 FTS5 索引（首次调 `qt_docs_search` 时构建） |

## 跑测试

```bash
cd qt-mcp
unset QT_MCP_SANDBOX        # 让所有工具用默认 sandbox
python -m pytest -q         # 全套测试
```

或跑单个套件：

```bash
python -m pytest tests/full/e2e_new_tools_v31.py -v   # 最新工具
python -m pytest tests/light/ -v                      # 快速 smoke（不需要 Qt SDK）
```

### 测试组织

| 目录 | 数量 | 何时跑 |
|---|---|---|
| `tests/light/` | 6 个套件 / <5s | 不需要 Qt SDK，跑纯 Python 逻辑（解析器 / helpers / 沙箱拒绝） |
| `tests/full/` | 555 个套件 / ~155s | 需要 Qt 5.14.2 + MinGW，跑真实 qmake + make |

每加一个新 sprint，就加一个 `tests/full/e2e_new_tools_v<N>.py`，至少 5 个 e2e 测试 + 完整 happy path / error path。

### 测试隔离模式

新工具的 e2e 测试统一用：

```python
@pytest.fixture(autouse=True)
def _qt_mcp_json(monkeypatch):
    monkeypatch.setenv("QT_MCP_JSON", "1")
```

让每个工具输出末尾有稳定 JSON footer。`_split_json()` helper 宽容解析不崩。

**CI** 在每次 push / PR 时自动跑（`.github/workflows/ci.yml`）：Windows runner + Python 3.12 + 全套 pytest。

## 项目结构

```
qt-mcp/
├── server.py              ⭐ 147 个工具全在这一个文件（29,795 行）
├── pyproject.toml         pip install 配置
├── README.md              本文件
├── CHANGELOG.md           版本历史
├── PROJECT_FILES.md       文件结构详解
├── LICENSE                MIT 协议
│
├── docs/                  架构图 + 演示截图
│   ├── ARCHITECTURE.md
│   └── demo/              qt-mcp 6 步走查
├── examples/minimal/      hello Qt 5 分钟示例 + .mcp.json
├── tests/
│   ├── light/            6 个无 Qt SDK 套件
│   └── full/             555 个 e2e 套件（每加一工具配一个 e2e_new_tools_v<N>.py）
├── .github/               issue / PR 模板 + GitHub Actions CI
└── docs_data/             Qt 6613 页文档 FTS5 索引（51 MB，build_docs_index.py 生成）
```

详见 [PROJECT_FILES.md](PROJECT_FILES.md)。

## FAQ

**Q: stdio server 加了新工具，Claude 不认怎么办？**
A: 重启 Claude Code。stdio MCP server 在启动时缓存工具列表，加完必须重启会话生效。

**Q: windeployqt 漏拷 Qt5Sql.dll / sqldrivers/ 怎么办？**
A: 在 `main.cpp` 加一行 `qDebug() << QSqlDatabase::drivers();` 强制链接 Qt5Sql。`qt_deploy` 会自动检测。

**Q: 32-bit / 64-bit 不匹配导致 .exe 一启动就崩？**
A: 跑 `qt_diagnose_env(deep=True)` 检查 PATH 顺序 + Qt bin bitness。`qt_dll_search_path` 分析缺失的 DLL。

**Q: MCP 客户端连不上 qt-mcp？**
A: 检查 `~/.claude.json` 里的 `mcpServers.qt-mcp.command` + `args`，手动跑 `python -m server` 看 stderr。

**Q: 怎么给项目定制 Qt 路径？**
A: `set QT_MCP_QT_ROOT=D:/Qt/5.14.2/mingw73_64`，重启 Claude Code。

**Q: 我的项目不在 sandbox 根下？**
A: `set QT_MCP_SANDBOX=D:/my_projects`，所有工具自动限制在这棵树下。

**Q: e2e_v<N>.py 测试有 QT_MCP_JSON 依赖怎么隔离？**
A: 套件顶部加 `pytest.fixture(autouse=True)` 设 `QT_MCP_JSON=1`，用 `_split_json()` helper 解析。

## 致谢与借鉴

本项目借鉴 / 参考以下资源：

- **[0xCarbon/qt-mcp](https://github.com/0xCarbon/qt-mcp)**：runtime introspection 套件（`qt_widget_introspect` / `qt_runtime_props` / `qt_console_messages` / `qt_layout_check` / `qt_screenshot_diff`）的核心 API 设计参考
- **SCU Wiki Qt 课件**：大一 C/C++ 实习的 Qt 基础教学材料
- **JB51《Qt 快速入门系列教程》**：62 篇教程 PDF，提供 C++/Qt API 用法参考

## 添加新工具

参考最近新增的工具流程：

1. 在 `server.py` 合适位置插入 Pydantic Input + `@mcp.tool` 函数
2. 加 e2e 测试到 `tests/full/e2e_new_tools_v<N>.py`
3. 更新 [README.md](README.md) 工具表 + [CHANGELOG.md](CHANGELOG.md)
4. 跑 `pytest -q` 验证 + 新套件全 PASS
5. 提醒用户重启 Claude Code（stdio MCP server 缓存工具列表，加完要重启才生效）

## 协议

MIT。可随便用、商用、改源码、闭源分发。详见 [LICENSE](LICENSE)。

## 贡献

欢迎 PR。提交前请确认：
- 新功能有 Pydantic Input + 完整 docstring + 至少 5 个 e2e 测试
- 现有 pytest 全 PASS
- 更新 [README.md](README.md) 工具表 + [CHANGELOG.md](CHANGELOG.md)
- `.github/PULL_REQUEST_TEMPLATE.md` 检查清单全勾

## 仓库

- **GitHub**: https://github.com/fan1959/qt-mcp
- **Issues**: https://github.com/fan1959/qt-mcp/issues
- **协议**: MIT
- **Python**: ≥ 3.10
- **平台**: Windows（依赖 pywinauto + Qt 5.14.2 MinGW）