# qt-mcp 演示走查

6 步端到端 demo：从空目录到一个由 AI 驱动的运行中 Qt MainWindow。所有步骤在 Claude Code 会话里可执行（前提是服务器已注册）。

**这个 demo 证明了什么**：MCP 服务器可以搭建、构建、运行、驱动、检查 Qt 项目，全程无需任何人在 IDE 里手动点击。

---

## 第 1 步 — `qt_diagnose_env`

做任何项目工作前，确认工具链健康。

> "跑 `qt_diagnose_env` 设 deep=True。"

返回每个必需二进制的 checklist、32 位 / 64 位共存报告、PATH 顺序审计、沙箱可写性测试。把 "Required Qt tool not found" 这种问题**提前**抓出来。

---

## 第 2 步 — `qt_scaffold`

> "在 `Files/demo/counter` 搭一个 `mainwindow` 项目。"

生成可运行骨架：

```
demo/counter/
├── counter.pro
├── main.cpp
├── mainwindow.h
├── mainwindow.cpp
└── mainwindow.ui
```

9 个模板的 enum（`widget` / `mainwindow` / `dialog` / `qml_app` / `console_app` / `cards_game` / `chess_game` / `generic_game` / `game_framework`）覆盖从 CLI 工具到完整棋牌游戏骨架。

---

## 第 3 步 — `qt_pro_edit` + `qt_class_wizard`

往刚搭好的项目里加一个 Counter QObject。

> "用 `qt_class_wizard` 生成一个 Counter 类，带 `Q_PROPERTY value` 和每 100 ms tick 的 QTimer。"

写 `counter.h` / `counter.cpp` / `counter.ui`，跑 `moc`，跑 `uic`，编译一个临时二进制确认链接通过，更新 `.pro` 包含新文件。

---

## 第 4 步 — `qt_build`

> "对 `Files/demo/counter` 跑 `qt_build`。"

`qmake` 解析 `.pro`，`mingw32-make` 并行跑（默认 `-j4`）。成功时，构建日志追加到 `<project_dir>/.qt_mcp_last_build.log`。失败时，日志被解析为结构化的 `--- diagnostics (JSON) ---` 块：file、line、column、tool、code、message、**suggestion**。

典型的 gcc 错误建议：*"Looks like a header is missing. Try `qt_grep` to confirm the symbol exists, or check your `.pro` INCLUDEPATH."*

---

## 第 5 步 — `qt_run`（后台） + `qt_ui_action`（驱动）

> "把 .exe 后台启动，然后驱动 counter 界面。"

1. `qt_run(executable=..., detach=True, timeout=0)` fork 出 `.exe`，返回 PID，MCP 会话继续往下走
2. `qt_ui_action(action="click", click_button="Start")` 按 `objectName` 找到按钮并点击。counter 的 `QTimer` 开始 tick
3. `qt_ui_action(action="screenshot", output_path=...)` 把窗口截图存为 PNG。`pywinauto` 的 `win.capture_as_image()`（PrintWindow）绕过桌面合成器，即使被遮挡的窗口也能拍清楚

```
Count: 33
[Stop] [Reset]
```

这 PNG 就是 `qt_ui_action` 产出的——见 `docs/demo/screenshots/`。

---

## 第 6 步 — `qt_validate` + `qt_smoke_test`

最后跑两个 sanity check。

> "用 `qt_validate` 检查项目文件。"

遍历 `.pro`，把每个 `SOURCES` / `HEADERS` / `FORMS` / `RESOURCES` 引用标为 `[OK]` / `[MISS]` / `[OOS]`（沙箱外）/ `[BAD]`（XML 解析错误）。下次 build 前抓拼写错和过期条目。

> "跑 `qt_smoke_test` 确认项目还能构建和启动。"

`clean → build → 跑 5s → kill → 结论：PASS / FAIL`。smoke test 输出每步末尾，不用翻屏就能定位回归。

---

## 这 6 张截图说明什么

这个目录里的 6 张 PNG（`mcp_via_pid_*.png`、`counter_t*.png`、`desktop.png`）来自上述走查的真实运行。它们是 MCP 服务器确实端到端驱动 Qt 窗口的视觉证据——没有手动 UI 操作，没有启动 Qt Creator，没有预编译二进制。

---

## 这个 demo 没覆盖什么

- **Qt Creator GUI 路径**（`qt_creator_open` / `qt_creator_run`）——这些工具在 IDE 里打开 `.pro` 然后用 Ctrl+B 构建。想看 Qt Creator 在屏上时（调试 IDE 行为、教学、可视化验证）有用。见 [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md)
- **翻译流**（`qt_translate`）——独立走查：写 `tr("...")` 调用、跑 `lupdate`、手工翻译 `.ts`、跑 `lrelease`、通过 `QTranslator` 加载 `.qm`
- **CI 集成**——见 [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) 里的 GitHub Actions 配置

---

## 重跑 demo

```bash
cd E:/Download_tools/QT/Tools/qt-mcp
python e2e_test.py     # 搭 → 构建 → 跑一个类似项目，截图，kill
python e2e_new_tools_v5.py   # qt_validate / qt_run_trace / qt_smoke_test
```

`e2e_creator_tools.py` 套件重现 Qt Creator GUI 路径，需要运行中的 Qt Creator 实例，按需启用。