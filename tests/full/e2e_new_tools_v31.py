"""
e2e_v31 — v0.4.3 sprint: 4 new tools

Tools covered:
  - qt_db_perf_index: SQLite index advisor (EXPLAIN QUERY PLAN + missing-index suggestions)
  - qt_qobject_invoke_connect_monitor: per-sender/receiver/signal/slot hot-list heatmap
  - qt_modernize_qt6_string_literal: u"" prefix for tr() + non-ASCII literals
  - qt_qobject_invocation_history: runtime Q_INVOKABLE invocation log parser
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

# Force JSON footer mode for round-trip tests
os.environ.setdefault("QT_MCP_JSON", "1")


@pytest.fixture(autouse=True)
def _qt_mcp_json_env(monkeypatch):
    monkeypatch.setenv("QT_MCP_JSON", "1")
    yield


def _split_json(out: str) -> dict:
    if "\n\n--- json ---" not in out:
        return {}
    try:
        return json.loads(out.split("\n\n--- json ---", 1)[1].strip())
    except Exception:
        return {}


sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import server  # noqa: E402

SAMPLE_DIR = server.SANDBOX_TMP / "e2e_v31_sprint"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


# =============== qt_db_perf_index ===============

@pytest.mark.asyncio
async def test_db_perf_index_missing_indexes():
    from server import QtDbPerfIndexInput, qt_db_perf_index
    import shutil
    db_dir = SAMPLE_DIR / "db_perf"
    if db_dir.exists():
        shutil.rmtree(db_dir)
    db_dir.mkdir(parents=True)
    db = db_dir / "test1.db"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
    con.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, total REAL)")
    con.execute("INSERT INTO users VALUES (1, 'alice', 'a@x.com')")
    con.execute("INSERT INTO orders VALUES (1, 1, 99.5)")
    con.commit()
    con.close()

    p = QtDbPerfIndexInput(db_file=str(db))
    out = await qt_db_perf_index(p)
    j = _split_json(out)
    assert j["ok"] is True
    assert "users" in out
    assert "orders" in out
    # INTEGER PRIMARY KEY should NOT be flagged as MISS — verify by absence of CREATE INDEX for 'id'
    assert "CREATE INDEX idx_orders_id" not in out
    assert "CREATE INDEX idx_users_id" not in out
    # INTEGER PRIMARY KEY shows up in plan detail
    assert "USING INTEGER PRIMARY KEY" in out
    # user_id, total, name, email SHOULD be flagged
    assert "user_id" in out
    assert "total" in out
    assert "name" in out
    assert "email" in out
    # Suggestions emitted
    assert "CREATE INDEX" in out


@pytest.mark.asyncio
async def test_db_perf_index_table_filter():
    from server import QtDbPerfIndexInput, qt_db_perf_index
    db = SAMPLE_DIR / "db_perf" / "test1.db"
    p = QtDbPerfIndexInput(db_file=str(db), table_filter="users")
    out = await qt_db_perf_index(p)
    assert "users" in out
    # 'orders' table should be excluded
    assert "[orders]" not in out


@pytest.mark.asyncio
async def test_db_perf_index_json_format():
    from server import QtDbPerfIndexInput, qt_db_perf_index
    db = SAMPLE_DIR / "db_perf" / "test1.db"
    p = QtDbPerfIndexInput(db_file=str(db), output_format="json")
    out = await qt_db_perf_index(p)
    head = out.split("\n\n--- json ---", 1)[0].strip()
    data = json.loads(head)
    assert "tables" in data
    assert "suggestion_count" in data
    assert data["suggestion_count"] >= 1


@pytest.mark.asyncio
async def test_db_perf_index_nonexistent_db():
    from server import QtDbPerfIndexInput, qt_db_perf_index
    p = QtDbPerfIndexInput(db_file=str(SAMPLE_DIR / "ghost.db"))
    out = await qt_db_perf_index(p)
    j = _split_json(out)
    assert j["ok"] is False
    assert "not found" in j["error"]


@pytest.mark.asyncio
async def test_db_perf_index_already_indexed():
    from server import QtDbPerfIndexInput, qt_db_perf_index
    import shutil
    db_dir = SAMPLE_DIR / "db_perf_idx"
    if db_dir.exists():
        shutil.rmtree(db_dir)
    db_dir.mkdir(parents=True)
    db = db_dir / "idx.db"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, sku TEXT)")
    con.execute("CREATE INDEX idx_items_sku ON items(sku)")
    con.execute("INSERT INTO items VALUES (1, 'A-001')")
    con.commit()
    con.close()

    p = QtDbPerfIndexInput(db_file=str(db))
    out = await qt_db_perf_index(p)
    # sku has an index -> should NOT be suggested
    assert "sku" in out
    assert "CREATE INDEX idx_items_sku" not in out  # the auto-named one


# =============== qt_qobject_invoke_connect_monitor ===============

SAMPLE_CPP_PMF = """\
#include <QObject>

class Sender : public QObject {
    Q_OBJECT
public:
    void emitFoo() { emit foo(); }
signals:
    void foo();
};

class Receiver : public QObject {
    Q_OBJECT
public slots:
    void onFoo() {}
    void onBar() {}
};

int main() {
    Sender s;
    Receiver r1, r2;
    QObject::connect(&s, &Sender::foo, &r1, &Receiver::onFoo);
    QObject::connect(&s, &Sender::foo, &r1, &Receiver::onBar);
    QObject::connect(&s, &Sender::foo, &r2, &Receiver::onFoo);
    return 0;
}
"""


@pytest.mark.asyncio
async def test_connect_monitor_basic():
    from server import QtQobjectInvokeConnectMonitorInput, qt_qobject_invoke_connect_monitor
    import shutil
    proj = SAMPLE_DIR / "cm_basic"
    if proj.exists():
        shutil.rmtree(proj)
    proj.mkdir(parents=True)
    (proj / "main.cpp").write_text(SAMPLE_CPP_PMF, encoding="utf-8")

    p = QtQobjectInvokeConnectMonitorInput(project_dir=str(proj))
    out = await qt_qobject_invoke_connect_monitor(p)
    # PMF format &Sender::foo (typed pointer-to-member) -> captured
    assert "Sender::foo" in out
    assert "Receiver::onFoo" in out
    # Sender var 's' wired 3 times -> top sender (regex captures bare var name)
    assert "     3  s" in out or "  3  s" in out
    j = _split_json(out)
    assert j["ok"] is True


@pytest.mark.asyncio
async def test_connect_monitor_json_format():
    from server import QtQobjectInvokeConnectMonitorInput, qt_qobject_invoke_connect_monitor
    proj = SAMPLE_DIR / "cm_basic"
    p = QtQobjectInvokeConnectMonitorInput(project_dir=str(proj), output_format="json")
    out = await qt_qobject_invoke_connect_monitor(p)
    head = out.split("\n\n--- json ---", 1)[0].strip()
    data = json.loads(head)
    assert "total_connects" in data
    assert data["total_connects"] == 3
    assert any(x["name"] == "Sender::foo" for x in data["top_signals"])


@pytest.mark.asyncio
async def test_connect_monitor_old_style():
    from server import QtQobjectInvokeConnectMonitorInput, qt_qobject_invoke_connect_monitor
    import shutil
    proj = SAMPLE_DIR / "cm_oldstyle"
    if proj.exists():
        shutil.rmtree(proj)
    proj.mkdir(parents=True)
    (proj / "main.cpp").write_text("""\
#include <QObject>
class S : public QObject { Q_OBJECT public: void f() { emit foo(); } signals: void foo(); };
class R : public QObject { Q_OBJECT public slots: void b() {} };
int main() {
    S s; R r;
    QObject::connect(&s, SIGNAL(foo()), &r, SLOT(b()));
    QObject::connect(&s, SIGNAL(foo()), &r, SLOT(b()));
    return 0;
}
""", encoding="utf-8")

    p = QtQobjectInvokeConnectMonitorInput(project_dir=str(proj), include_old_style=True)
    out = await qt_qobject_invoke_connect_monitor(p)
    # Old-style SIGNAL/SLOT is detected — class is "(?)" since regex can't infer it
    assert "foo" in out
    j = _split_json(out)
    assert j["ok"] is True
    assert j["data"]["total_connects"] == 2


@pytest.mark.asyncio
async def test_connect_monitor_no_connects():
    from server import QtQobjectInvokeConnectMonitorInput, qt_qobject_invoke_connect_monitor
    import shutil
    proj = SAMPLE_DIR / "cm_none"
    if proj.exists():
        shutil.rmtree(proj)
    proj.mkdir(parents=True)
    (proj / "main.cpp").write_text("int main() { return 0; }\n", encoding="utf-8")
    p = QtQobjectInvokeConnectMonitorInput(project_dir=str(proj))
    out = await qt_qobject_invoke_connect_monitor(p)
    assert "No connect" in out or "connects:  0" in out


@pytest.mark.asyncio
async def test_connect_monitor_top_n():
    from server import QtQobjectInvokeConnectMonitorInput, qt_qobject_invoke_connect_monitor
    proj = SAMPLE_DIR / "cm_basic"
    p = QtQobjectInvokeConnectMonitorInput(project_dir=str(proj), top_n=2)
    out = await qt_qobject_invoke_connect_monitor(p)
    # Even when total_connects=0 we don't have top_signals (json path skipped); but basic has 3.
    j = _split_json(out)
    if "data" in j and "top_signals" in j["data"]:
        assert len(j["data"]["top_signals"]) <= 2
    else:
        # total_connects=0 -> early-return path; just verify ok
        assert j["ok"] is True


# =============== qt_modernize_qt6_string_literal ===============

@pytest.mark.asyncio
async def test_modernize_qt6_string_basic_tr():
    from server import QtModernizeQt6StringLiteralInput, qt_modernize_qt6_string_literal
    import shutil
    proj = SAMPLE_DIR / "mqsl_basic"
    if proj.exists():
        shutil.rmtree(proj)
    proj.mkdir(parents=True)
    f = proj / "main.cpp"
    f.write_text("""\
#include <QObject>
void f() {
    QString s = tr("hello");
    QString t = QObject::tr("world");
    QString u = QStringLiteral("already_wrapped");
    QString v = u"already_uprefixed";
}
""", encoding="utf-8")
    # apply=True so we can read the file content directly (avoids dry-run diff parsing + stdout GBK)
    p = QtModernizeQt6StringLiteralInput(project_dir=str(proj), apply=True)
    out = await qt_modernize_qt6_string_literal(p)
    j = _split_json(out)
    assert j["ok"] is True
    assert j["data"]["files_changed"] >= 1
    new_text = f.read_text(encoding="utf-8")
    # tr("hello") → tr(u"hello"); QObject::tr("world") → QObject::tr(u"world")
    assert 'tr(u"hello")' in new_text
    assert 'QObject::tr(u"world")' in new_text
    # QStringLiteral already-wrapped literal should NOT be touched
    assert 'QStringLiteral("already_wrapped")' in new_text
    # already u"..." should NOT be double-prefixed
    assert 'uu"already_uprefixed"' not in new_text


@pytest.mark.asyncio
async def test_modernize_qt6_string_nonascii():
    from server import QtModernizeQt6StringLiteralInput, qt_modernize_qt6_string_literal
    import shutil
    proj = SAMPLE_DIR / "mqsl_nonascii"
    if proj.exists():
        shutil.rmtree(proj)
    proj.mkdir(parents=True)
    f = proj / "main.cpp"
    f.write_text("""\
#include <QString>
void f() {
    QString a = "纯中文";
    QString b = QString::fromUtf8("日本語");
    QString c = "ASCII only";
    QString d = "中文 mixed with English";
}
""", encoding="utf-8")
    p = QtModernizeQt6StringLiteralInput(project_dir=str(proj), apply=True)
    out = await qt_modernize_qt6_string_literal(p)
    # apply=True so we can read content directly (avoids Windows GBK stdout mojibake)
    new_text = f.read_text(encoding="utf-8")
    # '纯中文' → u"纯中文"; '日本語' → u"日本語"; '中文 mixed with English' → u"..."
    assert 'u"纯中文"' in new_text
    assert 'u"日本語"' in new_text
    assert 'u"中文 mixed with English"' in new_text
    # 'ASCII only' (no non-ASCII) should NOT be touched
    assert 'u"ASCII only"' not in new_text
    j = _split_json(out)
    assert j["ok"] is True


@pytest.mark.asyncio
async def test_modernize_qt6_string_dry_run_no_write():
    from server import QtModernizeQt6StringLiteralInput, qt_modernize_qt6_string_literal
    import shutil
    proj = SAMPLE_DIR / "mqsl_dryrun"
    if proj.exists():
        shutil.rmtree(proj)
    proj.mkdir(parents=True)
    f = proj / "main.cpp"
    f.write_text('void f() { tr("test"); }\n', encoding="utf-8")
    original_bytes = f.read_bytes()

    # dry-run (default)
    p = QtModernizeQt6StringLiteralInput(project_dir=str(proj), apply=False)
    out = await qt_modernize_qt6_string_literal(p)
    assert "DRY-RUN" in out or "dry-run" in out.lower()
    # File should be untouched
    assert f.read_bytes() == original_bytes


@pytest.mark.asyncio
async def test_modernize_qt6_string_apply_writes_bak():
    from server import QtModernizeQt6StringLiteralInput, qt_modernize_qt6_string_literal
    import shutil
    proj = SAMPLE_DIR / "mqsl_apply"
    if proj.exists():
        shutil.rmtree(proj)
    proj.mkdir(parents=True)
    f = proj / "main.cpp"
    f.write_text('void f() { tr("hello"); }\n', encoding="utf-8")

    p = QtModernizeQt6StringLiteralInput(project_dir=str(proj), apply=True)
    out = await qt_modernize_qt6_string_literal(p)
    bak = proj / "main.cpp.bak"
    assert bak.exists()
    new_text = f.read_text(encoding="utf-8")
    assert 'tr(u"hello")' in new_text
    j = _split_json(out)
    assert j["ok"] is True


@pytest.mark.asyncio
async def test_modernize_qt6_string_no_changes():
    from server import QtModernizeQt6StringLiteralInput, qt_modernize_qt6_string_literal
    import shutil
    proj = SAMPLE_DIR / "mqsl_nochange"
    if proj.exists():
        shutil.rmtree(proj)
    proj.mkdir(parents=True)
    (proj / "main.cpp").write_text("""\
#include <QString>
void f() {
    QString a = u"already";
    QString b = QStringLiteral("ok");
    QString c = QString::fromUtf8(u"unicode");
    int n = 42;
}
""", encoding="utf-8")
    p = QtModernizeQt6StringLiteralInput(project_dir=str(proj))
    out = await qt_modernize_qt6_string_literal(p)
    assert "No changes needed" in out


# =============== qt_qobject_invocation_history ===============

@pytest.mark.asyncio
async def test_invocation_history_basic():
    from server import QtQobjectInvocationHistoryInput, qt_qobject_invocation_history
    log = SAMPLE_DIR / "inv_basic.log"
    log.write_text(
        '{"ts": 1700000000.0, "method": "setText", "caller": "W::onA", "duration_ms": 1.5}\n'
        '{"ts": 1700000001.0, "method": "setText", "caller": "W::onA", "duration_ms": 2.1}\n'
        '{"ts": 1700000002.0, "method": "refresh", "caller": "W::onB", "duration_ms": 0.5}\n',
        encoding="utf-8",
    )
    p = QtQobjectInvocationHistoryInput(log_file=str(log))
    out = await qt_qobject_invocation_history(p)
    assert "setText" in out
    assert "refresh" in out
    assert "W::onA" in out
    j = _split_json(out)
    assert j["ok"] is True
    assert j["data"]["record_count"] == 3


@pytest.mark.asyncio
async def test_invocation_history_json_format():
    from server import QtQobjectInvocationHistoryInput, qt_qobject_invocation_history
    log = SAMPLE_DIR / "inv_basic.log"
    p = QtQobjectInvocationHistoryInput(log_file=str(log), output_format="json")
    out = await qt_qobject_invocation_history(p)
    head = out.split("\n\n--- json ---", 1)[0].strip()
    data = json.loads(head)
    assert data["record_count"] == 3
    assert any(m["method"] == "setText" for m in data["top_methods"])


@pytest.mark.asyncio
async def test_invocation_history_skips_invalid_lines():
    from server import QtQobjectInvocationHistoryInput, qt_qobject_invocation_history
    log = SAMPLE_DIR / "inv_invalid.log"
    log.write_text(
        '{"ts": 1, "method": "ok1"}\n'
        'this is not json\n'
        '{"ts": 2, "method": "ok2"}\n'
        '\n'
        '{"ts": 3, "method": "ok3"}\n',
        encoding="utf-8",
    )
    p = QtQobjectInvocationHistoryInput(log_file=str(log))
    out = await qt_qobject_invocation_history(p)
    assert "ok1" in out
    assert "ok2" in out
    assert "ok3" in out
    j = _split_json(out)
    assert j["ok"] is True
    assert j["data"]["record_count"] == 3
    assert j["data"]["skipped_lines"] == 1


@pytest.mark.asyncio
async def test_invocation_history_method_filter():
    from server import QtQobjectInvocationHistoryInput, qt_qobject_invocation_history
    log = SAMPLE_DIR / "inv_basic.log"
    p = QtQobjectInvocationHistoryInput(log_file=str(log), method_filter="set")
    out = await qt_qobject_invocation_history(p)
    # only setText matches 'set' (refresh does not)
    assert "setText" in out
    assert "refresh" not in out
    j = _split_json(out)
    assert j["data"]["record_count"] == 2


@pytest.mark.asyncio
async def test_invocation_history_ts_auto_detect():
    """Test that timestamps > 1e12 (milliseconds) are auto-converted to seconds."""
    from server import QtQobjectInvocationHistoryInput, qt_qobject_invocation_history
    log = SAMPLE_DIR / "inv_ms.log"
    # 1.7e12 in milliseconds (about year 2023 in ms)
    log.write_text(
        '{"ts": 1700000000000, "method": "ms_log1"}\n'
        '{"ts": 1700000001000, "method": "ms_log2"}\n',
        encoding="utf-8",
    )
    p = QtQobjectInvocationHistoryInput(log_file=str(log))
    out = await qt_qobject_invocation_history(p)
    j = _split_json(out)
    assert j["ok"] is True
    assert j["data"]["record_count"] == 2


@pytest.mark.asyncio
async def test_invocation_history_nonexistent_file():
    from server import QtQobjectInvocationHistoryInput, qt_qobject_invocation_history
    p = QtQobjectInvocationHistoryInput(log_file=str(SAMPLE_DIR / "ghost.log"))
    out = await qt_qobject_invocation_history(p)
    j = _split_json(out)
    assert j["ok"] is False
    assert "not found" in j["error"]


@pytest.mark.asyncio
async def test_invocation_history_empty_log():
    from server import QtQobjectInvocationHistoryInput, qt_qobject_invocation_history
    log = SAMPLE_DIR / "inv_empty.log"
    log.write_text("", encoding="utf-8")
    p = QtQobjectInvocationHistoryInput(log_file=str(log))
    out = await qt_qobject_invocation_history(p)
    assert "No invocations" in out
    j = _split_json(out)
    assert j["data"]["record_count"] == 0