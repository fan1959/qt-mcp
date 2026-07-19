# docs_data/

This directory holds the local FTS5 full-text index of the Qt 5.14.2 HTML
documentation, used by `qt_docs_search`.

**The index file (`*.db`) is gitignored — it's ~53 MB.**

## Rebuilding the index

From this directory:

```bash
python ../build_docs_index.py
# writes qt_5_14_2_docs.db
```

`build_docs_index.py` walks the Qt 5.14.2 HTML tree (default:
`E:\Download_tools\QT\Docs\Qt-5.14.2\qtwidgets`), strips navigation/footer
boilerplate, tokenizes each page, and bulk-loads everything into an
`fts5(title, body, module)` virtual table.

Rebuilding takes 1-2 minutes on a modern laptop. The resulting `.db` is
~53 MB; `qt_docs_search` reads it on every call.

## Query syntax

FTS5 syntax. See `qt_docs_search` docstring for full details:

- `QPushButton AND click`
- `"signal slot"`
- `QList NOT foreach`
- `(QWidget OR QDialog) AND modal`

Snippets are returned with `**term**` markers around matched tokens.

## Customizing the source tree

If your Qt install lives elsewhere, edit the `QT_DOCS_ROOT` constant in
`build_docs_index.py`. You can also re-run the script with a one-off override
by setting the env var `QT_DOCS_ROOT` before invoking it.