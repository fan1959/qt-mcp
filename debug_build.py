"""Minimal scaffold + build to inspect compile errors."""
import asyncio, shutil, sys, uuid
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).parent / "server.py"
TMP_ROOT = Path(r"E:\Download_tools\QT\.tmp")

async def main():
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    workdir = TMP_ROOT / f"dbg_{uuid.uuid4().hex[:8]}"
    workdir.mkdir(parents=True, exist_ok=True)
    proj = workdir / "mygame"
    try:
        params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await session.call_tool("qt_scaffold", arguments={"params": {
                    "name": "mygame", "template": "generic_game", "output_dir": str(proj)
                }})
                # Print generated gamecontroller.h
                print("==== game/gamecontroller.h ====")
                print((proj / "game" / "gamecontroller.h").read_text())
                print()
                print("==== view/gameview.cpp (head) ====")
                print((proj / "view" / "gameview.cpp").read_text()[:2000])
                print()
                print("==== mygame.pro ====")
                print((proj / "mygame.pro").read_text())
                # Try build with verbose logging
                res = await session.call_tool("qt_build", arguments={"params": {
                    "project_dir": str(proj), "build_type": "debug", "jobs": 2, "clean_first": False
                }})
                print("==== build result ====")
                print(res.content[0].text)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

asyncio.run(main())