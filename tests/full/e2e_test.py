r"""Extended end-to-end test: covers the upgraded toolchain.

- qt_scaffold generic_game
- qt_build
- qt_run detach + verify the process is alive
- qt_kill_exe
- qt_gen_qrc (no real images, but should generate an empty-ish XML file or error gracefully)
- qt_clean

All scratch directories live under E:\Download_tools\QT\.tmp\ so the test never
writes outside the QT sandbox.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import asyncio
import shutil
import sys
import uuid
from pathlib import Path

# Force UTF-8 stdout so Windows GBK doesn't choke on Unicode from tool output.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


SERVER = Path(__file__).parent.parent.parent / "server.py"
SANDBOX = Path(r"E:\Download_tools\QT").resolve()
TMP_ROOT = SANDBOX / ".tmp"


async def call(session: ClientSession, tool_name: str, **kwargs) -> str:
    print(f"\n=== {tool_name}({kwargs}) ===", flush=True)
    res = await session.call_tool(tool_name, arguments={"params": kwargs} if kwargs else {})
    text = res.content[0].text if res.content else ""
    print(text, flush=True)
    if res.isError:
        raise RuntimeError(f"{tool_name} failed")
    return text


async def is_process_alive(image_name: str) -> bool:
    """Cross-check via Windows tasklist that the launched exe is actually running."""
    # Use cmd /c to defeat Git-Bash mangling of /FI into a path.
    proc = await asyncio.create_subprocess_exec(
        "cmd", "/c", "tasklist", "/FI", f"IMAGENAME eq {image_name}",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return image_name.lower() in stdout.decode("utf-8", errors="replace").lower()


async def main() -> int:
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    workdir = TMP_ROOT / f"e2e_{uuid.uuid4().hex[:8]}"
    workdir.mkdir(parents=True, exist_ok=True)
    proj = workdir / "mygame"
    print(f"Workdir: {workdir}")

    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # 1) generic_game scaffold -> should produce game/ + view/ + resources/ dirs
                await call(session, "qt_scaffold",
                          name="mygame", template="generic_game", output_dir=str(proj))

                for sub in ("game", "view", "resources"):
                    assert (proj / sub).is_dir(), f"missing {sub}/"
                for src in ("game/gamecontroller.cpp", "view/gameview.cpp",
                            "game/card.h", "game/player.h"):
                    assert (proj / src).is_file(), f"missing {src}"

                # 2) build
                await call(session, "qt_build",
                          project_dir=str(proj), build_type="debug", jobs=4, clean_first=False)

                exes = sorted(proj.rglob("*.exe"))
                assert exes, "no .exe built"
                exe = exes[0]
                image_name = exe.name

                # 3) detach run
                await call(session, "qt_run",
                          executable=str(exe), detach=True)

                await asyncio.sleep(2.5)
                alive = await is_process_alive(image_name)
                print(f"\n>>> Process alive check: {alive}")
                assert alive, f"{image_name} not running after detach"

                # 4) kill
                await call(session, "qt_kill_exe", image_name=image_name)

                await asyncio.sleep(1)
                alive2 = await is_process_alive(image_name)
                print(f"\n>>> Process alive after kill: {alive2}")
                assert not alive2, f"{image_name} still running after kill"

                # 5) qt_gen_qrc on the empty resources/ folder (should report none found, no crash)
                await call(session, "qt_gen_qrc",
                          images_dir=str(proj / "resources"),
                          output_qrc=str(proj / "resources" / "mygame.qrc"))

                # 6) clean + assert no build artifacts remain
                await call(session, "qt_clean", project_dir=str(proj))
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
                assert not leftovers, f"qt_clean left {len(leftovers)} artifacts: {leftovers[:5]}"
                for sub in ("debug", "release", "build"):
                    assert not (proj / sub).exists(), f"qt_clean left {sub}/ directory"
                # Source files we scaffolded must still exist
                assert (proj / "mygame.pro").is_file(), "qt_clean removed the .pro file"

        print("\n=== E2E PASSED ===")
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))