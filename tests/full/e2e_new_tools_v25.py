"""e2e for v25 new tools (v0.3.9):

NEW TOOLS:
  - qt_heap_snapshot  (massif / heaptrack text parser + leak candidates)

Run: python e2e_new_tools_v25.py
"""

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import server
from server import SANDBOX_TMP, QtHeapSnapshotInput

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


# ============ qt_heap_snapshot ============

SAMPLE_MASSIF = """\
desc: peak
cmd: ./myapp
time: 0
mem_heap_B=0
mem_heap_extra_B=0
mem_stacks_B=0
heap_tree=empty
snapshot=0
time=100
desc: peak
cmd: ./myapp
snapshot=1
mem_heap_B=1024
mem_heap_extra_B=0
mem_stacks_B=0
heap_tree=detailed
 n0: 1024 0x400789
  n0: 768 0x4007AB
  n1: 256 0x4007CD
snapshot=2
time=200
mem_heap_B=2048
mem_heap_extra_B=0
mem_stacks_B=0
heap_tree=detailed
 n0: 2048 0x400789
  n0: 1536 0x4007AB
  n1: 512 0x4007CD
snapshot=3
time=300
mem_heap_B=4096
mem_heap_extra_B=0
mem_stacks_B=0
heap_tree=detailed
 n0: 4096 0x400789
  n0: 3072 0x4007AB
  n1: 1024 0x4007CD
"""

SAMPLE_HEAPTRACK = """\
# tracking 1.5s
allocated 1048576 bytes in 10 times at 0x401234 (malloc)
allocated 524288 bytes in 5 times at 0x405678 (myClass::create)
allocated 65536 bytes in 100 times at 0x409ABC (imageCache::load)
allocated 8192 bytes in 1 times at 0x40FEDC (initialization)
"""


async def test_heap_snapshot_massif():
    print("\n[1] qt_heap_snapshot -- massif happy path")
    work = fresh_dir(SANDBOX_TMP, "v25_heap_massif")
    src = work / "sample.txt"
    src.write_text(SAMPLE_MASSIF, encoding="utf-8")
    out = await server.qt_heap_snapshot(QtHeapSnapshotInput(source_file=str(src), top_n=5))
    print(out[:400])
    check("returns success", not out.startswith("Error:"), f"snippet: {out[:200]!r}")
    check("detects massif format", "format : massif" in out)
    check("shows snapshots count", "snapshots" in out)
    check("shows peak snapshot", "peak" in out and "4096" in out)
    check("flags leak candidate (monotonic growth)", "Leak candidates" in out)
    check("shows overall top tree", "0x400789" in out)


async def test_heap_snapshot_heaptrack():
    print("\n[2] qt_heap_snapshot -- heaptrack happy path")
    work = fresh_dir(SANDBOX_TMP, "v25_heap_ht")
    src = work / "sample.txt"
    src.write_text(SAMPLE_HEAPTRACK, encoding="utf-8")
    out = await server.qt_heap_snapshot(QtHeapSnapshotInput(source_file=str(src), top_n=5))
    print(out[:400])
    check("detects heaptrack format", "format : heaptrack" in out)
    check("shows total sites", "sites" in out)
    check("top by size shows 0x401234", "0x401234" in out)
    check("top by count shows imageCache", "imageCache" in out or "0x409ABC" in out)
    check("leak candidates flagged for repeated alloc",
          "Leak candidates" in out and "imageCache" in out)


async def test_heap_snapshot_unknown_format():
    print("\n[3] qt_heap_snapshot -- unknown format returns ERR")
    work = fresh_dir(SANDBOX_TMP, "v25_heap_unknown")
    src = work / "junk.txt"
    src.write_text("lorem ipsum\nfoo bar baz\n", encoding="utf-8")
    out = await server.qt_heap_snapshot(QtHeapSnapshotInput(source_file=str(src), top_n=5))
    print(out[:200])
    check("returns error", out.startswith("ERR") or "Error:" in out.lower() or "unrecognized" in out)


async def test_heap_snapshot_missing_file():
    print("\n[4] qt_heap_snapshot -- missing file returns ERR")
    out = await server.qt_heap_snapshot(
        QtHeapSnapshotInput(source_file=str(SANDBOX_TMP / "v25_does_not_exist.txt"), top_n=5)
    )
    print(out[:200])
    check("returns error", "cannot read" in out or "outside" in out or "does not exist" in out or out.startswith("ERR"))


async def test_heap_snapshot_json_trailer():
    print("\n[5] qt_heap_snapshot -- JSON trailer (QT_MCP_JSON=1)")
    work = fresh_dir(SANDBOX_TMP, "v25_heap_json")
    src = work / "sample.txt"
    src.write_text(SAMPLE_HEAPTRACK, encoding="utf-8")
    old = os.environ.get("QT_MCP_JSON") if 'os' in dir() else None
    os.environ["QT_MCP_JSON"] = "1"
    try:
        out = await server.qt_heap_snapshot(QtHeapSnapshotInput(source_file=str(src), top_n=3))
    finally:
        os.environ.pop("QT_MCP_JSON", None)
        if old:
            os.environ["QT_MCP_JSON"] = old
    check("json trailer present", "--- json ---" in out)
    check("json says ok:true", '"ok": true' in out or '"ok":true' in out)


import os
# already imported above
# (re-import here to keep tool happy if PYTHONFROZEN trims)


async def main():
    await test_heap_snapshot_massif()
    await test_heap_snapshot_heaptrack()
    await test_heap_snapshot_unknown_format()
    await test_heap_snapshot_missing_file()
    await test_heap_snapshot_json_trailer()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\n=== Summary ===  passed {passed} / {total}")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
