# 演示截图

这个目录存放真实 `qt-mcp` 运行的 PNG。

每张截图通过重跑 [`../README.md`](../README.md) 里的走查步骤产出，调用方式：

```python
await server.qt_ui_action(QtUIActionInput(
    action="screenshot",
    output_path="docs/demo/screenshots/step_N_name.png",
))
```

工具用 `pywinauto.capture_as_image()`（Windows `PrintWindow`），所以 PNG 是 Qt 窗口的真正截图——即使其他窗口遮挡它也能拍清楚。

## 标准运行下的截图含义

| 文件 | 内容 | 怎么拍的 |
|---|---|---|
| `step_1_diagnose.png` | `qt_diagnose_env deep=true` 的文本输出 | （终端截图） |
| `step_2_scaffold.png` | `qt_scaffold mainwindow` 写出的文件 | （资源管理器或终端 `tree`） |
| `step_3_class_wizard.png` | 生成的 `Counter` 类文件 | （终端 `ls`） |
| `step_4_build_ok.png` | `qt_build` 末尾 "Build OK" | （终端截图） |
| `step_5_counter_running.png` | Counter 窗口，tick 中，显示 `Count: 33` | `qt_ui_action screenshot` |
| `step_6_smoke_pass.png` | `qt_smoke_test` 最终结论 | （终端截图） |

## 已有的参考截图

Jul 8 开发期的真实截图保留在 `E:\Download_tools\QT\Files\qt_mcp_demo\`，作为历史参考。它们不打包进 qt-mcp 源码树，因为引用了用户本地的 Qt 安装路径。

## 重新拍摄

```bash
# 终端 1
python -m server

# 终端 2（Claude Code 或原始 MCP 客户端）
qt_scaffold(template="mainwindow", output_dir="...")
qt_build(project_dir="...")
qt_run(executable="...", detach=True)
qt_ui_action(action="screenshot", output_path="docs/demo/screenshots/step_5.png")
qt_kill_exe(image_name="...")
```