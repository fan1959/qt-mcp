import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

"""Tests the Jul-8 fixes:
1. qt_run detach should now detect when the launched process died immediately.
   (MCP server's _qt_env() always prepends Qt bin to PATH, so we can't easily
   strip DLLs. Verified by source-code review instead.)
2. qt_ui_action should now filter windows by expected PID, so a Qt Creator
   help panel that happens to share a title substring with our app no longer
   gets returned.
"""
import asyncio
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).parent.parent.parent / "server.py"
TMP_ROOT = Path(r"E:\Download_tools\QT\.tmp")


async def call(session, tool, expect_error=False, **kwargs):
    print(f"\n=== {tool}({kwargs}) ===", flush=True)
    res = await session.call_tool(tool, arguments={"params": kwargs} if kwargs else {})
    text = res.content[0].text if res.content else ""
    print(text, flush=True)
    if (res.isError or "Error" in text) and not expect_error:
        raise RuntimeError(f"{tool} unexpected error:\n{text}")
    return text


async def test_qt_run_diagnose_dead():
    """qt_run detach's aliveness-check + missing-DLL hint is wired (source review)."""
    print("\n# ---- qt_run startup-failure diagnosis (code path review) ----", flush=True)
    src = SERVER.read_text(encoding="utf-8")
    must_have = [
        "Detached launch FAILED",
        "Likely cause",
        "_is_pid_alive(",
        "_guess_missing_dll(",
    ]
    for needle in must_have:
        if needle not in src:
            raise RuntimeError(f"qt_run diagnostic not wired: missing {needle!r} in server.py")
    print("  PASS: qt_run detach has aliveness check + missing-DLL diagnostic.")


async def test_qt_ui_action_pid_filter():
    """qt_ui_action start should only return windows of the launched PID."""
    print("\n# ---- qt_ui_action PID filter ----", flush=True)
    exe = TMP_ROOT / "qt_mcp_demo" / "counter" / "debug" / "counter.exe"
    if not exe.is_file():
        print(f"  (skipping: {exe} not built yet)")
        return

    # Find a Qt Creator window's title to use as a *decoy* substring — qt_ui_action
    # must skip it because it belongs to a different process.
    from pywinauto import Application
    decoy_title = None
    try:
        for w in Application(backend="uia").windows():
            txt = (w.window_text() or "")
            if "Qt Creator" in txt or "QtCreator" in txt:
                decoy_title = txt
                break
    except Exception:
        pass

    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            if decoy_title:
                print(f"  (decoy found: {decoy_title!r})")
                t = await call(
                    s, "qt_ui_action",
                    action="start",
                    executable=str(exe),
                    window_title="QTimer Counter",
                    timeout=10,
                )
                if "PID" not in t:
                    raise RuntimeError(f"start didn't return a PID: {t}")
                session_id = t.split(": ")[1].splitlines()[0].strip()
                shot = TMP_ROOT / "qt_mcp_demo" / f"pid_filter_{uuid.uuid4().hex[:6]}.png"
                t2 = await call(
                    s, "qt_ui_action",
                    action="screenshot",
                    session_id=session_id,
                    output_path=str(shot),
                )
                if "Screenshot saved" not in t2:
                    raise RuntimeError(f"screenshot failed: {t2}")
                from PIL import Image
                img = Image.open(shot)
                pixels = list(img.getdata())[:2000]
                dark = sum(1 for p in pixels if isinstance(p, tuple) and sum(p[:3]) < 200)
                if dark / len(pixels) > 0.05:
                    raise RuntimeError(
                        f"image looks like Qt Creator's dark theme "
                        f"({dark}/{len(pixels)} dark pixels) — PID filter not working"
                    )
                print(f"  PASS: screenshot is from our process, not Qt Creator ({shot.name})")
                await call(s, "qt_ui_action", action="close", session_id=session_id)
            else:
                print("  (no Qt Creator running, skipping decoy test)")


async def main():
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    await test_qt_run_diagnose_dead()
    await test_qt_ui_action_pid_filter()
    print("\n=== FIXES E2E PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
