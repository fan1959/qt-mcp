import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

"""E2E test for the new GUI-path accelerator tools: qt_creator_open + qt_creator_run.

Demonstrates the fast Qt-Creator-GUI workflow:
  1. qt_scaffold a fresh widget project (qt-mcp, file-level)
  2. qt_creator_open it in Qt Creator (skip Welcome, skip wizard, reuse if running)
  3. Wait for the main window to be ready
  4. qt_creator_run = build (Ctrl+B) + run (Ctrl+R) inside the IDE
  5. Confirm the .exe is alive (parent is qtcreator.exe)
  6. Kill the app + close Qt Creator cleanly
  7. Sandbox rejection paths

The whole flow is intentionally short — this is the speedup the user asked for.
"""
import asyncio
import shutil
import sys
import time
import uuid
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).parent.parent.parent / "server.py"
TMP_ROOT = Path(r"E:\Download_tools\QT\.tmp")


async def call(session, tool, expect_error=False, **kwargs):
    print(f"\n=== {tool}({list(kwargs.keys())}) ===", flush=True)
    res = await session.call_tool(tool, arguments={"params": kwargs} if kwargs else {})
    text = res.content[0].text if res.content else ""
    if res.isError or "Error" in text:
        if not expect_error:
            raise RuntimeError(f"{tool} failed unexpectedly:\n{text[:400]}")
    return text


async def main():
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    work = TMP_ROOT / f"e2e_creator_{uuid.uuid4().hex[:8]}"
    work.mkdir(parents=True, exist_ok=True)
    proj = work / "demo_creator"
    print(f"Workdir: {work}")

    keep_on_failure = {"v": False}  # mutated on failure to skip cleanup

    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    try:
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()

                # ---- 1) Scaffold a project (qt-mcp, file-level) ----
                print("\n# ---- scaffold via qt-mcp ----", flush=True)
                t = await call(s, "qt_scaffold", name="demo", template="widget", output_dir=str(proj))
                assert "Scaffolded" in t, t

                # ---- 2) Open it in Qt Creator (skip welcome + wizard) ----
                print("\n# ---- qt_creator_open ----", flush=True)
                t0 = time.time()
                t = await call(s, "qt_creator_open",
                               pro_file=str(proj / "demo.pro"),
                               skip_welcome=True, reuse_existing=True, ready_timeout=20)
                open_elapsed = time.time() - t0
                print(f"  -> qt_creator_open returned in {open_elapsed:.1f}s")
                assert "Qt Creator ready" in t, f"qt_creator_open didn't report ready:\n{t}"
                # Parse PID from "Qt Creator ready (PID 12345)"
                import re
                m = re.search(r"PID (\d+)", t)
                assert m, f"no PID in response: {t}"
                creator_pid = int(m.group(1))
                print(f"  -> creator PID = {creator_pid}")

                # ---- 3) Verify Qt Creator is actually running and has the project loaded ----
                import subprocess
                ps = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq qtcreator.exe", "/NH"],
                    capture_output=True, text=True, timeout=5,
                )
                assert str(creator_pid) in ps.stdout, f"Qt Creator PID {creator_pid} not in tasklist"

                # Wait for project to actually load (kit dialog + .pro.user creation)
                deadline = time.time() + 15
                while time.time() < deadline:
                    if (proj / "demo.pro.user").is_file():
                        break
                    time.sleep(0.5)
                pro_user = proj / "demo.pro.user"
                print(f"  -> .pro.user created: {pro_user.is_file()}")
                # Diagnostic: capture Qt Creator state right after open
                from pywinauto import Application
                try:
                    app = Application(backend="uia").connect(process=creator_pid)
                    win = next((w for w in app.windows()
                                if w.class_name() == "Core::Internal::MainWindow"), None)
                    if win:
                        title = win.window_text()
                        print(f"  -> window title: {title!r}")
                        shot_path = work / "after_open.png"
                        win.capture_as_image().save(str(shot_path))
                        print(f"  -> diagnostic screenshot: {shot_path}")
                except Exception as e:
                    print(f"  -> diagnostic screenshot failed: {e}")

                # ---- 4) Build + run from inside the IDE ----
                print("\n# ---- qt_creator_run (build + run) ----", flush=True)
                t0 = time.time()
                t = await call(s, "qt_creator_run",
                               project_dir=str(proj),
                               wait_for_build=90, wait_for_run=15,
                               screenshot=str(work / "qtcreator_after_run.png"))
                run_elapsed = time.time() - t0
                print(f"  -> qt_creator_run returned in {run_elapsed:.1f}s")
                print(f"  -> result:\n{textwrap_indent(t, '     ')}")

                # Diagnostic: check if the .exe was actually built
                pro_file = next(proj.glob("*.pro"))
                built_exes = sorted(Path(p) for p in proj.parent.glob(f"build-{pro_file.stem}-*/debug/*.exe"))
                print(f"  -> built exes found: {[e.name for e in built_exes]}")

                # On failure, leave the work dir intact for inspection.
                if "App launched" not in t:
                    keep_on_failure["v"] = True
                    print(f"  -> leaving {work} intact for debugging")
                    print(f"  -> screenshot: {work / 'qtcreator_after_run.png'}")
                    raise RuntimeError(f"qt_creator_run didn't report app launch:\n{t}")
                m = re.search(r"PID (\d+)\)", t)
                assert m, f"no child PID in response: {t}"
                child_pid = int(m.group(1))
                print(f"  -> launched app PID = {child_pid}")

                # ---- 5) Confirm the .exe is actually running ----
                ps = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {child_pid}", "/NH"],
                    capture_output=True, text=True, timeout=5,
                )
                assert str(child_pid) in ps.stdout, f"child PID {child_pid} not alive:\n{ps.stdout}"

                # ---- 6) Sandbox rejection ----
                print("\n# ---- sandbox rejection ----", flush=True)
                t = await call(s, "qt_creator_open", expect_error=True,
                               pro_file=r"D:\outside\foo.pro")
                assert "sandbox" in t.lower() or "outside" in t.lower(), t

                # ---- 7) Build-only mode (run_after_build=False) ----
                print("\n# ---- build-only mode ----", flush=True)
                t = await call(s, "qt_creator_run",
                               project_dir=str(proj),
                               run_after_build=False, wait_for_build=90)
                assert "build" in t.lower(), t
                # No app should have been launched this time.
                assert "App launched" not in t, t

                # ---- 8) Clean up: kill the app, leave Qt Creator running for future demos ----
                print("\n# ---- cleanup ----", flush=True)
                subprocess.run(["taskkill", "/F", "/PID", str(child_pid)],
                               capture_output=True, text=True)
                print(f"  -> killed child app PID {child_pid}")
                # Leave Qt Creator running on purpose: the user wants to switch back
                # to either path at any time, and a warm Qt Creator is the fast case.

        print("\n=== CREATOR TOOLS E2E PASSED ===")
        return 0
    finally:
        if not keep_on_failure["v"]:
            try:
                shutil.rmtree(work, ignore_errors=True)
            except Exception:
                pass


def textwrap_indent(s: str, prefix: str) -> str:
    return "\n".join(prefix + ln for ln in s.splitlines())


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
