---
name: Bug 报告
about: 出问题了——qt_build 失败、某个工具返回了看不懂的提示等
title: "[bug] "
labels: ["bug"]
---

## 发生了什么

<!-- 用一段话说清楚 bug。 -->

## 复现步骤

1. （用这些参数调这个工具）
2. （然后调这个工具）
3. （看到这个输出）

## 预期输出

<!-- 你期望看到什么。 -->

## 实际输出

```
<把工具输出粘在这儿，包括任何 "--- json ---" 段>
```

## 环境

- Windows 版本：（例如 Windows 11 23H2）
- Python 版本：（`python --version`）
- Qt 安装路径：（`echo %QT_MCP_QT_ROOT%` 或你的 `.mcp.json` 的 `env` 块）
- qt-mcp 版本：（`python -c "import server; print(server.__version__)"`）
- 涉及哪些工具：

## 日志

如果你跑了 `qt_build` 失败，请把下面输出也粘上来：

```
python -c "import server; print(open(r'<project_dir>\.qt_mcp_last_build.log').read())"
```

## 其它

<!-- 加截图、项目 repo 链接等。 -->