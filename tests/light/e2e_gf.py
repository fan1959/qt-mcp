"""End-to-end test for the game_framework scaffold.

- qt_scaffold game_framework
- qt_build (compile the whole framework + both reference games)
- qt_run detach
- qt_kill_exe
- qt_clean
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import asyncio, shutil, sys, uuid
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).parent.parent.parent / "server.py"
TMP_ROOT = Path(r"E:\Download_tools\QT\.tmp")


async def call(session, tool, **kwargs):
    print(f"\n=== {tool}({kwargs}) ===", flush=True)
    res = await session.call_tool(tool, arguments={"params": kwargs} if kwargs else {})
    text = res.content[0].text if res.content else ""
    if res.isError:
        print(text, flush=True)
        raise RuntimeError(f"{tool} failed")
    return text


async def main():
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    work = TMP_ROOT / f"e2e_gf_{uuid.uuid4().hex[:8]}"
    proj = work / "mygame"
    print(f"Workdir: {work}")

    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    try:
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()

                # 1) Scaffold
                await call(s, "qt_scaffold",
                          name="mygame", template="game_framework", output_dir=str(proj))

                # Sanity check: the new files exist.
                expected = [
                    "mygame.pro", "main.cpp", "mygamewindow.h", "mygamewindow.cpp", "mygamewindow.ui",
                    "game/gamestate.h", "game/gameaction.h", "game/player.h",
                    "game/aiplayer.h", "game/aiplayer.cpp",
                    "game/gamecontroller.h", "game/gamecontroller.cpp",
                    "game/games/higherlower.h", "game/games/higherlower.cpp",
                    "game/games/guessnumber.h", "game/games/guessnumber.cpp",
                    "view/gameview.h", "view/gameview.cpp",
                    "view/gridwidget.h", "view/gridwidget.cpp",
                    "view/cardwidget.h", "view/cardwidget.cpp",
                ]
                for f in expected:
                    assert (proj / f).is_file(), f"missing generated file: {f}"

                # 2) Build
                try:
                    build_text = await call(s, "qt_build",
                              project_dir=str(proj), build_type="debug", jobs=4, clean_first=False)
                except RuntimeError as e:
                    print(f"BUILD FAILED, last output:\n{e}", flush=True)
                    # show debug dir contents
                    print("\n>>> Files in proj:", flush=True)
                    for p in sorted(proj.rglob("*")):
                        if p.is_file():
                            print(f"  {p.relative_to(proj)}", flush=True)
                    raise

                exes = sorted(proj.rglob("*.exe"))
                assert exes, f"no .exe produced. Build output: {build_text}"
                exe = exes[0]

                # 3) Detach
                await call(s, "qt_run", executable=str(exe), detach=True)

                # 4) Kill
                await call(s, "qt_kill_exe", image_name=exe.name)

                # 5) Clean + assert no build artifacts remain
                await call(s, "qt_clean", project_dir=str(proj))
                leftovers = (
                    list(proj.rglob("*.o"))
                    + list(proj.rglob("*.obj"))
                    + list(proj.rglob("*.exe"))
                    + list(proj.rglob("Makefile*"))
                    + list(proj.rglob("*.qmake.stash"))
                    + list(proj.rglob("ui_*.h"))
                    + list(proj.rglob("moc_*.cpp"))
                    + list(proj.rglob("moc_*.obj"))
                )
                assert not leftovers, f"qt_clean left {len(leftovers)} artifacts in game_framework: {leftovers[:5]}"
                for sub in ("debug", "release", "build"):
                    assert not (proj / sub).exists(), f"qt_clean left {sub}/ directory in game_framework"
                # Source files we scaffolded must still exist
                assert (proj / "mygame.pro").is_file(), "qt_clean removed the .pro file"
                assert (proj / "game" / "gamecontroller.h").is_file(), "qt_clean removed game/gamecontroller.h"

        print("\n=== E2E FRAMEWORK PASSED ===")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))