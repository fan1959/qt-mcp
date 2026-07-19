# qt-mcp — 文件结构与目录导览

> qt-mcp 是一个本地 stdio MCP 服务器，把 Qt 5.14.2 工具链封装成 147 个 Python 工具，让 Claude / 任何 MCP 兼容客户端可以在对话里直接搭建、构建、运行、测试、格式化、部署 Qt C++ 项目。本文档介绍每个目录和文件是什么、为什么存在、怎么用。

---

## 一句话总结

`qt-mcp` 把 Qt SDK 工具链（qmake / mingw32-make / windeployqt / moc / lupdate / qmllint / clang-format）变成 147 个可调用的 MCP 工具——Claude 调一个 `qt_build` 就等于替用户在终端跑 qmake + make。整个项目 ~30K 行 Python，561 个测试，依赖只有 `mcp` / `pydantic` / `pywinauto` / `Pillow`。

---

## 顶层结构（5 大块）

```
Tools/qt-mcp/
├── server.py              ⭐ 147 个工具全部在这一个文件里
├── pyproject.toml         Python 包配置（pip install 用）
├── README.md              项目主页（Quick Start / Features / 工具列表 / 架构图）
├── CHANGELOG.md           版本历史（V0.1 → V0.4.3，按 Keep a Changelog 格式）
├── LICENSE                MIT 协议
│
├── docs/                  架构说明 + 演示截图
├── examples/              最小可运行 Qt 示例项目（5 分钟跑通 hello world）
├── tests/                 561 个 pytest（每加一个工具配套一个 e2e 套件）
├── .github/               issue 模板 + PR 模板 + GitHub Actions CI
│
├── docs_data/             Qt 6613 页文档的 FTS5 索引（51 MB，build_docs_index.py 生成）
├── .input_recordings/     qt_input_recorder 工具录制输出（sandbox 目录）
├── .tmp/                  qt-mcp 跑测试时的 sandbox 临时目录
└── __pycache__/           Python 自动生成
```

---

## 1. 核心文件

### `server.py` ⭐ 最重要的一个文件

29,795 行 / 1.3 MB。**147 个 MCP 工具全部在这一个文件**。

**为什么一个文件**：
- MCP 工具注册机制要求所有 `@mcp.tool(name="qt_xxx")` 装饰函数能被 FastMCP 一次性扫描；一个文件最稳
- 跨工具共享 helpers（`_json_footer` / `_require_sandbox` / `_strip_comments` 等）不会重复 147 份
- 防止模块 import 顺序 bug（部分工具相互依赖 helper，拆文件会让 import 链变长）

**结构**：
- **顶部**（约 1-100 行）：imports + 常量 + sandbox 设置
- **Pydantic Input 类**（约 100-15,000 行）：每个工具一个 `QtXxxInput(BaseModel)` 定义参数
- **工具函数**（约 15,000-29,795 行）：每个工具一个 `async def qt_xxx(params)` 函数
- **辅助 helpers**（夹在工具之间）：`_json_footer` / `_require_sandbox` / `_strip_comments` 等

**找工具**：
```bash
grep -n 'name="qt_' server.py        # 列出 147 个工具 + 行号
grep -n '^class Qt.*Input' server.py # 列出 146 个 Pydantic 输入类
```

**一个工具长这样**：
```python
class QtDbPerfIndexInput(BaseModel):
    db_file: str = Field(...)

@mcp.tool(name="qt_db_perf_index")
async def qt_db_perf_index(params: QtDbPerfIndexInput) -> str:
    # 用 sqlite3 跑 EXPLAIN QUERY PLAN
    # 给 missing-index 建议
    return text_report + _json_footer({"ok": True, "data": {...}})
```

### `pyproject.toml`

Python 包的身份证——pip install 用：

- **name**: `qt-mcp`
- **version**: `0.4.3`
- **依赖**: `mcp[cli]`（FastMCP）+ `pydantic>=2.0`（输入验证）+ `pywinauto`（Windows UI 自动化）+ `Pillow`（图像）
- **入口脚本**: `qt-mcp = "server:main"`（装完后命令行 `qt-mcp` 可调用）

### `requirements.txt`

跟 pyproject.toml 重复（冗余但 pip install -r 方便），列出 Python 依赖。

### `conftest.py`

pytest 的全局钩子——所有测试自动应用 sandbox fixture + autouse JSON footer 模式。

### `pytest.ini`

pytest 配置：`asyncio_mode = auto`（async test 不用每次写 `@pytest.mark.asyncio`）+ 测试发现路径。

### `verify.py`

启动前体检脚本——检查 Qt SDK 是否装好、Python 依赖是否齐、sandbox 目录是否可写。CI 第一步先跑这个。

### `build_docs_index.py`

**一次性脚本**：把 Qt 5.14.2 自带的 6613 页 HTML 文档扫一遍，建一个 FTS5 全文索引（SQLite），让 `qt_docs_search` 工具能 100ms 内搜 Qt 文档。

生成结果（`docs_data/qt_5_14_2_docs.db` 51 MB）被 `.gitignore` 排除——每个用户 clone 后自己跑这个脚本重建。仓库保持在 < 2 MB。

### `debug_build.py`

debug 模式辅助脚本——记录 mcp 启动参数 + 最后一次 build log 位置。

### `templates_game_framework.py`

棋牌游戏模板的源码蓝图——被 `qt_scaffold` 工具引用，生成 tictactoe / chess / gomoku / breakout 等项目骨架。

---

## 2. 测试（561 个 pytest）

`tests/` 是质量门——**所有 PR 必须保持 561 PASS / 0 FAIL**。

```
tests/
├── __init__.py
├── full/                  555 个完整 e2e 测试（需要 Qt SDK + sandbox）
│   ├── e2e_test.py
│   ├── audit_test.py
│   ├── e2e_creator_tools.py
│   ├── e2e_fixes.py
│   ├── e2e_new_tools.py           # v3 baseline（~30 tests）
│   ├── e2e_new_tools_v2.py        # v2（~12 tests）
│   ├── e2e_new_tools_v3.py        # v3（~13 tests）
│   ├── ...
│   ├── e2e_new_tools_v30.py       # V0.4.2（19 tests）
│   └── e2e_new_tools_v31.py       # V0.4.3（22 tests）
└── light/                 6 个快速 smoke 测试（不需要 Qt SDK）
    ├── e2e_gf.py
    └── e2e_new_tools_v6.py
```

**套件编号含义**：
- `e2e_new_tools.py` 是 baseline（v3 sprint 加的）
- `e2e_new_tools_v<N>.py` 是每个 sprint 加的新工具测试套件
- `e2e_new_tools_v31.py` 是 V0.4.3 新加的（22 tests 覆盖 4 个新工具）

**怎么跑**：
```bash
cd Tools/qt-mcp
unset QT_MCP_SANDBOX   # 让所有工具用默认 sandbox
python -m pytest -q     # 561 passed in ~3min
```

---

## 3. 文档

```
docs/
├── ARCHITECTURE.md              # 架构图（FastMCP + stdio + Qt SDK subprocess）
├── demo/
│   ├── README.md                # 演示说明
│   └── screenshots/
│       └── README.md            # 截图占位符（reviewer 可加 demo 截图）
```

`README.md` 在仓库根是**项目主页**——Quick Start / Features / 147 tools 列表 / Environment variables / Architecture / Test instructions 全在这。

`CHANGELOG.md` 是**版本历史**——每版加了什么工具、改了什么、修什么 bug。

---

## 4. 示例项目（examples/）

```
examples/
└── minimal/
    ├── README.md            # 怎么用 minimal 示例
    ├── .mcp.json            # Claude Code MCP 客户端配置示例（指向本仓库 server.py）
    ├── hello.pro            # 最简 Qt .pro 文件
    └── main.cpp             # 最简 Qt main.cpp（一个 QPushButton + QLabel）
```

**用途**：让用户 5 分钟跑通"Claude + qt-mcp + Qt hello world"全链路——`pip install -e .` + 把 `.mcp.json` 配到 Claude Code + 让 Claude 调 `qt_build` 编译 + `qt_run` 启动 hello world。

---

## 5. GitHub 配置（.github/）

```
.github/
├── ISSUE_TEMPLATE/
│   ├── bug.md               # Issue 模板：报告 bug
│   └── feature.md           # Issue 模板：建议新工具
├── PULL_REQUEST_TEMPLATE.md # PR 模板：自动列测试清单 + 检查项
└── workflows/
    └── ci.yml               # GitHub Actions：push / PR 自动跑 pytest
```

`ci.yml` 是质量门——每次 push 到 main 或开 PR，GitHub 自动在 Windows runner 上：
1. checkout 代码
2. 装 Python 3.12 + pip 依赖
3. 跑 `verify.py`（环境检查）
4. 跑 `pytest -q`（561 测试）
5. 任何 fail → PR 不能 merge

---

## 6. 配置文件

| 文件 | 作用 |
|---|---|
| `.gitignore` | 排除 `__pycache__/` / `docs_data/*.db`（51 MB）/ `.tmp/`（sandbox）/ `.input_recordings/` / `*.bak`（本地备份）/ Qt build artifacts（`.exe` `.dll` 等） |
| `.gitattributes` | 行尾换行规则——确保 Windows / Linux / macOS clone 后格式一致 |
| `LICENSE` | MIT 开源协议（可随便用、商用、改、闭源） |

---

## 7. 用户安装后会生成什么（不被 git 跟踪）

| 路径 | 何时生成 | 大小 |
|---|---|---|
| `docs_data/qt_5_14_2_docs.db` | 跑 `build_docs_index.py` | 51 MB |
| `.tmp/` | qt-mcp 任何工具跑测试时 | 临时（运行后清） |
| `.input_recordings/` | `qt_input_recorder` 工具录制 | sandbox 输出 |
| `__pycache__/` | Python 自动 | 几 MB |
| `dist/` / `build/` | `pip install` 或 `python -m build` | 几 MB |

---

## FAQ

### Q: 147 个工具都在 `server.py` 一个文件？

是的。设计选择：
- 一次扫完所有 API（不用 jump between files）
- 跨工具共享 helpers 不会重复 147 次
- 防止模块 import 顺序 bug

### Q: 工具都是 Python 函数吗？

是的。每个工具签名：
```python
async def qt_xxx(params: QtXxxInput) -> str:
    # ...
    return text_report + _json_footer({"ok": True, "data": {...}})
```

返回字符串（人类可读文本 + JSON footer 给 Claude 解析）。C++ 工具走 subprocess 调 Qt SDK 真正的二进制（不在仓库内）。

### Q: 为什么不每个工具一个文件？

参考 `qt_signal_slot_trace`（281 行）/ `qt_network`（273 行）等大工具——一个工具几百到 1000+ 行。拆成 per-tool 文件会让 imports + sandbox 检查 + helper 重复 147 次，得不偿失。

### Q: 怎么新加工具？

参考 V0.4.3 的 `qt_db_perf_index`：

1. 在 `server.py` 合适位置插入 `QtDbPerfIndexInput(BaseModel)` + `@mcp.tool(name="qt_db_perf_index") async def qt_db_perf_index(...)`
2. 加 e2e 测试到 `tests/full/e2e_new_tools_v<N+1>.py`
3. 更新 `README.md` "The 147 tools" 表 + `CHANGELOG.md` 加 V0.X.Y 段
4. 跑 `pytest -q` 验证 + 新套件 22/22 PASS
5. 提醒 reviewer 重启 Claude Code（stdio MCP server 缓存工具列表，加完要重启才生效）

### Q: 51 MB 的 docs_data/*.db 不 push 怎么用？

每个用户 clone 后自己跑：
```bash
python build_docs_index.py    # 生成 51 MB FTS5 索引
```

仓库保持在 < 2 MB，但功能完整。

### Q: 怎么跑全套 561 个测试？

```bash
cd Tools/qt-mcp
unset QT_MCP_SANDBOX      # 让所有工具用默认 sandbox
python -m pytest -q       # 561 passed in ~3min
```

### Q: CI 跑什么？

GitHub Actions `.github/workflows/ci.yml`：
- 触发：push 到 main / 开 PR
- runner：`windows-latest`
- 步骤：checkout → setup-python 3.12 → pip install → verify.py → pytest -q
- 任何 fail → PR 红 ✗ 不能 merge

---

## 仓库元数据

- **仓库**: https://github.com/fan1959/qt-mcp
- **当前版本**: V0.4.3 (2026-07-19)
- **协议**: MIT
- **Python**: ≥3.10
- **平台**: Windows（依赖 pywinauto + Qt 5.14.2 MinGW）