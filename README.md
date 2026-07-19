# qt-mcp

> 一个本地 stdio MCP 服务器，把 Qt 5.14.2 + MinGW 工具链封装成 147 个 Python 工具，让 Claude 或任何 MCP 兼容客户端可以直接搭建、构建、运行、测试、格式化、部署、检查 Qt C++ 项目，不用离开对话。

**概述**：本项目把 Qt 5.14.2 工具链（qmake / mingw32-make / windeployqt / moc / lupdate / qmllint / clang-format 等）封装成 **147 个 MCP 工具**，让 Claude 在对话里就能完成 Qt 项目的完整生命周期。MIT 协议，当前版本 `v0.4.3`。

[![Python](https://img.shields.io/badge/python-≥3.10-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.4.3-orange)](CHANGELOG.md)
[![MCP](https://img.shields.io/badge/MCP-1.28%2B-purple)](https://modelcontextprotocol.io)

---

## 项目特点

- **147 个工具**覆盖 Qt C++ 项目完整生命周期
- **本地 FTS5 全文检索**：把 Qt 5.14.2 自带 6613 页文档建成索引，100 ms 内搜到答案
- **AI 友好的诊断信息**：`qt_build` 把编译器 / moc / uic / 链接器输出解析成结构化 JSON，并给出可执行的修复建议
- **完整的 e2e 测试**：561 个 pytest，每个工具配套 happy path + error path 验证
- **零样例代码污染**：所有 Qt 二进制（`*.exe` / `*.dll`）走 subprocess 调真实 Qt SDK，不引入 C++ 源码

## V0.4.3 新增 4 个工具

| 工具 | 作用 |
|---|---|
| `qt_db_perf_index` | SQLite 索引建议器，跑 EXPLAIN QUERY PLAN 给出缺失索引 + CREATE INDEX SQL |
| `qt_qobject_invoke_connect_monitor` | 静态 connect 调用热点图：top sender / receiver / signal / slot / 文件 |
| `qt_modernize_qt6_string_literal` | `tr("中文")` → `tr(u"中文")` + 非 ASCII 字面量加 `u""` 前缀 |
| `qt_qobject_invocation_history` | Runtime 调用历史 log 解析：每方法调用次数 + 耗时 + 调用者 + 最近 timeline |

详见 [CHANGELOG.md](CHANGELOG.md)。

---

## 5 分钟上手

### 前置条件

- Windows 10 / Windows 11
- Qt 5.14.2 已装（默认路径 `E:\Download_tools\QT\5.14.2\mingw73_64`）
- Python ≥ 3.10
- MinGW 730_64 已装

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

---

## 147 个工具分类

| 分类 | 数量 | 代表工具 |
|---|---|---|
| 项目脚手架 | 13 | `qt_scaffold` / `qt_template_scaffold` / `qt_class_wizard` |
| 构建 | 5 | `qt_build` / `qt_clean` / `qt_shadow_build_setup` |
| 运行 | 3 | `qt_run` / `qt_perf_budget` / `qt_perf_compare` |
| 测试 | 4 | `qt_test` / `qt_qml_test` / `qt_test_fuzz` / `qt_sanitizer_run` |
| 静态分析 | 19 | `qt_clazy_check` / `qt_cppcheck` / `qt_complexity_lint` / `qt_doc_lint` |
| 文档与搜索 | 4 | `qt_docs_search` / `qt_docs_gen` / `qt_documentation_auto_fill` / `qt_translate` |
| 部署与签名 | 8 | `qt_deploy` / `qt_deploy_bundle` / `qt_signature` / `qt_signature_batch` |
| 数据库 | 6 | `qt_db_seed` / `qt_db_validate` / `qt_db_dump` / `qt_db_perf_index` |
| 网络 | 2 | `qt_network` / `qt_ftp_client_gen` |
| 多媒体 | 1 | `qt_multimedia_setup` |
| QML | 4 | `qt_qml_lint` / `qt_qml_perf_lint` / `qt_qml_component_gen` |
| Qt 3D | 1 | `qt_qtquick_3d_setup` |
| C++ 重构 | 3 | `qt_modernize_qt5_to_qt6` / `qt_modernize_qt6_string_literal` |
| 信号与槽 | 4 | `qt_signal_slot_trace` / `qt_signal_disconnect_check` / `qt_qobject_invoke_*` |
| Q_PROPERTY | 2 | `qt_property_browser` / `qt_hotreload_check` |
| 教学与示例 | 3 | `qt_cpp_tutorial_scaffold` / `qt_graphics_view_scaffold` |
| 主题与样式 | 2 | `qt_theme_gen` / `qt_qstyle_sheet_gen` |
| 游戏 / 棋牌 | 1 | `qt_scaffold --template chess_game / tictactoe_game / gomoku` |
| 其他实用 | 60+ | `qt_achievement` / `qt_leaderboard_ui` / `qt_input_recorder` 等 |

完整列表见 [PROJECT_FILES.md](PROJECT_FILES.md)。

---

## 环境变量

| 变量 | 默认值 | 作用 |
|---|---|---|
| `QT_MCP_QT_ROOT` | `E:\Download_tools\QT\5.14.2\mingw73_64` | Qt 5.14.2 安装根目录 |
| `QT_MCP_QT_32_ROOT` | `E:\Download_tools\QT\5.14.2\mingw73_32` | Qt 32-bit 安装目录（跑 32-bit .exe 时用）|
| `QT_MCP_MINGW_BIN` | `E:\Download_tools\QT\Tools\mingw730_64\bin` | 64-bit MinGW bin/ |
| `QT_MCP_SANDBOX` | `E:\Download_tools\QT` | sandbox 根目录，所有 MCP 输入输出必须在此目录下 |
| `QT_MCP_JSON` | （未设）| 设为 `1` 时每个工具输出末尾追加 JSON footer（调试用）|

---

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
       │   ├─ _json_footer()    # 每个工具结尾加 {ok, data}
       │   ├─ _require_sandbox()  # 拦截 sandbox 外路径
       │   └─ _strip_comments()    # 静态分析前剥离注释
       │
       └─ subprocess 调 Qt SDK 二进制
              ├─ qmake
              ├─ mingw32-make
              ├─ windeployqt
              ├─ moc / uic / rcc
              ├─ lupdate / lrelease
              ├─ qmllint
              └─ clang-format
```

详细架构图见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

---

## 跑测试

```bash
cd qt-mcp
unset QT_MCP_SANDBOX        # 让所有工具用默认 sandbox
python -m pytest -q         # 561 passed in ~3min
```

或跑单个套件：

```bash
python -m pytest tests/full/e2e_new_tools_v31.py -v   # V0.4.3 新工具（22 tests）
python -m pytest tests/light/ -v                      # 快速 smoke（不需要 Qt SDK）
```

**CI** 在每次 push / PR 时自动跑（`.github/workflows/ci.yml`）：Windows runner + Python 3.12 + 全套 561 测试。

---

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
├── examples/minimal/      5 分钟跑通的 hello Qt 示例
├── tests/                 561 个 pytest（tests/full + tests/light）
├── .github/               issue / PR 模板 + GitHub Actions CI
└── docs_data/             Qt 文档 FTS5 索引（51 MB，由 build_docs_index.py 生成）
```

详见 [PROJECT_FILES.md](PROJECT_FILES.md)。

---

## 添加新工具

参考 `qt_db_perf_index`（V0.4.3 新加）的流程：

1. 在 `server.py` 合适位置插入 Pydantic Input + `@mcp.tool` 函数
2. 加 e2e 测试到 `tests/full/e2e_new_tools_v<N+1>.py`
3. 更新 [README.md](README.md) 工具表 + [CHANGELOG.md](CHANGELOG.md)
4. 跑 `pytest -q` 验证 + 新套件 22/22 PASS
5. 提醒用户重启 Claude Code（stdio MCP server 缓存工具列表，加完要重启才生效）

---

## 协议

MIT 协议。可随便用、商用、改源码、闭源分发。详见 [LICENSE](LICENSE)。

## 贡献

欢迎 PR。提交前请确认：
- 新功能有 Pydantic Input + 完整 docstring + 至少 5 个 e2e 测试
- 现有 561 测试全 PASS
- 更新 [README.md](README.md) + [CHANGELOG.md](CHANGELOG.md)
- `.github/PULL_REQUEST_TEMPLATE.md` 检查清单全勾

## 仓库

- **GitHub**: https://github.com/fan1959/qt-mcp
- **Issues**: https://github.com/fan1959/qt-mcp/issues
- **当前版本**: V0.4.3 (2026-07-19)