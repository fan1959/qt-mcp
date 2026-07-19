"""e2e for v27 new tools (v0.3.9):

NEW TOOLS:
  - qt_concurrency_lint  (8 rules: QtConcurrent / QThread / QFuture / QRunnable / QSemaphore / QMutex)

Run: python e2e_new_tools_v27.py
"""

import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import server
from server import SANDBOX_TMP, QtConcurrencyLintInput

PASS = "[OK]"
FAIL = "[FAIL]"
results = []


def check(name: str, cond: bool, hint: str = "") -> bool:
    tag = PASS if cond else FAIL
    line = f"  {tag} {name}"
    if hint and not cond:
        line += f"  ({hint})"
    print(line)
    results.append((name, cond))
    return cond


def fresh_dir(parent: Path, name: str) -> Path:
    p = parent / name
    if p.exists():
        try:
            subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(p)],
                           check=False, capture_output=True, timeout=10)
        except Exception:
            pass
        shutil.rmtree(p, ignore_errors=True)
    p.mkdir(parents=True, exist_ok=True)
    return p


BAD_CPP = '''\
#include <QtConcurrent/QtConcurrent>
#include <QThreadPool>
#include <QFutureWatcher>
#include <QRunnable>
#include <QThread>
#include <QMutex>
#include <QMutexLocker>
#include <QSemaphore>

void onRunInGui() {
    auto results = QtConcurrent::blockingMapped(QList<int>(), [](int x){ return x; });
    QThreadPool::globalInstance()->start(new SomeTask());
}

class MyWatcher {
public:
    QFutureWatcher watcher;
};

class MyTask : public QRunnable {
public:
    void run() override { /* no autoDelete setup */ }
};

class WorkerThread : public QThread {
    void run(QString x) {
        while (true) { sleep(1); }
    }
};

class GoodSlot : public QObject {
public slots:
    void onPress() {
        QMutexLocker lock(&m_mutex);
    }
private:
    QMutex m_mutex;
};

void initBad() {
    QSemaphore sem(500);
}
'''

GOOD_CPP = '''\
class WorkerThread : public QThread {
    void run(QString x) {
        exec();
    }
};

void safeRun() {
    QtConcurrent::run([](){ return 42; });
}
'''


async def test_concurrency_lint_bad():
    print("\n[1] qt_concurrency_lint -- bad file catches 7 rules")
    work = fresh_dir(SANDBOX_TMP, "v27_concurrency_bad")
    (work / "bad.cpp").write_text(BAD_CPP, encoding="utf-8")
    res = await server.qt_concurrency_lint(QtConcurrencyLintInput(
        project_dir=str(work),
        min_severity="info",
        output_format="text",
    ))
    print(res[:1000])
    check("returns success", not res.startswith("Error:"))
    check("verdict FAIL (warnings present)", "verdict       : FAIL" in res)
    check("qtconcurrent_blocking_main_thread", "qtconcurrent_blocking_main_thread" in res)
    check("qthreadpool_no_wait", "qthreadpool_no_wait" in res)
    check("qfuture_watcher_missing_setfuture", "qfuture_watcher_missing_setfuture" in res)
    check("qrunnable_no_autodelete", "qrunnable_no_autodelete" in res)
    check("qthread_subclass_no_quit", "qthread_subclass_no_quit" in res)
    check("qmutex_lock_in_event_loop", "qmutex_lock_in_event_loop" in res)
    check("qsemaphore_init_too_large", "qsemaphore_init_too_large" in res)


async def test_concurrency_lint_clean():
    print("\n[2] qt_concurrency_lint -- clean file (no warnings)")
    work = fresh_dir(SANDBOX_TMP, "v27_concurrency_good")
    (work / "good.cpp").write_text(GOOD_CPP, encoding="utf-8")
    res = await server.qt_concurrency_lint(QtConcurrencyLintInput(
        project_dir=str(work),
        min_severity="warning",
        output_format="text",
    ))
    print(res[:400])
    check("verdict PASS on clean", "verdict       : PASS" in res)
    check("zero findings", "findings      : 0" in res)


async def test_concurrency_lint_json_format():
    print("\n[3] qt_concurrency_lint -- JSON output format")
    work = fresh_dir(SANDBOX_TMP, "v27_concurrency_json")
    (work / "bad.cpp").write_text(BAD_CPP, encoding="utf-8")
    res = await server.qt_concurrency_lint(QtConcurrencyLintInput(
        project_dir=str(work),
        output_format="json",
    ))
    j = json.loads(res)
    check("json verdict = FAIL", j["verdict"] == "FAIL")
    check("json findings > 0", len(j["findings"]) >= 6)
    check("json by_rule present", "by_rule" in j)
    check("json files_scanned > 0", j["files_scanned"] >= 1)


async def test_concurrency_lint_warning_only():
    print("\n[4] qt_concurrency_lint -- min_severity=warning filter")
    work = fresh_dir(SANDBOX_TMP, "v27_concurrency_warn")
    (work / "bad.cpp").write_text(BAD_CPP, encoding="utf-8")
    res = await server.qt_concurrency_lint(QtConcurrencyLintInput(
        project_dir=str(work),
        min_severity="warning",
        output_format="json",
    ))
    j = json.loads(res)
    all_warn = all(f["severity"] == "warning" for f in j["findings"])
    check("warning-only filter excludes info", all_warn)
    check("warning count > 0", len(j["findings"]) > 0)


async def test_concurrency_lint_skip_directives():
    print("\n[5] qt_concurrency_lint -- skipped #include directives (no false positives from headers)")
    work = fresh_dir(SANDBOX_TMP, "v27_concurrency_skipinc")
    # Headers-only cpp with no body — should yield 0 findings
    only_includes = '''\
#include <QMutexLocker>
#include <QSemaphore>
#include <QRunnable>
#include <QThread>
'''
    (work / "headers_only.cpp").write_text(only_includes, encoding="utf-8")
    res = await server.qt_concurrency_lint(QtConcurrencyLintInput(
        project_dir=str(work),
        output_format="json",
    ))
    j = json.loads(res)
    check("no false positives from #include lines", len(j["findings"]) == 0)


async def test_concurrency_lint_missing_dir():
    print("\n[6] qt_concurrency_lint -- missing project_dir returns error")
    res = await server.qt_concurrency_lint(QtConcurrencyLintInput(
        project_dir=str(SANDBOX_TMP / "v27_does_not_exist_dir"),
        output_format="text",
    ))
    print(res[:200])
    check("returns error for missing dir", res.startswith("Error:") or "does not exist" in res)


async def main():
    await test_concurrency_lint_bad()
    await test_concurrency_lint_clean()
    await test_concurrency_lint_json_format()
    await test_concurrency_lint_warning_only()
    await test_concurrency_lint_skip_directives()
    await test_concurrency_lint_missing_dir()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\n=== Summary ===  passed {passed} / {total}")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
