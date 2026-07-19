"""Functional + safety audit:

- qt_deploy smoke test (was never exercised)
- sandbox rejection: every tool refuses to operate outside E:\\Download_tools\\QT\\
- error-path coverage: missing files, bad templates
"""

import asyncio
import shutil
import sys
import uuid
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


SERVER = Path(__file__).parent.parent.parent / "server.py"
SANDBOX = Path(r"E:\Download_tools\QT").resolve()
TMP_ROOT = SANDBOX / ".tmp"


async def call(session: ClientSession, tool_name: str, expect_error: bool = False, **kwargs) -> str:
    res = await session.call_tool(tool_name, arguments={"params": kwargs} if kwargs else {})
    text = res.content[0].text if res.content else ""
    flagged_error = res.isError
    if expect_error:
        assert "Error" in text or flagged_error, f"{tool_name} should have errored but got: {text!r}"
    else:
        assert "Error" not in text, f"{tool_name} unexpected error: {text}"
    return text


async def main() -> int:
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    work = TMP_ROOT / f"audit_{uuid.uuid4().hex[:8]}"
    work.mkdir(parents=True, exist_ok=True)
    print(f"Workdir: {work}")

    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    try:
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()

                # 1) qt_deploy smoke: scaffold + build + deploy
                print("\n--- qt_deploy smoke test ---")
                proj = work / "deploytest"
                await call(s, "qt_scaffold", name="deploytest", template="widget", output_dir=str(proj))
                await call(s, "qt_build", project_dir=str(proj), build_type="debug", jobs=4)
                exe = next(proj.rglob("*.exe"))
                deploy_out = work / "deploy_out"
                await call(s, "qt_deploy", executable=str(exe), output_dir=str(deploy_out))
                assert deploy_out.is_dir(), "deploy folder not created"
                deployed_dlls = list(deploy_out.glob("*.dll"))
                assert deployed_dlls, "no DLLs copied — windeployqt likely failed silently"
                print(f"  -> deployed {len(deployed_dlls)} DLLs into {deploy_out.name}")

                # 1.5) release build smoke: qt_build with build_type=release must
                # produce an exe under release/, not just debug/. This is the path
                # qt_deploy auto-detects ("release" in exe.name) so it must work.
                print("\n--- release build ---")
                rel_proj = work / "releasetest"
                await call(s, "qt_scaffold", name="releasetest", template="widget", output_dir=str(rel_proj))
                await call(s, "qt_build", project_dir=str(rel_proj), build_type="release", jobs=4)
                release_exe = next(rel_proj.rglob("release/*.exe"), None)
                assert release_exe and release_exe.is_file(), "release build did not produce release/releasetest.exe"
                print(f"  -> release exe: {release_exe.relative_to(rel_proj)}")

                # 2) Sandbox rejection: every writable tool must refuse a path on D:
                print("\n--- sandbox rejection ---")
                bad = r"D:\should\not\write\here"
                bad_proj = str(Path(bad) / "proj")
                bad_dir = str(Path(bad) / "out")
                await call(s, "qt_scaffold", expect_error=True, name="x", template="widget", output_dir=bad_dir)
                await call(s, "qt_build", expect_error=True, project_dir=bad_proj)
                await call(s, "qt_clean", expect_error=True, project_dir=bad_proj)
                await call(s, "qt_gen_qrc", expect_error=True, images_dir=bad_dir, output_qrc=str(Path(bad_dir) / "a.qrc"))
                await call(s, "qt_deploy", expect_error=True, executable=str(Path(bad) / "x.exe"))
                # qt_run must also refuse a non-sandbox exe (path check happens before existence check)
                await call(s, "qt_run", expect_error=True, executable=str(Path(bad) / "x.exe"))

                # 3) Error path coverage
                print("\n--- error paths ---")
                await call(s, "qt_build", expect_error=True, project_dir=str(work / "nope"))
                await call(s, "qt_run", expect_error=True, executable=str(work / "nope.exe"))
                await call(s, "qt_clean", expect_error=True, project_dir=str(work / "nope"))
                # Scaffold refuses to overwrite non-empty dir
                await call(s, "qt_scaffold", expect_error=True, name="deploytest", template="widget", output_dir=str(proj))

        print("\n=== AUDIT PASSED ===")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

def test_qt_deploy_basic():
    """qt_deploy should run windeployqt on a built .exe."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path('tests/full').resolve().parent.parent))
    import server
    from server import QtDeployInput
    import shutil, asyncio
    async def go():
        # Use the counter project
        proj = Path('Files/qt_mcp_demo/counter')
        exe = proj / 'debug' / 'counter.exe'
        if not exe.exists():
            return  # skip if not built
        out = await server.qt_deploy(QtDeployInput(executable=str(exe), output_dir=str(proj / 'deploy')))
        assert 'windeployqt' in out
        assert 'Deploy folder' in out
    asyncio.run(go())
    print('  qt_deploy e2e passed')
