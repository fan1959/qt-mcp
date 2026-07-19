"""e2e for v9 new tools: qt_score, qt_timer, qt_replay, qt_lint, qt_analyze.

Run: python e2e_new_tools_v9.py
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import server
from server import (
    QtScoreInput,
    QtTimerInput,
    QtReplayInput,
    QtLintInput,
    QtAnalyzeInput,
    SANDBOX_TMP,
    SANDBOX_ROOT,
)

PASS = "\033[32m[OK]\033[0m"
FAIL = "\033[31m[FAIL]\033[0m"
results = []


def check(name: str, cond: bool, hint: str = "") -> bool:
    tag = PASS if cond else FAIL
    line = f"  {tag} {name}"
    if hint and not cond:
        line += f"  ({hint})"
    print(line)
    results.append((name, cond))
    return cond


async def test_qt_score_add_list():
    """qt_score add then list should show the entries."""
    print("\n[1] qt_score -- add + list")
    sf = SANDBOX_TMP / "v9_score_basic"
    if sf.exists():
        shutil.rmtree(sf, ignore_errors=True)

    add1 = await server.qt_score(QtScoreInput(action="add", score_file=str(sf / "scores.json"), player="alice", score=100, game="chess"))
    check("add alice succeeded", "added" in add1.lower())
    add2 = await server.qt_score(QtScoreInput(action="add", score_file=str(sf / "scores.json"), player="bob", score=150, game="chess"))
    check("add bob succeeded", "added" in add2.lower())

    lst = await server.qt_score(QtScoreInput(action="list", score_file=str(sf / "scores.json")))
    check("list shows alice", "alice" in lst)
    check("list shows bob", "bob" in lst)


async def test_qt_score_leaderboard():
    print("\n[2] qt_score -- leaderboard ranks by score")
    sf = SANDBOX_TMP / "v9_score_lb"
    if sf.exists():
        shutil.rmtree(sf, ignore_errors=True)
    for p, s in [("alice", 50), ("bob", 200), ("charlie", 100)]:
        await server.qt_score(QtScoreInput(action="add", score_file=str(sf / "scores.json"), player=p, score=s, game="go"))

    lb = await server.qt_score(QtScoreInput(action="leaderboard", score_file=str(sf / "scores.json"), game="go", top_n=3))
    check("leaderboard starts with bob", lb.find("bob") < lb.find("charlie") < lb.find("alice"))


async def test_qt_score_reset():
    print("\n[3] qt_score -- reset clears all")
    sf = SANDBOX_TMP / "v9_score_reset"
    if sf.exists():
        shutil.rmtree(sf, ignore_errors=True)
    await server.qt_score(QtScoreInput(action="add", score_file=str(sf / "scores.json"), player="x", score=10))
    out = await server.qt_score(QtScoreInput(action="reset", score_file=str(sf / "scores.json")))
    check("reset succeeded", "reset" in out.lower())
    lst = await server.qt_score(QtScoreInput(action="list", score_file=str(sf / "scores.json")))
    check("after reset, no entries", "no scores" in lst.lower() or "no entries" in lst.lower())


async def test_qt_score_invalid_action():
    print("\n[4] qt_score -- invalid action")
    out = await server.qt_score(QtScoreInput(action="bad"))
    check("rejects invalid action", "invalid action" in out)


async def test_qt_timer_start_status():
    print("\n[5] qt_timer -- start + status")
    sf = SANDBOX_TMP / "v9_timer_basic"
    if sf.exists():
        shutil.rmtree(sf, ignore_errors=True)

    start = await server.qt_timer(QtTimerInput(action="start", timer_id="player1_turn", state_file=str(sf / "t.json")))
    check("start succeeded", "started" in start.lower())

    await asyncio.sleep(0.2)
    status = await server.qt_timer(QtTimerInput(action="status", timer_id="player1_turn", state_file=str(sf / "t.json")))
    check("status reports running", "running" in status)


async def test_qt_timer_pause_resume():
    print("\n[6] qt_timer -- pause + resume")
    sf = SANDBOX_TMP / "v9_timer_pause"
    if sf.exists():
        shutil.rmtree(sf, ignore_errors=True)
    await server.qt_timer(QtTimerInput(action="start", timer_id="t1", state_file=str(sf / "t.json")))
    await asyncio.sleep(0.1)
    pause = await server.qt_timer(QtTimerInput(action="pause", timer_id="t1", state_file=str(sf / "t.json")))
    check("pause succeeded", "paused" in pause.lower())

    # Capture elapsed at pause
    await asyncio.sleep(0.2)
    resume = await server.qt_timer(QtTimerInput(action="resume", timer_id="t1", state_file=str(sf / "t.json")))
    check("resume succeeded", "resumed" in resume.lower())


async def test_qt_timer_stop():
    print("\n[7] qt_timer -- stop")
    sf = SANDBOX_TMP / "v9_timer_stop"
    if sf.exists():
        shutil.rmtree(sf, ignore_errors=True)
    await server.qt_timer(QtTimerInput(action="start", timer_id="t1", state_file=str(sf / "t.json")))
    await asyncio.sleep(0.1)
    stop = await server.qt_timer(QtTimerInput(action="stop", timer_id="t1", state_file=str(sf / "t.json")))
    check("stop reports final elapsed", "stopped" in stop.lower() and "elapsed" in stop.lower())


async def test_qt_timer_list():
    print("\n[8] qt_timer -- list shows all timers")
    sf = SANDBOX_TMP / "v9_timer_list"
    if sf.exists():
        shutil.rmtree(sf, ignore_errors=True)
    for tid in ["t1", "t2", "t3"]:
        await server.qt_timer(QtTimerInput(action="start", timer_id=tid, state_file=str(sf / "t.json")))
    lst = await server.qt_timer(QtTimerInput(action="list", state_file=str(sf / "t.json")))
    check("lists t1", "t1" in lst)
    check("lists t2", "t2" in lst)
    check("lists t3", "t3" in lst)


async def test_qt_timer_invalid_action():
    print("\n[9] qt_timer -- invalid action")
    out = await server.qt_timer(QtTimerInput(action="bad"))
    check("rejects invalid action", "invalid action" in out)


async def test_qt_replay_record_play():
    print("\n[10] qt_replay -- record + play")
    rd = SANDBOX_TMP / "v9_replay_basic"
    if rd.exists():
        shutil.rmtree(rd, ignore_errors=True)
    for step_type, data in [("move", {"x": 1, "y": 2}), ("draw", {"card": "ace"}), ("pass", {})]:
        await server.qt_replay(QtReplayInput(
            action="record", session_id="game1", replay_dir=str(rd),
            step_type=step_type, data=data,
        ))
    play = await server.qt_replay(QtReplayInput(action="play", session_id="game1", replay_dir=str(rd)))
    check("play shows move", "move" in play)
    check("play shows draw", "draw" in play)
    check("play shows pass", "pass" in play)


async def test_qt_replay_list():
    print("\n[11] qt_replay -- list shows all replays")
    rd = SANDBOX_TMP / "v9_replay_list"
    if rd.exists():
        shutil.rmtree(rd, ignore_errors=True)
    for sid in ["g1", "g2"]:
        await server.qt_replay(QtReplayInput(action="record", session_id=sid, replay_dir=str(rd), step_type="move", data={}))
    lst = await server.qt_replay(QtReplayInput(action="list", replay_dir=str(rd)))
    check("lists g1", "g1" in lst)
    check("lists g2", "g2" in lst)


async def test_qt_replay_load():
    print("\n[12] qt_replay -- load returns full JSON")
    rd = SANDBOX_TMP / "v9_replay_load"
    if rd.exists():
        shutil.rmtree(rd, ignore_errors=True)
    await server.qt_replay(QtReplayInput(action="record", session_id="x", replay_dir=str(rd), step_type="test", data={"k": "v"}))

    # Enable JSON trailer for this call
    old_env = os.environ.get("QT_MCP_JSON")
    os.environ["QT_MCP_JSON"] = "1"
    try:
        out = await server.qt_replay(QtReplayInput(action="load", session_id="x", replay_dir=str(rd)))
    finally:
        if old_env is None:
            os.environ.pop("QT_MCP_JSON", None)
        else:
            os.environ["QT_MCP_JSON"] = old_env

    check("load reports steps count", "steps:   1" in out)
    check("load includes json trailer with data", '"k": "v"' in out or "'k': 'v'" in out)
    check("load trailer has ok=true", '"ok": true' in out)


async def test_qt_replay_delete():
    print("\n[13] qt_replay -- delete")
    rd = SANDBOX_TMP / "v9_replay_del"
    if rd.exists():
        shutil.rmtree(rd, ignore_errors=True)
    await server.qt_replay(QtReplayInput(action="record", session_id="todel", replay_dir=str(rd), step_type="x", data={}))
    out = await server.qt_replay(QtReplayInput(action="delete", session_id="todel", replay_dir=str(rd)))
    check("delete succeeded", "deleted" in out.lower())


async def test_qt_lint_no_files():
    print("\n[14] qt_lint -- empty project (graceful)")
    tmp = SANDBOX_TMP / "v9_lint_empty"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    out = await server.qt_lint(QtLintInput(project_dir=str(tmp), linters=["cpplint"]))
    check("handles empty project", "LINT PASS" in out or "no files" in out.lower() or "not found" in out.lower())


async def test_qt_lint_basic_cpp():
    print("\n[15] qt_lint -- lint a project with .cpp files")
    tmp = SANDBOX_TMP / "v9_lint_cpp"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    (tmp / "app.cpp").write_text(
        '// simple file\n#include <iostream>\nint main() { std::cout << "hi" << std::endl; return 0; }\n',
        encoding="utf-8",
    )
    out = await server.qt_lint(QtLintInput(project_dir=str(tmp), linters=["cpplint"]))
    check("returns text with cpplint section", "cpplint" in out)


async def test_qt_lint_sandbox():
    print("\n[16] qt_lint -- rejects paths outside sandbox")
    out = await server.qt_lint(QtLintInput(project_dir=r"D:\outside\foo"))
    check("sandbox error", "outside the allowed sandbox" in out)


async def test_qt_analyze_no_cpp():
    print("\n[17] qt_analyze -- missing project")
    out = await server.qt_analyze(QtAnalyzeInput(project_dir=str(SANDBOX_TMP / "v9_analyze_missing")))
    check("reports missing project", "not a directory" in out or "no .cpp" in out)


async def test_qt_analyze_sandbox():
    print("\n[18] qt_analyze -- rejects paths outside sandbox")
    out = await server.qt_analyze(QtAnalyzeInput(project_dir=r"D:\outside\foo"))
    check("sandbox error", "outside the allowed sandbox" in out)


async def main():
    await test_qt_score_add_list()
    await test_qt_score_leaderboard()
    await test_qt_score_reset()
    await test_qt_score_invalid_action()
    await test_qt_timer_start_status()
    await test_qt_timer_pause_resume()
    await test_qt_timer_stop()
    await test_qt_timer_list()
    await test_qt_timer_invalid_action()
    await test_qt_replay_record_play()
    await test_qt_replay_list()
    await test_qt_replay_load()
    await test_qt_replay_delete()
    await test_qt_lint_no_files()
    await test_qt_lint_basic_cpp()
    await test_qt_lint_sandbox()
    await test_qt_analyze_no_cpp()
    await test_qt_analyze_sandbox()

    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    total = len(results)
    print()
    print(f"\033[1m=== V9 E2E: {passed}/{total} passed, {failed} failed ===\033[0m")
    if failed:
        print("Failed:")
        for name, ok in results:
            if not ok:
                print(f"  - {name}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())