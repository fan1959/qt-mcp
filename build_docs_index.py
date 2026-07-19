"""Build a SQLite FTS5 index of the local Qt 5.14.2 HTML documentation.

Walks every .html under E:\\Download_tools\\QT\\Docs\\Qt-5.14.2\\, extracts the
<title> and first <p>, and inserts into a portable FTS5 table.

Output DB: E:\\Download_tools\\QT\\.tmp\\qt_docs_index.db
Index schema:
    pages(title, description, module, url, body)
    pages_fts(title, description, body)  -- FTS5 virtual table
"""
import re
import sqlite3
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DOCS_ROOT = Path(r"E:\Download_tools\QT\Docs\Qt-5.14.2")
DB_PATH = Path(r"E:\Download_tools\QT\.tmp\qt_docs_index.db")

TAG_RE = re.compile(r"<[^>]+>", re.S)
SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
WHITESPACE_RE = re.compile(r"\s+")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
FIRST_P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.S | re.I)


def html_to_text(s: str) -> str:
    s = SCRIPT_STYLE_RE.sub(" ", s)
    s = TAG_RE.sub(" ", s)
    s = WHITESPACE_RE.sub(" ", s)
    return s.strip()


def first_paragraph(html: str, max_len: int = 800) -> str:
    """Extract the first <p>...</p>, returned as plain text, truncated."""
    m = FIRST_P_RE.search(html)
    if not m:
        return ""
    text = html_to_text(m.group(1))
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "..."
    return text


def module_of(path: Path) -> str:
    """Return the module name (e.g. 'qtwidgets') from a path under DOCS_ROOT."""
    rel = path.relative_to(DOCS_ROOT)
    parts = rel.parts
    if len(parts) >= 1:
        return parts[0]
    return ""


def url_of(path: Path) -> str:
    """file:// URL the docs server would expose for this page (purely informational)."""
    rel = path.relative_to(DOCS_ROOT)
    return f"file:///{rel.as_posix()}"


def build():
    if not DOCS_ROOT.exists():
        print(f"DOCS_ROOT not found: {DOCS_ROOT}")
        return 1

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("""
        CREATE VIRTUAL TABLE pages_fts USING fts5(
            title,
            description,
            body,
            tokenize = 'porter unicode61'
        )
    """)
    conn.execute("""
        CREATE TABLE pages (
            id INTEGER PRIMARY KEY,
            title TEXT,
            description TEXT,
            module TEXT,
            url TEXT,
            body TEXT
        )
    """)

    html_files = list(DOCS_ROOT.rglob("*.html"))
    print(f"Indexing {len(html_files)} HTML files from {DOCS_ROOT}")

    t0 = time.time()
    n = 0
    skipped = 0
    for path in html_files:
        try:
            html = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            skipped += 1
            continue
        tm = TITLE_RE.search(html)
        title = html_to_text(tm.group(1)) if tm else path.stem
        description = first_paragraph(html)
        # Body = whole visible text, but truncated to keep index lean.
        body = html_to_text(html)
        if len(body) > 4000:
            body = body[:4000].rsplit(" ", 1)[0] + "..."
        module = module_of(path)
        url = url_of(path)
        conn.execute(
            "INSERT INTO pages(title, description, module, url, body) VALUES (?, ?, ?, ?, ?)",
            (title, description, module, url, body),
        )
        rowid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO pages_fts(rowid, title, description, body) VALUES (?, ?, ?, ?)",
            (rowid, title, description, body),
        )
        n += 1
        if n % 500 == 0:
            conn.commit()
            print(f"  ... {n} indexed in {time.time() - t0:.1f}s")

    conn.commit()
    conn.close()
    dt = time.time() - t0
    size_mb = DB_PATH.stat().st_size / 1024 / 1024
    print(f"Indexed {n} pages (skipped {skipped}) in {dt:.1f}s. DB: {DB_PATH} ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(build())