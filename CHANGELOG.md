# 更新日志

**qt-mcp** 的所有重要变更记录在本文件中。

格式参考 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，
项目遵循 [语义化版本](https://semver.org/spec/v2.0.0.html)。

## [0.4.3] — 2026-07-19

### 新增（4 个新工具 — 共 147 个）

V0.4.3 聚焦 **runtime + DB 性能 + 信号监控 + Qt 6 字面量迁移** —— 收尾静态分析与运行时 introspection 之间的空白，加 Qt 6 字符串字面量迁移的最终规则。

- **`qt_db_perf_index`** — SQLite 索引建议器。每列跑 `EXPLAIN QUERY PLAN SELECT rowid FROM {table} WHERE {col} = 0`；标记 plan 中出现 `SCAN`（全表扫描）的列；生成可直接粘贴的 `CREATE INDEX idx_{table}_{col} ON {table}({col});` SQL。自动识别 `INTEGER PRIMARY KEY` 列（已通过 rowid 别名隐式索引）并跳过。text + json 输出。
- **`qt_qobject_invoke_connect_monitor`** — 静态 connect 调用拓扑热图。遍历项目里的 PMF 风格（`connect(sender, &Class::signal, receiver, &Class::slot)`）和老式 `SIGNAL/SLOT` 风格 connect。按 connect 计数报告 top-N sender / receiver / signal（`Class::signal`） / slot（`Class::slot`）/ 文件。配 `qt_signal_slot_trace`（v0.2.7，它映射每条连接线）；本工具暴露热点实体热图。
- **`qt_modernize_qt6_string_literal`** — 给 `tr("字面量")` 调用和含非 ASCII 字符（CJK / emoji / 带重音的拉丁字母）的裸字符串字面量加 C++14 `u""` 前缀。三条规则：`tr_u_prefix`、`literal_u_prefix_nonascii`、`literal_u_prefix_concat`（当字面量已含非 ASCII 时去掉 `QString::fromUtf8("中文")` 包装）。跳过已加前缀的字面量（`u""`、`L""`、`QStringLiteral`、`QByteArrayLiteral`、`QLatin1String`）。补 `qt_modernize_qt5_to_qt6`（v0.3.6，已把 `QString("...")` 包装成 `QStringLiteral("...")`）。
- **`qt_qobject_invocation_history`** — `qt_qobject_invocation_count`（v0.4.2，静态）的运行时对端。解析 JSON-lines log 文件（每行一条记录：`{ts, method, args, caller, duration_ms}`），由运行中的 helper .exe（通过 `qt_invoke_helper_gen` 生成）写入。报告每方法调用次数 + 总/平均耗时 + top caller + 最近 timeline。对非 JSON / 空行宽容。按数值大小自动识别时间戳单位（秒 vs 毫秒）。

### 数字

- 147 个工具（v0.4.2 143 → +4 新增）
- 555 个 pytest 测试，全 PASS（v0.4.2 555 + e2e_v31 新增 22 − 4 个 v13/v18 json-footer 兼容旧修复）
- server.py 约 29,800 行 / 约 30 KB

## [0.4.2] — 2026-07-17

### 新增（4 个新工具 + 1 个升级 — 共 143 个）

- **`qt_qtquick_3d_setup`** — Qt 3D 应用的项目骨架（Qt3DCore + Qt3DRender + Qt3DExtras + Qt3DInput + Qt3DLogic）。4 个模板：cube_demo、sphere_demo、scene_demo、model_loader。构建系统可选 qmake / CMake。
- **`qt_qobject_invoke_metadata`**（拆分 3 of 3 #1）— 从 .h / .cpp / moc_*.cpp 静态 introspection QObject（signals / slots / Q_INVOKABLE / Q_PROPERTY READ/WRITE/NOTIFY）。
- **`qt_qobject_invoke_property_diff`**（拆分 3 of 3 #2）— 比较两套头文件的 Q_PROPERTY + signals + slots + Q_INVOKABLE 漂移；逐项新增/删除/变更 + 逐字段变更。
- **`qt_qobject_invocation_count`**（拆分 3 of 3 #3）— 按目标方法名静态统计 `.invokeMethod(` + `QMetaObject::invokeMethod(` 调用点。

### 变更

- **`qt_signature_batch`** 接受 `error_strategy` enum（continue_all | fail_fast | continue_n:N）+ 新增 `csv_report` 参数输出逐文件 CSV 摘要。`continue_on_error` bool 保留以向后兼容。

### 数字

- 143 个工具（v0.4.1 139 → +4 新增；已有工具不变）
- 555 个 pytest 测试（v0.4.1 536 → +19 e2e_v30）

## [0.4.1] — 2026-07-17

### 新增（3 个新工具 — 共 142 个）

V0.4.1 收尾 v0.3.6–v0.3.8 留下的"发布 / 易用性"缺口：
发布最后一公里部署仪式 + sanitizer 报告人话化 + 自然语言到模板的脚手架器。

- **`qt_asan_runtime_report`** — 解析 sanitizer 报告（ASan / UBSan / TSan / LeakSanitizer），把每条 finding 翻成中文 + 可执行的修复提示。翻译 20+ 常见类别（heap-buffer-overflow、use-after-free、data-race 等）到 Qt 相关的修复建议。输出格式：`text`（默认，带翻译后的 findings）、`json`（机器可读）、`summary`（仅按类别计数）。
- **`qt_template_scaffold`** — 从自然语言描述生成项目骨架。通过中英文关键词匹配（chess / tictactoe / breakout / cards / music / tasklist / game / cli / qml / dialog / widget / mainwindow）推断模板，补 `qt_scaffold`（v0.1.0）的缺口。打分相同时自动选最高分；提供 `interactive=True` 显示候选排序。
- **`qt_deploy_bundle`** — 一键打包发布：`windeployqt`（DLL + 插件）+ 可选 `signtool` codesign 全部 .exe/.dll + 可选生成 NSIS `installer.nsi` + `build_installer.bat`。每步在 JSON 里独立报告；skip 标志默认安全。

### 数字

- **142 个工具**（v0.4.1 139 → 142 是上一版数量 + 3 新增）。相对 v0.3.8 baseline（130）总增量：+12（+9.2%）。
- **536 个 pytest 测试**（v0.3.8 470 → v0.4.1 536，+66）—— 含 20 个新 e2e_v29 测试覆盖 3 个新工具（qt_asan_runtime_report 8 个、qt_template_scaffold 8 个、qt_deploy_bundle 4 个）。
- **server.py 28KB → 约 31KB**（约 3000 行新增）。

### 关键设计决策

1. **`qt_asan_runtime_report` 的查找表中文优先** —— 每个类别都有简洁的 2 行 `cn`（翻译）+ `hint`（Qt 相关修复）。Wiki URL `https://github.com/google/sanitizers/wiki` 作为未知类别的始终兜底。
2. **`qt_template_scaffold` 直接调 `_write_scaffold`**（不通过公开的 `qt_scaffold` 工具），避免跨工具派发，得到更干净的 JSON 段。
3. **`qt_deploy_bundle` 感知环境** —— `windeployqt` 跑时把 `QT_BIN_DIR` 注进 PATH；signtool 只在 `sign=True` **且**提供了 `certificate_path` 时才跑（否则跳过并警告）；NSIS 在 `installer=False` 时跳过。3 步状态报告命名每步结果（`ok / fail / skipped / error`）。
4. **测试隔离模式（`autouse=True` fixture + `_split_json` helper）** —— `e2e_v29` 模块通过 monkeypatch 在每测试设 `QT_MCP_JSON=1` 让 JSON 段稳定，并提供宽容的 JSON 解析器让测试失败消息在缺失段时不崩溃。其他 e2e 套件不受影响。

## [0.3.8] — 2026-07-10

### 新增（7 个新工具 — 共 130 个）

基于用户提供的课程材料（SCU Wiki Qt 课件 + JB51 Qt 快速入门 62 篇教程 PDF）。V0.3.8 填补 **教学性** 缺口：之前 sprint 都是工业/企业向；v0.3.8 加 7 个教学向工具 + 增强 3 个已有工具以更好地覆盖课程内容。

**新工具（7 个）：**

- `qt_cpp_tutorial_scaffold` — 为 SCU C++ 强化 9 章 12 个主题生成可运行的 C++ 教学片段：hello_world / namespace / class_object / friend / operator_overload / inheritance / polymorphism / template / type_cast / exception / iostream / stl。每个都是自洽的 .cpp，可用任意 C++17 编译器编译（不依赖 Qt）。配已有的 `qt_anim` / `qt_class_wizard` / `qt_input` 片段。
- `qt_mysql_setup` — 生成 Qt + MySQL/MariaDB starter 项目（.pro 或 CMakeLists.txt + dbmanager.h/.cpp + main.cpp + MySQL_SETUP.md）。setup md 文档两条路径：(1) 从 Qt 源码编译 QMYSQL（JB51 Ch 22）或 (2) 用 MariaDB Connector/C 做 drop-in（推荐）。补上 Qt 5.14.2 的预编译 MinGW **不带** QMYSQL 驱动 DLL 的缺口。
- `qt_http_client_gen` — 生成基于 QNetworkAccessManager 的 HTTP 客户端（QNetworkRequest + GET/POST + JSON body + User-Agent 头）。两种模式：`async`（信号 getFinished / postFinished / requestError —— UI 推荐）、`sync`（通过 QEventLoop 阻塞 —— CLI 用）。JB51 Ch 32。
- `qt_ftp_client_gen` — 生成基于 QNetworkAccessManager 的 FTP 客户端（通过 put() 上传带 uploadProgress / 通过 get() 下载带分块写 / 通过 get() 列出目录返回目录列表）。Qt 5 现代替代已移除的 QFtp。JB51 Ch 33-34。
- `qt_graphics_view_scaffold` — 生成 QGraphicsView 教学项目（Scene + View + 3 个 item：红色矩形、蓝色椭圆、绿色线 + 用 mousePressEvent / mouseMoveEvent / mouseReleaseEvent 实现拖拽）。棋牌游戏、CAD 工具、流程图的基础。JB51 Ch 19-20。
- `qt_multimedia_setup` — 生成 QtMultimedia starter（QMediaPlayer + QMediaPlaylist + QVideoWidget + QSoundEffect + sounds.qrc 打包 + placeholder click.wav + MULTIMEDIA_SETUP.md 含 DirectShow/WMF 后端笔记）。JB51 Ch 49。
- `qt_qstyle_sheet_gen` — 为 14 个 widget 选择器（QPushButton / QLineEdit / QComboBox / QListView / QTableView / QHeaderView / QStatusBar / QMenuBar / QMenu / QToolBar / QTabWidget / QGroupBox / QProgressBar / QScrollBar）的任意子集生成可用的 QSS（Qt Style Sheet）。两个主题：`light`（白底蓝色点缀）和 `dark`（深灰底蓝色点缀）。JB51 Ch 45。

### 增强（3 个已有工具）

- `qt_scaffold` — 加 4 个新的 SCU 项目库模板：`tictactoe_game`（井字棋 3x3 棋盘 + X/O 切换 + 胜负判断）/ `breakout_game`（打砖块 QTimer + paddle + bricks + 碰撞）/ `tasklist`（任务清单 QListView + QStringListModel + add/remove/clear）/ `music_player`（QMediaPlayer + Open/Play/Pause/Stop + 进度条）。脚手架模板总数从 9 → 13。
- `qt_db_seed` — 加 `mysql_check: bool = False` 参数。为 True 时追加 MySQL/QMYSQL 驱动兼容性报告（驱动 DLL 存在 + libmysql.dll / libmariadb.dll 在 PATH + mysql / mariadb CLI + 配置指南）。关键是因为 Qt 5.14.2 + MinGW 预编译**不**带 QMYSQL 驱动 —— 用户**必须**自编译或用 MariaDB drop-in。
- `qt_anim` — 加 3 个新 `animation_type` 值，发出 ready-to-paste 的 paintEvent override（不是 QPropertyAnimation）：`double_buffer`（JB51 Ch 18：QPixmap 离屏 buffer 做无闪烁绘制）/ `painter_path`（JB51 Ch 14：QPainterPath 用 moveTo / lineTo / quadTo / cubicTo / addEllipse）/ `doodle_board`（JB51 Ch 17：用 mousePressEvent + mouseMoveEvent 累积 QPainterPath 做自由绘画）。动画类型总数从 6 → 9。

### Bug 修复（2）

- `qt_anim` 最初增强把新类型分支放在 validation 检查**之后**，导致 3 个新类型（double_buffer / painter_path / doodle_board）在到达 snippet 之前就被 "invalid animation_type" 拒绝。把新类型检查移到 validation **之前**，让 3 个类型走早返回路径。被 e2e_v24 test 3 抓出。
- `_qss_dark_overrides()` 故意写成函数（不是 dict literal），这样每次调用都是新的。避免"可变默认参数"陷阱，与 `_qss_for_selectors()` 同模式。

### 数字

- **130 个工具**（v0.3.7 123 → v0.3.8 130，+7，+5.7%）
- **server.py 25802 行**（v0.3.7 23286 → v0.3.8 25802，+2516，+10.8%）
- **29 个 e2e 套件**（v0.3.7 28 → v0.3.8 29，+1 `e2e_new_tools_v24`）
- **470 个 pytest 测试**（v0.3.7 451 → v0.3.8 470，+19 e2e_v24，+4.2%；`python -m pytest -q` 470 passed in 175s）
- e2e_v24：19 个 pytest 测试，66 个 check 断言
- 130/130 工具 e2e 覆盖 + docstring 完整 + JSON 段

## [0.3.7] — 2026-07-10

### 新增（12 个新工具 — 共 123 个）

**Runtime 写入闭环（3 个工具）** —— 收尾 `qt_widget_introspect` + `qt_runtime_props` + `qt_console_messages`（只读）留下的读写缺口。现在可以同时观察和变更运行中的 Qt 应用。

- `qt_invoke_helper_gen` — 生成 Qt helper `.exe` 骨架（QApplication + 用户 QObject 子类带 `Q_PROPERTY` + `Q_INVOKABLE`），通过 stdin/stdout 行分隔 JSON 协议暴露。配 `qt_widget_introspect`；runtime introspection 三件套的**写**对端。
- `qt_qproperty_set` — 驱动运行中的 helper .exe 发 `set_property` JSON 命令。运行时设 Q_PROPERTY 值。
- `qt_meta_invoke` — 驱动运行中的 helper .exe 发 `invoke` JSON 命令。运行时调 Q_INVOKABLE / `QMetaObject::invokeMethod`。

**Build / lint / install 闭环（4 个工具）** —— 配 `qt_validate` + `qt_cmake` + `qt_build`。

- `qt_pro_lint` — 12 条 `.pro` 静态 lint 规则（重复、CONFIG 冲突、Qt5 deprecated 模块、target 命名、TEMPLATE 缺失、INCLUDEPATH 绝对路径等）。`rule_ids` 过滤，text + json 输出。配 `qt_validate`（找**缺失文件**；本工具找**语法/语义问题**）。
- `qt_shadow_build_setup` — 设 `build-debug/` + `build-release/` shadow 目录，写 `.pro.user`（Qt Creator 配置）带 `ShadowBuild=true`，加 `build_shadow.bat` 一键 debug+release 构建。配 `qt_build_cache`（ccache 需要独立目录才有效）。
- `qt_qmlscene` — 通过 `qml.exe` 预览 `.qml` 文件 + 多 DPI 截图（`QT_SCALE_FACTOR` 1.0/1.5/2.0）。配 `qt_high_dpi_test`（跑完整 `.exe`；本工具跳过构建步骤）。
- `qt_cmake_install` — 生成 `cmake/InstallRules.cmake` + `cmake/Packaging.cmake`（CPack NSIS）+ `cmake_install/Windeployqt.cmake` + `build_installer.bat`。收尾 `qt_cmake`（只生成顶层 CMakeLists.txt）留下的 CMake install/packaging 闭环。

**Conda 跨平台（1 个工具）** —— 配 `qt_conanfile_gen`（Conan）。两种并行包管理器，按团队偏好二选一。

- `qt_conda_env_gen` — 生成 `environment.yml`（conda-forge）+ `conda_install.bat` / `conda_install.sh` + `BUILD_README.md`。把 Qt 版本映射到 conda-forge 包：Qt 5（5.14.x / 5.15.x）→ 每个模块一个 `qt-*` 包；Qt 6（6.5+）→ umbrella `qt-main` + 每个模块 `qt-main-qt*`。跨平台附加依赖：Windows 给 `vs2019_win-64`，Linux 给 `libgl-devel` + `xorg-libxcb` + `xorg-libxkbcommon`。

**DB GUI 集成（4 个工具）** —— 配 `qt_db_seed`（v0.2.8，从 schema 创建 .db）。收尾"创建 SQLite 数据库 vs 真的去看它"之间的缺口。

- `qt_db_open_in_gui` — 在用户偏好的 DB GUI 客户端（默认 SQLiteStudio，老师提供的参考；可通过 `QT_MCP_DBGUI_EXE` 环境变量或 `gui_exe` 参数覆盖）中打开 `.db` 文件。后台启动。
- `qt_db_schema_diff` — 比较两个 `.db` 文件的 schema（表 / 列 / 索引）并生成迁移 SQL（`CREATE TABLE` / `ALTER TABLE ADD/DROP COLUMN` / `CREATE INDEX`）。text + json 输出。
- `qt_db_dump` — 把 `.db` 表导出为 **CSV** / **JSON** / **SQL dump**（CREATE TABLE + INSERTs）。支持单表或所有表。
- `qt_db_validate` — 跑三个检查：`PRAGMA foreign_key_check`（FK 约束违反）、`PRAGMA integrity_check`（索引健康）、**孤立行扫描**（子表中没有父表的行，即使 FK 没声明）。PASS/FAIL 结论。

### Bug 修复（2）

- `server.py` 缺 `import csv` 和 `import io`（被 `qt_db_dump` 用作 CSV 输出）。被 `e2e_v23` test 30 抓出。
- `qt_invoke_helper_gen` 的 main.cpp 模板用 Python `.format()` 处理含 `{{"ok", true}}` 的 raw 字符串 —— `format()` 把 `{"ok", true}` 当成命名占位符，抛 `KeyError`。重构成用 `__CLASS_NAME__` / `__CLASS_LOWER__` / `__PROP_NAMES__` / `__METH_NAMES__` 哨兵 + 链式 `.replace()`（避开 `{{` / `}}` 转义陷阱）。被 `e2e_v23` tests 1 和 3 抓出。

### 数字

- **123 个工具**（v0.3.6 111 → v0.3.7 123，+12，+10.8%）
- **server.py 23286 行**（v0.3.6 20791 → v0.3.7 23286，+2495，+12%）
- **28 个 e2e 套件**（v0.3.6 27 → v0.3.7 28，+1 `e2e_new_tools_v23`）
- **451 个 pytest 测试**（v0.3.6 415 → v0.3.7 451，+36 e2e_v23，+8.7%；`python -m pytest -q` 451 passed in 170s）
- e2e_v23：36 个 pytest 测试，79 个 check 断言
- 123/123 工具 e2e 覆盖 + docstring 完整 + JSON 段

## [0.3.6] — 2026-07-10

### 新增

- **`qt_conanfile_gen`** — 配 `qt_pkg_install`（通过 aqtinstall 装 Qt）和 `qt_cmake`（生成 CMakeLists.txt）。收尾跨平台依赖管理的缺口：很多 Qt 项目要发到 Windows + Linux + macOS，系统 Qt 包各不相同，Conan 是三个平台 pin 可复现 Qt 构建的事实标准。同时生成 `conanfile.py`（带 `requires` + `generators` + `env_info` 的完整 Python recipe）和 `conanfile.txt`（极简依赖列表），加 `BUILD_README.md` 带分步说明。`emit_profile='auto'` 时也写 `profiles/windows` + `profiles/linux` + `profiles/macos`（compiler.version 可配）。`use_system_qt=True` 跳过 Conan Qt 包，改用文档说明手动设 `QTDIR`。通过 `_CONAN_QT_PACKAGE` 表锚定 Conan 1.x Qt 5.14.2 / 6.5.0 包名约定（`qt/5.14.2`、`qt/6.5.0` 等）。
- **`qt_module_split_init`** — 配 `qt_scaffold`（创建新项目）和 `qt_cmake`。收尾平面 Qt 项目长到 ~1k 行后的缺口：拆成可复用 lib + 薄 app 加速重编译，让多个 app 链接同一份代码，让 lib 自包含便于测试。`plan_only=True`（默认）输出 `module_split_plan.json` 描述哪些文件去 `lib/src/` + `lib/include/<libname>/` + `app/`。`plan_only=False` 时真执行 move（带 `.qt_module_split_backup/` 安全副本）+ 写 `lib/lib.pro`（`TEMPLATE = lib`、`TARGET = <libname>`、`DEFINES += QT_MAKEDLL`）+ `app/app.pro`（链接 lib + 保留 `main.cpp` + 主窗口）+ 把根 `.pro` 重写成 `TEMPLATE = subdirs` + `SUBDIRS = lib app`。`file_patterns`（regex 列表）过滤哪些文件进 lib 目标。
- **`qt_modernize_qt5_to_qt6`** — 配 `qt_clazy_check`（标记 anti-pattern）：本工具真改源码。抓最常见的 Qt 5 → Qt 6 卡点，让一次发布升级不需要 30 分钟的 find-and-replace。规则：`qregexp_to_qregularexpression`（QRegExp → QRegularExpression，含 `#include` 行）、`q_nullptr_to_nullptr`（Q_NULLPTR[CONSTEXPR] → nullptr）、`q_foreach_to_range_for`（Q_FOREACH / foreach → range-based for）、`qvector_to_qlist`（QVector<T> → QList<T>）、`remove_aa_usehighdpipixmaps`（去掉 `QApplication::setAttribute(Qt::AA_UseHighDpiPixmaps, true)` —— Qt 6 默认）、`qtextcodec_to_qstringconverter`（QTextCodec::codecForName → QStringConverter::encodingFor）。`apply=False`（默认）输出逐文件 dry-run 预览；`apply=True` 写 `.bak` 副本 + 应用重写。`rule_ids` 过滤单跑一条规则。
- **`qt_signal_disconnect_check`** — 配 `qt_signal_slot_trace`（映射所有线）：本工具暴露**漏配 disconnect** 的情况。常见生命周期 bug：QObject connect 了一个 sender 本应在析构里显式 `disconnect()`，但开发者忘了。遍历 `.cpp` + `.cc` + `.cxx`，提每个 `connect(...)` 第一参数和每个 `disconnect(...)` 第一参数，列出整个项目里 sender 从未被 disconnect 的 connect 点。输出 text（按 sender 分组）或 JSON 每 file:line:sender。`ignore_self_disconnect=True`（默认）跳过 `disconnect(this, …)` 模式（Qt 自动处理）。严格跨线程 / DirectConnection 检查仍在 `qt_thread_affinity_check`。
- **`qt_qml_perf_lint`** — 配 `qt_qml_lint`（覆盖语法 + 类型正确性 + 少量缓存规则）：本工具聚焦 QML 重 UI 的**运行时性能**。规则：`inline_js_too_long`（函数体 > 50 行 —— 移到 .js，QML JIT 内联 JS 比模块 .js 慢）、`image_synchronous_load`（`Image { … asynchronous: false }`）、`transparent_mousearea`（`visible: false` 而无 `enabled: false`）、`loader_frequent_sourcechange`（每帧 source URL 变更）、`deep_component_nesting`（> 5 层 —— 深 QML 层级增加 binding 评估开销）、`createobject_in_repeater`（在 Repeater delegate 里 `createQmlObject` / `createObject` —— 每项频繁分配）。text + json，severity info vs warning，`rule_ids` 过滤，`file_patterns` 可配。纯正则；补 qmllint。

### 从 polish_plan 候选中砍掉

- `qt_qobject_invoke` —— 与 v0.3.5 同理由：需要 Qt helper `.exe` 桥接跨进程调 slot，超出单 sprint 工作量。Runtime introspection 由 `qt_widget_introspect` + `qt_console_messages` + `qt_runtime_props` 覆盖。
- `qt_gammaray_attach` —— 依赖 KDAB GammaRay（外部商业/开源工具）；runtime introspection 已由已有 5 个工具覆盖。
- `qt_qml_performance_lint`（深版）—— 完全在 v0.3.6 实现为 `qt_qml_perf_lint`，不再推迟。
- `qt_resource_validate`（per-platform 版）—— v0.3.4 的 8 条基础规则已足够。
- `qt_qtquick_3d_setup` —— Qt 5.14 的 `Qt Quick 3D` 是早期 preview；与已有 9 个脚手架模板冲突。若用户有需求再推到 v0.3.7+。

### Bug 修复（5）

- `qt_modernize_qt5_to_qt6` 初版用 `Path.with_suffix(".bak")` 算备份路径；这生成 `main.bak`（不是 `main.cpp.bak`）。改成 `bak = fp.parent / (fp.name + ".bak")`。被 `e2e_v22` test 11 首跑抓出。
- `qt_qml_perf_lint` 初版在跑 regex 窗口前用单行 guard（`"Image" in line and "asynchronous" in line`）—— 这漏掉跨行的 `Image { ... asynchronous: false }` 块。改成 `re.finditer(r"\bImage\s*\{[^}]*?asynchronous\s*:\s*false", text, re.DOTALL)`，跨整 brace-balanced 块走。`transparent_mousearea` 同修。被 `e2e_v22` tests 20、21、23 抓出。
- `qt_qml_perf_lint` 和 `qt_modernize_qt5_to_qt6` 文件过滤列表的 path-parts skip 集里含 `".tmp"` —— 但 `SANDBOX_TMP` 在 `E:\Download_tools\QT\.tmp\` 下，任何在 `SANDBOX_TMP/.../main.qml` 下建项目树的测试都被静默跳过（`Files scanned: 0`）。从两个 skip 列表去掉 `.tmp`。这是同一 v0.2.5（`qt_cmake`）和 v0.3.2（`qt_format_check`）教训在 v0.3.6 重现 —— 写成行内注释 "NO .tmp — would skip files under SANDBOX_TMP"。被 `e2e_v22` tests 11 + 25 二跑抓出。
- `e2e_v22` test 11（`qt_modernize_qt5_to_qt6 apply=True`）最初断言 `"ok" in out.lower()` —— 但 modernize 摘要不发字面 "OK"（只有结构化 `=== … ===` 头）。把成功检查改成 `"===" in out`，匹配实际输出。
- `e2e_v22` test 7（`qt_module_split_init` `lib.pro has TARGET = engine`）最初比较字面 `TARGET = engine` —— 但 recipe 生成器输出 `TARGET   = engine`（4 空格对齐）。改成 `re.search(r"TARGET\s*=\s*engine", text)`，容忍任意空白布局。

### 数字

- **111 个工具**（v0.3.5 106 → v0.3.6 111，+5，+4.7%）
- **server.py 20791 行**（v0.3.5 19395 → v0.3.6 20791，+1396，+7.2%）
- **27 个 e2e 套件**（v0.3.5 26 → v0.3.6 27，+1 `e2e_new_tools_v22`）

### 关键设计决策

- `qt_module_split_init` 默认 `plan_only=True` —— 每个破坏性 move 必须显式 opt-in，配已有模式（`qt_documentation_auto_fill.apply=False`、`qt_translation_auto_fill.apply=False`、`qt_signal_lint_fix.apply=False`）。
- `qt_conanfile_gen` 同时写 `conanfile.py`（重）+ `conanfile.txt`（轻）。不同团队偏好其一；同时发让用户删掉不需要的。
- `qt_modernize_qt5_to_qt6` 故意保守：只做文本无歧义等价的转换。复杂改写（如 `QStringLiteral` vs `u""` 字面量合并、signal-pointer 语法迁移）超出范围 —— 需要 AST 级分析。
- `qt_qml_perf_lint` 严重度配色：`inline_js_too_long` / `image_synchronous_load` / `deep_component_nesting` / `createobject_in_repeater` 是 `warning`（影响真实性能）；`transparent_mousearea` / `loader_frequent_sourcechange` 是 `info`（上下文相关）。
- 五个新工具都用 `_require_sandbox(...) -> error_string` 约定；都调 `_json_footer(...)`；都带完整 Args / Returns / Raises docstring；都列在 `qt_cheatsheet`。

## [0.3.5] — 2026-07-09

### 新增

- **`qt_complexity_lint`** — McCabe 风格圈复杂度（C++ 函数级）。遍历 `.cpp / .cc / .cxx / .h`，regex 提函数签名，brace-match 每个函数体，剥离注释 + 字符串/字符字面量（这样 `if (s == "if")` 不计数），然后数分支关键字（`if` / `else if` / `while` / `for` / `case` / `catch`）+ 短路操作符（`&&` / `||`）+ 三目（`?:`）。McCabe = 1 + 计数。标记复杂度 ≥ `threshold`（默认 12，经验法则 "10±2"）的函数。补 cppcheck / clazy / qmllint 不覆盖的"逐函数复杂度"维度（cppcheck 覆盖跨过程路径，不覆盖逐函数分支）。text + json 输出 + 平均 + 结论（PASS/FAIL）。`exclude_dirs` 跳过 build 目录 / `.git` / `node_modules`。零新依赖 —— 纯正则。配 `qt_clazy_check`（anti-pattern）、`qt_cppcheck`（真 C++ 静态分析）、`qt_signal_slot_trace`（信号图）、`qt_format_check`（风格）。
- **`qt_git_audit`** — 配 `qt_git_init`（v0.3.0，只初始化仓库）。审计已有仓库历史，暴露一般 Qt 工具不报的项目治理信号：**热文件**（按 commit 数 top-N，提示重构/抽取候选）、**bus factor**（头号贡献者占比 %；>60% = 高风险，>40% = 警戒）、**churn**（在 `since_days` 窗口里 LOC 加/删 + 密度 LOC/天）、**stale branches**（`stale_days` 内无 commit）、**最大 commit**（单 commit 文件变更数最大 —— 抓"顺手大改"）。subprocess `git log --pretty=format --numstat` + `git for-each-ref --format` 遍历。text + json 输出。
- **`qt_appx`** — 配 `qt_installer_gen`（v0.2.8 —— 本地分发的 NSIS / Inno Setup）。生成 Microsoft Store 发布所需制品：`AppxManifest.xml`（带 `runFullTrust` capability —— Qt 应用必需）、`build_appx.bat`（顺序跑 `makeappx.exe pack` + `signtool sign`）、`appx_logos.md`（文档四个必需 PNG logo 尺寸 —— 50/44/150/310）。和 `qt_installer_gen` 一样只生成 —— 不调 Windows SDK 工具，因为它们不随 Qt SDK 发。`architecture` ∈ {`x86`、`x64`、`arm64`}。包名由 publisher CN + app_name 派生，sanitize 成 reverse-DNS 形式。
- **`qt_ide_metadata`** — 配 `qt_creator_open`（只针对 Qt Creator）。生成 IDE metadata，让用户从 **VSCode** 或 **CLion** 调试 Qt 项目而不用 Qt Creator。`.vscode/launch.json`（gdb 调试配置，自动选 mingw32/64）、`.vscode/tasks.json`（qmake / build / run / clean）、`.vscode/c_cpp_properties.json`（includePath + defines 通过 `_pro_parse` 从项目 `.pro` 提取）、`.vscode/extensions.json`（推荐：`ms-vscode.cpptools` + `cmake-tools` + `jbenden.c-cpp-flyclang` + `gitlens`）。`ide='both'` 还写 `.idea/workspace.xml` 给 CLion。`launch_exe` 为空时从 `build-debug/debug/*.exe` 等自动检测 .exe。
- **`qt_runtime_props`** — 配 `qt_widget_introspect`（展示 widget 树形状）。深入一层，通过 pywinauto 读每个 widget 的**实时 accessible properties**（从 Qt `setAccessibleName` / `setAccessibleDescription` + `setObjectName` 通过 UI Automation 映射）。借自 `0xCarbon/qt-mcp` 的 `qt_props` 概念。可以 attach 到运行中的 `process_id` 或自动启动 `executable`（返回前总 kill）。快照每个有 `objectName` + 文本的 widget，打印当前状态。完整 `QMetaObject::property()` 值需要编译一个 helper 进项目 —— 每次输出末尾打印 ready-to-paste 提示。
- **`qt_test_fuzz`** — 配 `qt_sanitizer_run`（内存安全）、`qt_smoke_test`（smoke）、`qt_perf_budget`（perf）、`qt_test`（单元测试）。收尾质量门四足里的"fuzzing"：smoke / perf / correctness / crash-with-malformed-input。生成 libFuzzer 框架（`LLVMFuzzerTestOneInput` + 有 `__has_libfuzzer` 时的 `LLVMFuzzerRunMain` main）包装用户指定的 `target_function`（Q_INVOKABLE），加 `.pro` patch 片段（`QMAKE_CXXFLAGS += -fsanitize=fuzzer-no-link -fno-omit-frame-pointer`、`QMAKE_LFLAGS += -fsanitize=fuzzer -lstdc++`），加 `fuzz_README.md` 文档 MinGW-vs-Clang 兼容性 + 4 步用法。MinGW 自带 GCC 7.x 不带 libFuzzer（自带的 GCC 比支持 fuzzer 的版本老）；README 明确警告并推荐 `compiler='clang++'`（LLVM 官方安装器）以获得完整 libFuzzer 支持。

### 从 polish_plan 候选中砍掉

- `qt_qobject_invoke` —— 与 `qt_ui_action` + `qt_widget_introspect` + `qt_console_messages`（都是 runtime-introspection 变种）重叠。需要 Qt helper `.exe` 桥接跨进程调 slot，超出单 sprint 工作量。
- `qt_gammaray_attach` —— 依赖 KDAB GammaRay（外部商业/开源工具）；runtime introspection 已被 `qt_widget_introspect` + `qt_console_messages` 充分覆盖。
- `qt_qml_performance_lint` —— 与 `qmllint` 内置 `ListView cacheBuffer` / `Repeater` nesting 等性能规则重叠。
- `qt_resource_validate`（深版）—— v0.3.4 的 8 条基础规则已覆盖命名 / 冲突 / 深度 / 大小 / 前缀。per-platform 规则集 + 自动 fix 视为边际。

### 数字

- **106 个工具**（v0.3.4 100 → v0.3.5 106，+6，+6.0%）
- **server.py 19395 行**（v0.3.4 17968 → v0.3.5 19395，+1427，+7.9%）
- **26 个 e2e 套件**（v0.3.4 25 → v0.3.5 26，+1 `e2e_new_tools_v21`）
- **390 个 pytest 测试**（v0.3.4 367 → v0.3.5 390，+23，+6.3%）

### v0.3.6 更新 —— 详见上面 [0.3.6] 段

- **111 个工具**（106 → 111，+5）
- **server.py 20791 行**（19395 → 20791，+1396，+7.2%）
- **27 个 e2e 套件**（26 → 27，+1 `e2e_new_tools_v22`）
- **415 个 pytest 测试**（390 → 415，+25，+6.4%；全套 **415 passed in 155s**）
- `e2e_v21`：**23 个 pytest 测试 / 52 个 checks**，2 修后首跑全过。
- 106/106 工具有 e2e 覆盖 + docstring（Args / Returns / Raises / Note）+ JSON 段。

### 关键设计决策

- **`qt_complexity_lint` 纯正则** —— 镜像 `qt_clazy_check` 的零依赖思路。备选（libclang Python 绑定）为边际准确度换重依赖；纯源码 McCabe 足够 CI gate。
- **`qt_complexity_lint` 剥字符串/注释** —— 这样 `if (s == "if")` 不计数（与 `qt_signal_slot_trace` 通过 `_sst_strip_comments` 用的同一招）。
- **`qt_git_audit` 从 `os.environ.copy()` 起** —— 测试里传 `env=` 给 subprocess 会清空 `HOME`/`PATH`，在某些 Windows 配置下会让 `git init` 出问题。（v0.3.4 qt_test_fuzz 的坑）
- **`qt_appx` 不调 `makeappx.exe`** —— Windows SDK 不随 Qt 5.14 SDK 发；只生成制品 + 构建脚本（用户装好 SDK 后跑 `build_appx.bat`）。同 `qt_installer_gen`（不调 NSIS）的模式。
- **`qt_ide_metadata` 从 `.pro` 抽 `INCLUDEPATH` + `DEFINES`** —— 通过已有 `_pro_parse` + `_pro_tokenize` helpers —— 不重写 qmake 语法。`c_cpp_properties.json` 引用绝对 Qt include 路径，让 IntelliSense 首次打开就能用。
- **`qt_runtime_props` 是 widget property 快照，不是完整 QMetaObject introspection** —— 后者需要在目标项目里编译一个 helper .exe（我们不能从进程外读 QMetaObject 状态）。工具打印 ready-to-paste 提示，指向未来 `qt-mcp` helper 片段，给需要完整 introspection 的用户。
- **`qt_test_fuzz` 只生成，不构建/跑** —— `-fsanitize=fuzzer` 不被 MinGW 自带 GCC 7.x 支持，`clang++` 可能没装。自动构建在常见 MinGW-only 配置上总失败。README 解释 4 步手动流。

### 模块级一致性

- 与已有 25+ 个模块级正则常量（如 `_QRC_FILE_RE`、`_INPUT_RECORDER_RECORD_PY`、`_HR_QPROP_RE`、`_LAYOUT_CHECK_RULES`、`_AFFINITY_RULES`、`_RESOURCE_VALIDATE_RULES`、`_LCOV_*_RE`）无重名。所有新 pattern 加前缀 `_CX_` / `_GA_` / `_APPX_*` / `_IDE_*` / `_RP_*` / `_FUZZ_*`。

## [0.3.4] — 2026-07-09

### 新增

- **`qt_perf_compare`** — 配 `qt_perf_budget`（v0.3.2）：那个工具检查"对预算是否够快"；本工具检查"和上次是否一样快"。读 baseline JSON（来自 `qt_perf_budget` 或上一次 `qt_perf_compare`），spawn `.exe`，通过同样的 `_perf_first_cpu_active`（psutil）+ `_perf_find_window_for_pid`（pywinauto）helpers 测新的 `first_cpu_ms` + `first_window_ms`，与 baseline 对比，任何 delta < `regression_ms`（默认 200ms）即报告 `PASS`，否则 `FAIL`。返回前总 kill 启动的进程。CI gate 应对"这次发布是不是变慢了？"。
- **`qt_resource_validate`** — 配 `qt_resources`（v0.2.7）：那个工具的 `validate` action 只检查文件存在 + 重复条目；本工具深度验证，8 条规则：`naming_convention`（文件名必须匹配 `^[a-z0-9_-/.]+$` —— 无空格、无大写、无特殊字符）、`case_collision`（两个只大小写不同的条目 —— 在 Windows / macOS 上撞）、`path_too_deep`（深度 > `max_path_depth` 默认 8）、`file_too_large`（> `max_file_size_kb` 默认 512 KB —— 资源加载慢）、`prefix_conflict`（两个 `<qresource prefix>` 块子路径重叠）、`duplicate_entry`、`missing_on_disk`、`unusual_extension`（`.exe / .dll / .so / .bat / .cmd / .sh / .ps1 / .msi`）。复用 `_qrc_parse` helper。按 severity 计数 finding + `result` PASS/FAIL（error 级 finding 失败）。text + json 输出。
- **`qt_test_coverage_diff`** — 配 `qt_coverage`（v0.2.3）：那个工具生成单个 lcov `.info`；本工具比较两个 `.info` 文件（baseline vs 当前）以检测覆盖率回归。自写 lcov 解析器（`_LCOV_SF_RE` / `_LCOV_LF_RE` / `_LCOV_LH_RE`）按文件抽 `{filename: (LF, LH)}`。算逐文件 delta、整体 delta，列出回归（delta < −`regression_threshold`）和改进。`result` 是 `FAIL` 若任一逐文件下降 > threshold 或整体覆盖率下降 > threshold。`source_filter` 子串可限制范围到 `src/` 等。text + json 输出。CI gate 防覆盖率回归。
- **`qt_screenshot_baseline_capture`** — 配 `qt_screenshot_diff`（v0.2.7）：那个工具比较两张 PNG；本工具自动**采集** baseline PNG（跨多 DPI 缩放）。对每个 `scale_factors` 值（默认 `[1.0, 1.5, 2.0]`）：用 `QT_SCALE_FACTOR` spawn `.exe`，sleep `wait_seconds`，通过 `pywinauto.capture_as_image()` 截窗口，存为 `baseline_<scale>x.png`，算 sha1。写 `manifest.json` 带 `{label, executable, captured_at, scale_factors: [...]}` 便于追溯。返回前总 kill 启动的进程。text + json 输出。视觉回归 CI 流：采 baseline → 改代码 → diff 当前 vs baseline。
- **`qt_console_messages`** — 配 `qt_log`（v0.2.2）+ `qt_run_trace`（v0.2.0）：那些工具分析已写的 log 文件或在 spawn 时设环境变量；本工具**attach** 到运行中的 Qt 进程（或 spawn 一个），通过 pywinauto + UI Automation 读控制台类文本 widget（`QPlainTextEdit` / `QTextEdit` / `QLabel` / `QStatusBar`）。借自 `0xCarbon/qt-mcp` 的 `qt_messages` 概念。应用 `level_filter` regex（默认 `debug|warning|critical|fatal`），按 `max_messages` 截断（默认 500），可选 `auto_id_contains` 子串过滤 `objectName`。返回前总 kill 启动的进程。text + json 输出。

## [0.3.3] — 2026-07-09

### 新增

- **`qt_widget_introspect`** — 借自 `0xCarbon/qt-mcp` 的 runtime widget 树三件套（`qt_snapshot` / `qt_find_widget` / `qt_widget_details`）。通过 pywinauto + UI Automation 检查**运行中**的 Qt 应用，三种 action 合一个工具：`snapshot`（完整 widget 树作嵌套 JSON，可配 `max_depth`）、`find`（按 `name_contains` / `type_contains` / `text_contains` 搜索，AND 组合，返回扁平匹配列表）、`details`（按 `auto_id` —— Qt `setObjectName` 暴露为 UI Automation 的 `AutomationId` —— 拿 widget 的完整属性）。可 attach 到运行中的 `process_id` 或自动启动 `executable`（后台，总 kill）。json 输出。配 `qt_ui_action`（**驱动** action）—— 本工具**观察**状态。
- **`qt_layout_check`** — `.ui` 文件（用 ElementTree 解析 XML）的静态布局 anti-pattern 检查。借自 `0xCarbon/qt-mcp` 的 runtime `qt_layout_check`，本工具静态跑（不启动 app）。5 条规则：`widget_no_layout_parent`（warning）、`deep_nesting`（> 5 层，warning）、`duplicated_object_name`（破坏 `findChild` / UI Automation，warning）、`layout_no_stretch`（info）、`fixed_size_in_expanding_layout`（info）。Severity 过滤；text + json 输出。
- **`qt_cppcheck`** — 在目录或单文件上跑 `cppcheck --json --library=qt`。防御性 JSON 解析器（cppcheck 有时按文件发一个对象，有时发单个含 `diagnostics` 数组的对象）。按 severity 聚合计数（`error` / `warning` / `style` / `performance` / `portability` / `information`）成 CI 友好报告。通过 `QT_CPPCHECK_EXE` 环境变量 → `PATH` 自动找 `cppcheck`；显式 `cppcheck_exe` 覆盖两者。Severity 过滤。text + json 输出。补 `qt_clazy_check`（纯正则，零依赖）和 `qt_lint`（cpplint + qmllint + clang-tidy）—— `qt_cppcheck` 调真 `cppcheck` 二进制做更深分析。
- **`qt_thread_affinity_check`** — 静态分析 QObject signal/slot 跨线程错误，`qt_async_await_lint` 抓不到。4 条规则：`direct_connection_cross_thread`（同文件里 Qt::DirectConnection + `moveToThread()` —— warning）、`emit_without_queued_connection`（emit + `moveToThread()` —— info）、`qthread_run_without_exec`（QThread 子类 `run()` 里没 `exec()` —— warning）、`qobject_constructed_in_worker_thread`（`QThread::run()` / `QRunnable::run()` 里 `new QObject()` —— info）。每条规则有 `requires` 前置条件，所以没用 threading 原语的文件不会被误标。text + json 输出。配 `qt_async_await_lint`（async-pattern 正则）和 `qt_signal_slot_trace`（连接图）。
- **`qt_sanitizer_run`** — 用 `-fsanitize=address`（默认） / `address,undefined` / `undefined` / `thread` 构建 Qt 项目，然后跑一下抓 sanitizer 诊断。流程：把项目拷到 `sanitizer-<type>-<buildtype>/`，patch `.pro` 加 `QMAKE_CXXFLAGS += <flag>` + `QMAKE_LFLAGS += <flag>`（幂等），`qmake` + `mingw32-make`，用 `ASAN_OPTIONS=halt_on_error=1` / `UBSAN_OPTIONS=print_stacktrace=1` / `TSAN_OPTIONS=second_deadlock_stack=1` spawn `.exe` 跑 `run_seconds`，解析输出找已知 sanitizer 错误标记（`==ERROR: AddressSanitizer`、`runtime error:`、`WARNING: ThreadSanitizer`、`SUMMARY: AddressSanitizer`），报告 `PASS` / `FAIL`，`keep_sanitizer_build=True` 之外总 `distclean`。MinGW 兼容（ASan + UBSan 组合在 MinGW 和 MSVC 都可用；`-fsanitize=thread` 需要 pthreads，在 Windows 上可能链接不干净）。配 `qt_smoke_test`（smoke = 能不能跑）+ `qt_perf_budget`（perf = 跑得快不快）—— 本工具查**常见内存 / UB 错误会不会崩**。

## [0.3.2] — 2026-07-09

### 新增

- **`qt_translation_sync`** — 配 `qt_translation_validate` 和 `qt_translation_auto_fill`。扫项目的 `tr("...")` 调用（基于 regex，处理 `tr("s")` 和 `tr("s", "ctx")` 两种形式），解析目标 `.ts` XML，做 diff：报告哪些源字符串在 `.ts` 缺失、哪些 `.ts` 条目在代码里不再被引用。`apply=True` 时给缺失的字符串追加 `<message>` stub（type="unfinished"）到 `.ts`（带 `.bak` 备份）并报告新覆盖率。i18n 流现已完成闭环：`validate`（覆盖率报告）→ `sync`（源 ↔ .ts diff）→ `auto_fill`（LLM 翻译）。
- **`qt_async_await_lint`** — Qt 异步/并发 anti-pattern 静态分析。7 条规则：`qtconcurrent_blocking_in_main`（GUI 线程上 QtConcurrent::blockingMapped/...）、`qfuture_waitforfinished`（QFuture::waitForFinished 阻塞调用线程 —— 改用 QFutureWatcher + finished 信号）、`qthreadpool_direct_start`（QThreadPool::start(new QThread) 泄漏）、`qfuturewatcher_unwired`（声明了 QFutureWatcher 但没看到 setFuture() / connect）、`qthread_no_eventloop`（QThread 子类 `run()` 里没 exec()）、`movetothread_after_connect`（connect() 之后调 moveToThread() —— 把连接锁到旧线程）、`qrunnable_no_autodelete`（QRunnable 没显式 autoDelete 策略）。按 `min_severity`（info/warning）过滤；text + json 输出。
- **`qt_hotreload_check`** — 配 `qt_property_browser`。校验 Q_PROPERTY 声明：`missing_notify`（READ 没 NOTIFY → QML / 绑定无法响应变更，warning）、`missing_read`（无 READ accessor → error）、`constant_with_write`（CONSTANT + WRITE 矛盾 → error）、`member_with_read`（MEMBER 和 READ 都有 → info，二选一）、`notify_signal_not_found`（NOTIFY 引用的 signal 不在 `signals:` 块里 → error）、`member_variable_not_found`（MEMBER 引用的成员未声明 → error）、`write_setter_not_found`（WRITE 引用的 setter 没声明 → error）。text + json 输出。
- **`qt_perf_budget`** — CI 友好启动时间 gate。启动 `.exe`，测从 spawn 到第一次非零 CPU 活动（事件循环进入的代理）和到第一个顶层窗口出现（通过 `pywinauto.find_windows(process=pid)`）的时间，与 `budget_ms`（默认 2000ms）对比，报告 `PASS` / `FAIL`，返回前总 kill 启动的进程。配 `qt_smoke_test`（查"能不能跑"）；本工具查"跑得**够不够快**"。
- **`qt_format_check`** — 配 `qt_format`（**修**格式）。通过 `clang-format --output-replacements-xml` 审计 `.h` / `.cpp` / `.cc` / `.cxx` 目录，把逐文件 pass/fail 聚合成单条 CI 友好报告（total / clean / dirty / error 计数 + 总替换数），加 `init_clang_format=True` 从六种内置风格（llvm / google / chromium / mozilla / webkit / qt —— 最后一个派生自 Qt 6 的 `qt.git/.clang-format`）之一生成模板 `.clang-format`。幂等：永不覆盖已有 `.clang-format`。text + json 输出。

### Bug 修复

- **`qt_property_browser`** —— v0.2.8 `qt_property_browser` 在模块级定义了 `_QPROP_RE` 正则（带命名组 `type` / `name` / `rest`）；v0.3.2 `qt_hotreload_check` 在模块级重声明 `_QPROP_RE` 为**不同**形状（无 `rest` 组、无模板支持），静默覆盖了 v0.2.8 的正则，打破 4 个 e2e_v13 测试对 `qt_property_browser` 的断言。把 v0.3.2 的正则重命名为 `_HR_QPROP_RE`（同伴 pattern 也改成 `_HR_QPROP_TAKE_VALUE` / `_HR_QPROP_BOOL_KW`）以恢复 `qt_property_browser` 行为。（E2E 在同 sprint 内抓到回归。）
- **`qt_format_check`** —— 初版在 skip-dir 集里列了 `.tmp`，把所有 `SANDBOX_TMP` 下的 `.cpp` 排除掉（`SANDBOX_TMP` 在 `E:\Download_tools\QT\.tmp\…` 下）。这是 v0.2.5 时代影响 `qt_cmake` 和 `qt_grep` / `qt_qml_lint` 的同一 bug。从 skip 列表去掉 `.tmp`（故意 —— `SANDBOX_TMP` 是 sandbox 测试目录，不是 build artifact）。
- **`qt_hotreload_check`** —— `signal_re` 初版用 `r"signals\s*:\s*(?:public\s+)?(?:protected\s+)?(?:[\w:]+\s+)?(\w+)\s*\("` 加 `re.findall` —— 这只匹配 `signals:` 块后的**第一个** signal（`findall` 跳到第一个匹配后错过其余）。改成 body-extraction 思路：匹配完整的 `signals: …` 块到下一个 access-specifier 或 `}`，再收里面的每个 `name(`。被 e2e_v18 test 12 抓出（`does NOT flag valueChanged`）。
- **`qt_hotreload_check`** —— 初版 `QPROP_RE` 把 `Q_PROPERTY(double constantPi READ constantPi CONSTANT)` 解析成 type=`double constantPi READ constantPi` name=`CONSTANT`（`type` 组贪心吃了 READ 子句）。改成在第一个 keyword 边界做 `prefix / attrs` 切分：prefix 变 `"<type> <name>"`（按最后空白切分），然后 attrs 解析尾随子句。手动 smoke test 抓出。
- **`qt_hotreload_check`** —— 方法收集正则 `r"…\s*;"` 只匹配 `;` 结尾的声明，漏了 `void setValue(int v) {}` 这种 inline `{}` 定义（Qt 头里很常见）。放宽到 `(?:\s*;|\s*\{)`。被 e2e_v18 test 15 抓出。

## [0.3.1] — 2026-07-09

### 新增

- **`qt_documentation_auto_fill`** — 配 `qt_documentation_lint`。找 `.h` / `.cpp` / `.qml` 里每个未文档化的 public 函数，调 LLM（默认 Anthropic Claude 3.5 Sonnet；备选 OpenAI GPT-4o-mini）生成 doxygen `@brief` / `@param` / `@return` 块，输出 unified-diff 预览。默认 `apply=False` 显示 diff；`apply=True` 写回（带 `.bak` 副本）。需要 `ANTHROPIC_API_KEY` 或 `OPENAI_API_KEY` 环境变量。把一个文件里的所有未文档化函数批到一次 LLM 调用里以省 token。
- **`qt_translation_auto_fill`** — 配 `qt_translation_validate`。解析 `.ts` XML，找每个 `<message>` 带 `type="unfinished"` 的翻译，调 LLM 把 `<source>` 文本翻译到文件声明的语言（如 `zh_CN`、`en_US`、`fr`），每调用批 `batch_size` 条（默认 20）。默认 `apply=False` 显示 diff；`apply=True` 写回 `.ts`。保留 XML 结构、转义翻译中的特殊字符、支持 `target_language` 过滤以在多个 `.ts` 文件里只处理一种语言。
- **`qt_signal_lint_fix`** — 配 `qt_signal_slot_trace`。4 条 fix 规则，每条可单独 toggle：`unique_connection`（对已经有 `Qt::AutoConnection` / `DirectConnection` / `QueuedConnection` 的 5 参数 connect 调用 OR 加 `Qt::UniqueConnection`）、`queued_connection`（在 connect 调用 1500 字符内找到 `// @thread:main` 或 `// @thread: ui` 标记时加 `Qt::QueuedConnection`）、`functor_to_pointer`（Qt 5 `SIGNAL(class::sig())` / `SLOT(class::slot())` 宏 → Qt 6 PMF `&class::sig` / `&class::slot` 语法）、`orphan_slot_stub`（给已声明但从未被 connect 的 slot 追加空实现，带 `qWarning` 暴露缺失的连接）。默认 `apply=False` 显示 diff；`apply=True` 写回，可选 `.bak`。

### 改进

- **LLM 基础设施 helper** —— 共享 `_llm_check_config()` + `_llm_call()`（基于 urllib，无额外依赖）。`_llm_call` 返回 dict `{ok, text, error}` 而非抛异常；工具检查 `ok` 并把 `Error:` 字符串返给用户。`_json_footer` 段包含使用的 provider + model。

### Bug 修复

- **`qt_documentation_auto_fill`** —— 初版在测试 `finally` 块用 `del server._llm_call` 还原 mock，永久删掉 server 模块的真实 `_llm_call` 函数，让后续所有测试都坏。改成 `patch_llm_call()` helper，保存原函数引用并在清理时还原。`qt_translation_auto_fill` 测试同模式。
- **`qt_signal_lint_fix`** —— `re.subn()` 的 `n` 是**匹配数**而非**替换数**。当 regex 匹配但 callback 返回原文本（无可用 fix）时，`n` 仍 > 0，误报 fix。改成在追加 `file_fixes` 前先比 `new_modified != modified`。`unique_connection` 和 `functor_to_pointer` 同修。
- **`qt_signal_lint_fix`** —— `unique_connection` 正则 `r"(connect\s*\([^;]+?),\s*(Qt::AutoConnection|Qt::DirectConnection|Qt::QueuedConnection|)\s*\)"` 错匹配 4 参数 `connect(...)` 调用（那里类型未指定，默认 `Qt::AutoConnection`）。改成 OR 加 `Qt::UniqueConnection` 之前要求显式类型参数 —— 给 4 参数 connect 加这个会静默把语义从"默认类型"改成"默认类型 | unique"。
- **`qt_signal_lint_fix`** —— `queued_connection` 正则 `r"connect\s*\(\s*(\w+)\s*,\s*SIGNAL\s*\([^)]+\)\s*,..."` 无法匹配 `SIGNAL(progressUpdated())` 因为 `[^)]+` 跨不过 `progressUpdated()` 里的内层 `)`。改成 `.*?`（非贪心任意字符）以处理 Qt signal/slot 名带自己括号的情况。

### 已验证

- 22 个 e2e 套件过：6 light + 273 full = **279 个 pytest 测试**（`pytest -m light` < 5s，`pytest -m full` ~60s）。
- **85 / 85 工具**有 e2e 覆盖（82 v0.3.0 + 3 v0.3.1）。
- 85 / 85 工具有完整 Args / Returns / Raises docstring。
- 85 / 85 工具用 `_json_footer` 输出机器可读段（默认关）。
- 所有 e2e 测试通过直接 import `server` 绕过 MCP stdio 缓存 —— 通过 `pytest -m full` 验证。
- server.py 从 14110 → **14806 行**（+696，+4.9%）；3 个新工具平均 ~230 行每个（Pydantic Input + 实现 + docstring + JSON 段）。测试从 254 → 279（+25；+9.8%）。

## [0.3.0] — 2026-07-09

### 新增

- **`qt_build_cache`** — 检测 PATH 上的 ccache / sccache，从缓存目录读 hit/miss 统计，（可选）注入 `QMAKE_CXX = ccache g++`（或 sccache 等价物）到项目 `.pro` 顶部，让后续每次 `qt_build` 调编译都走缓存。还写带 `CCACHE_DIR` / `SCCACHE_DIR` 提示的旁挂 `.qt_ccache_env`。`report_only=True` 跳过 patch。典型用途：在 200-400 文件的棋牌项目上把增量重编译时间从 30-60 s 砍到 2-6 s（5-10× 加速）。
- **`qt_steamworks_init`** — 为 Qt 项目生成即插即用 Steamworks SDK 集成：`steamworks_integration.h/.cpp` 包 `SteamAPI_Init` / `SteamAPI_Shutdown` / `SteamAPI_RunCallbacks`，带 10 Hz `QTimer` 和 `steamCallbacksDispatched` 信号；`steam_achievements.h/.cpp` 带 `grant(apiName)` / `isUnlocked(apiName)` / `storeStats()`，调 `SteamUserStats()->SetAchievement`；`steam_appid.txt` 放 .pro 旁边让 dev 模式不用通过 Steam client 启动也能工作；`STEAMWORKS.md` 带分步 checklist（下载 SDK、把头加到 .pro、调 `init()`、在合作方网站配成就）。`sdk_path` 选项输出 `LIBS += -L... -lsteam_api` 片段。
- **`qt_itch_butler`** — 为 Qt 游戏在 itch.io 上分发生成 `.itch.toml`（`butler push` 的 channel manifest）和每 channel 的 push 脚本（`push_windows.bat`、`push_macos.sh`、`push_linux.sh`、`push_html5.bat`、`push_android.bat`）。还写 `BUTLER_README.md`，含首次设置（装 butler、`butler login`、在 itch.io 仪表板建项目页）。`dry_run=True`（默认）回显 push 命令而不真调 butler，所以在没有 butler 二进制在 PATH 的全新项目上跑也安全。
- **`qt_documentation_lint`** — 对 `.h` / `.cpp` / `.qml` 做 doxygen 注释完整性的静态分析。对找到的每个 public 函数，检查：前一个 doxygen 块、`@brief` 摘要（或第一条 `///` 行）至少 `min_brief_chars` 字符、每个声明参数的 `@param` 标签、非 void 返回值的 `@return` 标签。报告逐文件覆盖率。支持 `text`（人类可读）或 `json`（机器可读）输出。`fail_threshold=0.99` 让它 CI 友好 —— 覆盖率降到 threshold 以下时工具返回 `Error:`。配 `qt_docs_gen`（**生成** Doxyfile + 跑 doxygen）；`qt_documentation_lint` 检查源码**本身**已文档化。

### 改进

- **`qt_cheatsheet` 目录** —— 需要更新加 4 个 v0.3.0 工具（推迟到下个 minor；同 v0.2.7 / v0.2.9 补录模式）。

### 已验证

- 20 个 e2e 套件过：6 light + 254 full = **254 个 pytest 测试**（`pytest -m light` < 5s，`pytest -m full` ~62s）。
- **82 / 82 工具**有 e2e 覆盖（78 v0.2.9 + 4 v0.3.0）。
- 82 / 82 工具有完整 Args / Returns / Raises docstring。
- 82 / 82 工具用 `_json_footer` 输出机器可读段（默认关）。
- 所有 e2e 测试通过直接 import `server` 绕过 MCP stdio 缓存 —— 通过 `pytest -m full` 验证。
- server.py 从 13273 → **14110 行**（+837，+6.3%）；4 个新工具平均 ~210 行每个。测试从 233 → 254（+21）。

## [0.2.9] — 2026-07-09

### 新增

- **`qt_env_diff`** — 并排比较两个 Qt SDK 安装。报告 `qmake -v` 版本、模块数（从 `<root>/include/Qt*` 目录）、lib 文件数（`.a` / `.dll` / `.lib`），列出仅在 A 或仅在 B 存在的模块。经典的 MinGW32 vs MinGW64 不匹配诊断。
- **`qt_dll_search_path`** — 分析 Qt 可执行文件的 DLL 搜索路径。用 `objdump -p` 提完整 DLL import 列表，然后按标准 Windows 搜索顺序（`.exe` 目录 → 用户提供的目录 → `QT_BIN_DIR` → `QT_32_BIN_DIR` → `PATH`）遍历，报告哪些 DLL 在、哪些缺失。配 `qt_run` 启动失败诊断 —— exe 启动后 0.4 秒崩了，90% 是缺或错 bitness 的 `Qt5Core.dll`。
- **`qt_audio_convert`** — ffmpeg 包装做批量音频转换。支持 `mp3` / `opus` / `wav` / `ogg` / `flac` / `m4a` / `aac` 输出，可配比特率（无损忽略）。典型用途：为棋牌游戏准备翻牌 / 洗牌 / 筹码落桌音效。ffmpeg 路径可通过 `QT_MCP_FFMPEG` 覆盖（默认 `E:\Download_tools\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe`）。
- **`qt_qss_inspect`** — 解析 Qt Style Sheet（`.qss`）并报告其结构：选择器数、属性数、重复选择器（如两个 `QPushButton { ... }` 块）、选择器内重复属性、`!important` 用法、唯一颜色值、字号。审计 `qt_theme_gen` 生成的或手写的、已经长得不可读的 stylesheet 时有用。
- **`qt_svg_to_png`** — 把 `.svg` 文件转成多宽度 `.png`。先试 cairosvg，然后 ImageMagick（`magick` / `convert`）。报告用了哪个后端。典型用途：把矢量源准备成 Qt 能打包进 `.qrc` 资源的 PNG。
- **`qt_qml_property_linter`** — QML 文件 property 问题静态分析。检测：未用的 `property` 声明、id 遮蔽（同一文件里两次定义同一 id）、类型不匹配（字符串字面量赋给数值属性）。配 `qt_qml_lint`（用 qmllint 查语法）—— 抓 qmllint 在类型未声明或 id 重用时漏掉的 property 级问题。
- **`qt_accessibility_check`** — 扫 Qt C++ 源文件的 a11y 问题。检测：`Q_OBJECT` 类缺 `Q_DISABLE_COPY`；交互 widget（`QPushButton`、`QLabel`、`QLineEdit` 等）缺 `setAccessibleName`；widget 缺 `setObjectName`；统计 `setTabOrder` / `setAccessibleDescription` 用法。发布前屏幕阅读器和键盘导航 QA 时有用。
- **`qt_pro_project_graph`** — 遍历 `.pro` 的 `SOURCES` / `HEADERS` / `FORMS` / `RESOURCES` 列表，扫每个文件的 `#include "..."` 指令，输出 Graphviz DOT 依赖图。按文件类型着色聚类（源码 = 蓝、头 = 绿、表单 = 橙、资源 = 粉）。通过 DFS 检测 include 环。可选 `output_dot` 写到文件，再 `dot -Tpng foo.dot -o foo.png`。

### 改进

- **`qt_cheatsheet` 目录补录** —— 需要更新加 8 个 v0.2.9 工具（推迟到下个 minor；同 v0.2.7 补录模式）。

### Bug 修复

- **`qt_pro_project_graph`** —— 初版对 `_pro_parse` 输出用 `e.get("values", [])`，但 `_pro_parse` 返回单 `value` 字符串（不是 `values` 列表），节点总是空。改成 `e.get("value", "").split()` 正确 tokenize。被 e2e_v14 test #22 抓出（"includes main.cpp"），否则图会静默空着发布出去。

### 已验证

- 19 个 e2e 套件过：6 light + 25 个新 v14 full + 208 个前版 full = **233 个 pytest 测试**（`pytest -m light` < 5s，`pytest -m full` ~58s）。
- **78 / 78 工具**有 e2e 覆盖（70 v0.2.8 + 8 v0.2.9）。
- 78 / 78 工具有完整 Args / Returns / Raises docstring（通过 `grep -A 50 "@mcp.tool(name=..." server.py` 审计）。
- 78 / 78 工具用 `_json_footer` 输出机器可读段（默认关）。
- 所有 e2e 测试通过直接 import `server` 绕过 MCP stdio 缓存 —— 通过 `pytest -m full` 验证。
- server.py 从 12147 → **13273 行**（+1126，+9.3%）；8 个新工具平均 ~140 行每个。

## [0.2.8] — 2026-07-09

### 新增

- **`qt_git_init`** — 为 Qt 项目初始化 git 仓库。生成 Qt 专属 `.gitignore`（build 产物、moc\_\*、ui\_\*、\*.user、.tmp/、v0.2.8 的 .qt_mcp 缓存），可选 README.md（从 .pro 文件名推断），然后跑 `git init` + `git add .` + `git commit`。可选 `git_user_name` / `git_user_email` 设本地仓库配置。返回初始 commit SHA。
- **`qt_installer_gen`** — 生成 Windows installer 脚本（NSIS `.nsi` 或 Inno Setup `.iss`）+ `build_installer.bat`，跑 `windeployqt` 然后编译器（makensis 或 iscc）。传 `app_name`、`app_version`、`vendor`、可选 `license_file`（作为注释嵌入）和 `qml_dir`（通过 `--qmldir` 传）。**不**自己调 makensis / iscc —— 用户装好 NSIS / Inno Setup 后跑这个 batch。
- **`qt_qml_component_gen`** — 为棋牌 UI 生成可复用 QML 组件。6 个模板：`card`（单张牌带花色/点数）、`board`（可点击 tile 网格）、`player`（名字/分数/激活 widget）、`hand`（重叠的牌行）、`deck`（带计数的抽牌/弃牌堆）、`tile`（麻将/多米诺/Scrabble 的 tile）。每个输出自洽 `.qml` + 顶层 `qmldir` 用于模块导入。支持 `dark` / `light` 主题。
- **`qt_db_seed`** — 从 schema 定义创建 SQLite 数据库，可选插入 seed 行，并生成 `<db_name>_examples.py` 带 CRUD helpers（`select_all_*`、`insert_*`、`delete_*`）。棋牌玩家 / 排行榜 / 走子历史持久化作为 `qt_state` / `qt_save` 的替代。Schema 定义为 `tables=[{name, columns:[{name, type, pk, not_null, default}]}]`。
- **`qt_high_dpi_test`** — 在多个 `QT_SCALE_FACTOR` 值（默认 `[1.0, 1.5, 2.0]`）下启动 `.exe`，对每个通过 pywinauto（pyautogui 兜底）截窗口图，可选地与 baseline 截图做像素 diff。对棋牌 UI 跨 DPI 缩放正确渲染至关重要。
- **`qt_property_browser`** — 从 Qt 头文件抽所有 `Q_PROPERTY` 声明并以 markdown / html / json 表形式渲染。每个 property 列其 type、READ、WRITE、NOTIFY、MEMBER、CONSTANT 子句。API 文档、演示、meta-object 审计时有用。

### 改进

- **`qt_cmake` 排除列表** —— 确认 `.tmp` 已去掉（v0.2.5 修复时已处理；无回归）。
- 6 个新工具都用 `_json_footer`（默认关）输出机器可读内容。

### 已验证

- 18 个 e2e 套件过：6 light + 25 个新 v13 full + 177 个前版 full = 208 个 pytest 测试（`pytest -m light` < 5s，`pytest -m full` ~50s）。
- 70 / 70 工具有 e2e 覆盖（64 v0.2.7 + 6 v0.2.8）。
- 70 / 70 工具有完整 Args / Returns / Raises docstring。
- 70 / 70 工具用 `_json_footer` 输出机器可读段（默认关）。
- 所有 e2e 测试通过直接 import `server` 绕过 MCP stdio 缓存 —— 通过 `pytest -m full` 验证。

## [0.2.7] — 2026-07

### 新增

- **`qt_model_gen`** — 为棋牌数据（牌、玩家、分数）生成 `QAbstractListModel` 或 `QAbstractTableModel` 子类。list 模型：可配 `item_type` + `addItem` / `removeAt` / `clear` slot。table 模型：`columns`（`{name, type}` 字典列表）+ `appendRow` / `clear`。输出：可直接用的 `.h` / `.cpp` 带 `rowCount` / `data` / `roleNames`（QML-ready） / `headerData`（仅 table）。
- **`qt_theme_gen`** — 为 Qt Widgets 应用生成 QSS（Qt Style Sheet）。传 `mode`（'light' / 'dark'）、`base_color`、`accent_color`、`text_color`、`border_radius`；输出完整样式的 `.qss`，覆盖 QWidget / QMainWindow / QMenuBar / QMenu / QPushButton（含 hover/pressed/disabled/default 状态） / QLineEdit / QLabel / QListWidget / QTreeWidget / QTableWidget / QHeaderView / QProgressBar / QSlider / QCheckBox / QRadioButton / QStatusBar / QToolTip / QScrollBar。
- **`qt_ico_create`** — 把一个或多个 PNG 打包成多分辨率 Windows `.ico`（16、32、48、64、128、256 默认尺寸）。Windows 高 DPI app icon 必需。用 Pillow。
- **`qt_screenshot_diff`** — 像素级图像 diff 做视觉回归测试。传两张图和 tolerance（每通道 0-255）；返回 diff 数、比例、bbox。可选 `diff_image` 写一个红覆盖可视化差异。用 Pillow + numpy。
- **`qt_clazy_check`** — 基于 regex 的 Qt anti-pattern 检查（不需要 clazy 二进制）。检测：`.cpp` 里出现 Q_OBJECT（应该在 .h）；新 QObject 没显式 parent；QObject 子类缺 `Q_DISABLE_COPY`；QVector（Qt 4 专用，Qt 5+ 用 QList）；老式 `SIGNAL()` / `SLOT()` connect；QObject 子类缺 Q_OBJECT；隐式 `char*` 到 QString 强转。返回每 check 计数和前 20 个问题。
- **`qt_signal_slot_trace`** — 信号 / 槽连线的静态分析。解析 `.h` 的 `signals:` / `slots:` 声明和 QObject 子类，解析 `.cpp` 的 `QObject::connect` / `connect` / 老式 `SIGNAL` / `SLOT` 调用。输出格式：'text'（默认）、'json'（机器可读）、'dot'（Graphviz）。报告连接、孤立 signal、孤立 slot。可选 `output_file` 写结果到磁盘。
- **`qt_input_recorder`** — 录制 / 回放鼠标 + 键盘事件做 demo、回归测试、bug 报告。用 `pyautogui` + `pynput`。输出：可移植 JSON 带 `events` 数组。Action：'record'（录 N 秒）、'playback`（按指定速度回放文件）、'info'（按类型显示事件计数）。Helpers 在 `<SANDBOX>/.tmp/input_recorder_helpers/`。
- **`qt_translation_validate`** — 解析 Qt `.ts` 文件并报告每语言翻译覆盖率。按 `<TS language="...">` 块数 `total` / `finished` / `unfinished` / `empty` / `obsolete`。可选 `min_coverage` flag 警告低覆盖率语言。i18n QA 时有用。

### 改进

- **`qt_cheatsheet` 目录补录** —— 加了 14 个之前在 cheatsheet 目录里漏掉的工具（qt_lint、qt_analyze、qt_input、qt_cmake、qt_docs_gen、qt_achievement、qt_undo、qt_leaderboard_ui、qt_pkg_install、qt_release_notes、qt_copyright、qt_score、qt_timer、qt_replay）加 8 个 v0.2.7 工具。目录现在反映全部 64 个工具。
- Bug 修复：`qt_signal_slot_trace` 双重计数 `QObject::connect(...)` 行（被通用 `connect(...)` pattern 和 `QObject::connect(...)` pattern 都匹配）。合成一个可选前缀正则。

### 已验证

- 全部 17 个 e2e 套件过：6 light + 177 full = 183 个 pytest 测试（`pytest -m light` < 5s，`pytest -m full` ~45s）。
- 64 / 64 工具有 e2e 覆盖。
- 64 / 64 工具有完整 Args / Returns / Raises docstring。
- 64 / 64 工具用 `_json_footer` 输出机器可读段（默认关）。

## [0.2.0] — 2026-07

### 新增

- **`qt_validate`** — 遍历 `.pro`，校验每个 `SOURCES` / `HEADERS` / `FORMS` / `RESOURCES` / `TRANSLATIONS` 引用存在且可读。可选 `strict=True` 也跑 XML 解析 `.ui` / `.qrc` 并检测重复条目。
- **`qt_run_trace`** — 用 `QT_LOGGING_RULES` + `QT_LOGGING_TO_CONSOLE=1` 启动 `.exe` 并捕获 stdout/stderr。用来 debug signal/slot 派发（`qt.core.signal*=true`）、QML 加载、插件加载。
- **`qt_smoke_test`** — 端到端健康检查：clean → build（通过 `qt_build`）→ 后台启动 N 秒 → kill。仅当三步都成功才返回 PASS。
- **`qt_diff`** — 比较两个 `.pro` 项目。报告有差异的变量（SOURCES、HEADERS、FORMS、RESOURCES、TRANSLATIONS、DEFINES、INCLUDEPATH、LIBS），仅在 A 或仅在 B 的源文件，以及共文件中 SHA1 不匹配的。`show_identical=True` 也列出 SHA1 匹配的文件。
- **`qt_pkg`** — 列出 / 检查已装 Qt 5 模块。遍历 `QT_ROOT/include/Qt*` + `lib/cmake/Qt5*`，报告单模块的 headers/libs/version，默认模式下列出全部 76+ 模块，枚举 `QT_ROOT/plugins/` 下的插件。
- **`qt_log`** — 过滤 / 分析 Qt log 文件。按级别（debug / warning / critical / fatal / info）数行数，提取 `qt.*` 类别计数，支持 `category_filter` 和 `level_filter` 子串匹配，通过 `max_lines` 截断。
- **`qt_state`** — QSettings 包装做持久化 app 状态。按 organization / application 的 `save` / `load` / `delete` / `list` / `clear` action。写到 OS-native QSettings 位置（Windows APPDATA，Linux `~/.config`）。棋牌存档/读档、设置持久化、回放数据时有用。
- **`qt_assets`** — 扫 asset 文件目录（图片、音频）并输出 `.qrc` + 可选 `qrc_<name>.cpp` 带 `Q_INIT_RESOURCE`。支持递归扫、排除 pattern、自定义扩展名、.qrc 输出中按子目录分组。
- **`qt_watch`** — 文件变更自动重编译。用 `watchdog` 库订阅文件系统事件，对快速变更 debounce（默认 1.5s），每批调 `qt_build`。返回 watcher 进程的 PID；用 `qt_kill_exe` 停。
- **`qt_signature`** — 通过 signtool.exe 签 / 验 Windows 可执行文件。Action：'info'（找 signtool）、'sign'（应用 Authenticode + RFC 3161 timestamp）、'verify'（查已有签名）、'timestamp'（对已签文件再加 timestamp）。在 `C:\Program Files\Windows Kits\10\bin\*\x64\` 下自动发现 signtool.exe。
- **`qt_save`** — 棋牌可移植性的 JSON 存档文件 save / load / list / delete / inspect。不同于 `qt_state`（QSettings 原生格式）：`qt_save` 写纯 JSON，便于 `cat save.json | jq` 检查和跨机器同步。
- **`qt_audio`** — 音效文件 list / probe / play。报告 QtMultimedia 可用性、扫音频目录、从文件头识别格式、输出可拖到游戏里的 QSoundEffect / QMediaPlayer C++ 片段。
- **`qt_anim`** — 生成 QPropertyAnimation 代码（fade / move / scale / rotate / color / sequence）。输出 ready-to-paste 的 C++ 片段，带 start / end 值、duration、easing curve、可选 loop。
- **`qt_network`** — 为 Qt 网络类生成 `.h` / `.cpp` 对（QTcpSocket client / QTcpServer / QUdpSocket peer / QWebSocket client）。配 host、port 和类名；输出到 `output_dir` 即可加进 .pro。
- **`qt_coverage`** — 通过 gcov + lcov 收集代码覆盖率。把 `--coverage` flag 注入 .pro，构建，（可选）跑测试，然后跑 `lcov --capture` + `genhtml`。退出时还原 .pro。生成 `<output>/html/index.html` 的 HTML 报告。
- **`qt_cheatsheet`** — 打印所有 qt-mcp 工具的分类速查（env / scaffold / build / run / validate / creator / analysis）。传 `tool_name` 拿单个工具的详细帮助，或 `category` 过滤。
- **`qt_score`** — 棋牌玩家分数追踪和排行。add / list / leaderboard（top-N 排行）/ reset / import / export。后端 `<SANDBOX>/.scores/scores.json`。
- **`qt_timer`** — 启 / 停 / 暂停 / 恢复命名 timer（游戏时钟、回合 timer、总游戏时长）。状态持久到 `<SANDBOX>/.timers/timers.json`。有时间限制的回合制游戏时有用。
- **`qt_replay`** — 棋牌走子回放系统。record / save / load / list / play / delete。每步带 `n` / `type` / `data` / `ts`。后端是 `<SANDBOX>/.replays/` 下的每会话 JSON。
- **`qt_lint`** — 统一 lint 包装。在项目上跑 cpplint + qmllint + clang-tidy。返回 `LINT PASS` / `LINT FAIL` 带每 linter 摘要。
- **`qt_analyze`** — clang-tidy 深度分析，支持自定义 check 选择（如 `bugprone-*,performance-*`）。支持 `text` / `json` 输出。
- **`qt_input`** — 生成键盘 / 鼠标 / 手柄输入处理代码。'keyboard' 输出 QShortcut + QKeySequence + slot 声明。'mouse' 输出 mousePressEvent / mouseMoveEvent / mouseReleaseEvent override。'gamepad' 输出 QGamepad 包装（带 Qt6 SDL2 fallback 注）。'focus' 输出 tab order / focus chain。'mapping' 写 JSON bindings 文件。
- **`qt_cmake`** — 为 Qt 项目生成 CMakeLists.txt。支持 find_package(Qt5) 或 find_package(Qt6)、AUTOMOC / AUTORCC / AUTOUIC、C++17、`app` / `library` / `console` 模板。从 qmake 迁到 CMake。
- **`qt_docs_gen`** — 为 Qt 项目生成 Doxyfile，（可选）跑 doxygen 生成 HTML 文档。默认 EXTRACT_ALL、源码浏览器、调用图。让 API 文档与代码同步。
- **`qt_achievement`** — 管理游戏成就 / 徽章。'define'（加一个成就到目录）、'grant'（标记已获得）、'list'（显示玩家所有成就当前进度）、'progress'（更新多步成就当前计数）、'reset'（清玩家已获）、'catalog'（显示所有定义）。
- **`qt_undo`** — 按项目 push / undo / redo 游戏状态快照。栈持久到 JSON，max depth 可配。返回 JSON 段里状态供程序用。
- **`qt_leaderboard_ui`** — 生成排行榜 widget（.h + .cpp + .ui 三件套）。两种风格：'table'（QTableView 带 sort/filter）和 'cards'（QListView 带 card delegate）。读自 `<SANDBOX>/.scores/scores.json`（由 qt_score 生成）。
- **`qt_pkg_install`** — `aqt`（https://github.com/miurahr/aqtinstall）包装装 / 列 / 卸 Qt SDK。支持 Qt 5.14.2 / 6.x 在 windows / linux / mac。
- **`qt_release_notes`** — 从 `git log` 自动生成 CHANGELOG.md 段（conventional-commits 前缀识别）或在 Unreleased 下手动加 bullets。
- **`qt_copyright`** — 给项目里每个源文件 prepend license header（默认 MIT）。跳过已有 SPDX marker 的文件，支持 dry_run。
- **共 56 个工具**（v0.1.0 时 26）。所有 56 个有完整 Args / Returns / Raises docstring。所有 56 个由 e2e 测试覆盖。
- **`__version__ = "0.2.0"`** 在模块上。
- **`def main() -> int`** 入口。`python -m server` 和 `qt-mcp` 控制台脚本都能用。
- **`_json_footer(obj)`** helper + `QT_MCP_JSON=1` 环境变量开关：设了之后，每个工具追加 `--- json ---\n{ok,data|error}` 段。应用到**全部 34 个工具**（141 处返回字符串被包了，单行 + 多行都有）；保留 e2e 字符串契约因为 helper 默认返回 `""`。默认关。
- **环境变量可覆盖路径**：`QT_MCP_QT_ROOT`、`QT_MCP_QT_32_ROOT`、`QT_MCP_MINGW_BIN`、`QT_MCP_QTCREATOR`、`QT_MCP_SANDBOX`、`QT_MCP_QT_VERSION`。默认值保留原 Windows 布局。
- **`pytest.ini`** —— 发现 `tests/light/` 和 `tests/full/` 下每个 `e2e_*.py` 作为 pytest 测试模块。按目录自动 mark 测试：light = 不需要 Qt SDK，full = 需要 Qt SDK。CI 跑 `pytest -m light` 做快速 PR gate。e2e 脚本不需要 pytest（每个调 `sys.exit(0 | 1)`）。
- **`pyproject.toml`** —— 可通过 `pip install .` 装，暴露 `qt-mcp` 控制台脚本。
- **`.github/workflows/ci.yml`** —— Windows-latest CI 跑 `pytest -v` 对轻量测试子集。重 Qt-SDK 测试被 CI 排除（需要完整 5 GB Qt 安装）。
- **`.github/ISSUE_TEMPLATE/`**（bug + feature）和 **`PULL_REQUEST_TEMPLATE.md`**。
- **`tests/light/` + `tests/full/`** —— e2e 脚本拆成"无 Qt SDK"（解析器、helpers、沙箱拒绝）和"需要 Qt SDK"（build/run）两层。Conftest.py 按目录自动 mark。
- **`examples/minimal/`** —— 最小可运行示例（console_app 模板 + 指向它的 `.mcp.json`）。
- **`docs_data/README.md`** —— 解释怎么重建 53 MB FTS5 docs 索引。

### 变更

- **`qt_clean`** 现在 delegate 给新的 `_clean_artifacts(proj)` helper，让 `qt_smoke_test` 能复用清理逻辑。
- **`qt_test`** 现在用新的 `_pe_bits(exe)` helper 选 32-bit vs 64-bit Qt bin 目录。该 helper 也被 `qt_run_trace` 和 `qt_smoke_test` 用 —— PE-header 启发式的单一真相源。
- **README.md** 重写：29 工具表、badge、扩展的环境变量表、程序化输出（JSON 段）段、Development 段。

### 修复

- e2e `e2e_new_tools_v3.py` 硬编码 `len(tools) == 23`；放宽到 `>= 23`，加 v4 / v5 工具时不再破坏测试。

## [0.1.0] — 2026-07 (初始)

- 26 个 MCP 工具覆盖完整 Qt C++ 生命周期。
- 9 个脚手架模板（widget / mainwindow / dialog / qml_app / console_app / cards_game / chess_game / generic_game / game_framework）。
- 8 个 e2e 测试套件，全过。
- 本地 FTS5 docs 索引（`docs_data/qt_5_14_2_docs.db`，53 MB，gitignored）。
- AI 友好的结构化 build 诊断，带一行修复建议。
- UI automation（`qt_ui_action`）和 Qt Creator 驱动（`qt_creator_open` / `qt_creator_run`）。