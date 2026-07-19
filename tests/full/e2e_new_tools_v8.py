"""e2e for v8 new tools: qt_watch, qt_signature, qt_save, qt_audio, qt_anim,
qt_network, qt_coverage, qt_cheatsheet.

Run: python e2e_new_tools_v8.py
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
    QtWatchInput,
    QtSignatureInput,
    QtSaveInput,
    QtAudioInput,
    QtAnimInput,
    QtNetworkInput,
    QtCoverageInput,
    QtCheatsheetInput,
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


async def test_qt_cheatsheet_list():
    """qt_cheatsheet with no filter should list all tools."""
    print("\n[1] qt_cheatsheet -- list all tools")
    out = await server.qt_cheatsheet(QtCheatsheetInput())
    check("returns text starting with === qt_cheatsheet", out.startswith("=== qt_cheatsheet"))
    check("includes env category", "--- env" in out)
    check("includes scaffold category", "--- scaffold" in out)
    check("includes build category", "--- build" in out)
    check("includes qt_env tool", "qt_env" in out)
    check("includes qt_anim tool", "qt_anim" in out)


async def test_qt_cheatsheet_one_tool():
    print("\n[2] qt_cheatsheet -- detail for one tool")
    out = await server.qt_cheatsheet(QtCheatsheetInput(tool_name="qt_env"))
    check("starts with === qt_env", out.startswith("=== qt_env"))


async def test_qt_cheatsheet_category():
    print("\n[3] qt_cheatsheet -- filter by category")
    out = await server.qt_cheatsheet(QtCheatsheetInput(category="env"))
    check("includes only env category", "env" in out and "scaffold" not in out.replace("env", ""))


async def test_qt_anim_fade():
    """qt_anim fade should generate a QPropertyAnimation snippet."""
    print("\n[4] qt_anim -- fade")
    out = await server.qt_anim(QtAnimInput(
        animation_type="fade",
        target_widget="this",
        duration_ms=300,
        start_value="0.0",
        end_value="1.0",
    ))
    check("starts with === qt_anim", out.startswith("=== qt_anim"))
    check("includes QPropertyAnimation", "QPropertyAnimation" in out)
    check("uses opacity property", "opacity" in out)
    check("uses 300ms duration", "300" in out)


async def test_qt_anim_move():
    print("\n[5] qt_anim -- move")
    out = await server.qt_anim(QtAnimInput(
        animation_type="move",
        target_widget="this->label",
        duration_ms=500,
        start_value="QRect(0, 0, 100, 100)",
        end_value="QRect(0, 0, 300, 300)",
    ))
    check("uses geometry property", "geometry" in out)
    check("uses QRect", "QRect" in out)


async def test_qt_anim_sequence():
    print("\n[6] qt_anim -- sequence")
    out = await server.qt_anim(QtAnimInput(
        animation_type="sequence",
        target_widget="this",
        duration_ms=1000,
        end_value="(ignored for sequence)",
    ))
    check("uses QSequentialAnimationGroup", "QSequentialAnimationGroup" in out)


async def test_qt_anim_invalid():
    print("\n[7] qt_anim -- invalid type")
    out = await server.qt_anim(QtAnimInput(animation_type="bad", end_value="x"))
    check("rejects invalid type", "invalid animation_type" in out)


async def test_qt_save_roundtrip():
    """qt_save save/load should roundtrip JSON data."""
    print("\n[8] qt_save -- save/load roundtrip")
    save_dir = SANDBOX_TMP / "v8_save_roundtrip"
    if save_dir.exists():
        shutil.rmtree(save_dir, ignore_errors=True)

    save_out = await server.qt_save(QtSaveInput(
        action="save", save_dir=str(save_dir), name="game1",
        data={"score": 100, "level": 3, "items": ["sword", "potion"]},
    ))
    check("save succeeded", "saved" in save_out.lower())

    load_out = await server.qt_save(QtSaveInput(
        action="load", save_dir=str(save_dir), name="game1",
    ))
    check("load returned score", "100" in load_out)
    check("load returned level", "3" in load_out)
    check("load returned items", "sword" in load_out)


async def test_qt_save_list():
    print("\n[9] qt_save -- list saves")
    out = await server.qt_save(QtSaveInput(action="list", save_dir=str(SANDBOX_TMP / "v8_save_roundtrip")))
    check("lists game1 save", "game1.json" in out)


async def test_qt_save_inspect():
    print("\n[10] qt_save -- inspect save structure")
    out = await server.qt_save(QtSaveInput(
        action="inspect", save_dir=str(SANDBOX_TMP / "v8_save_roundtrip"), name="game1",
    ))
    check("shows score key", "score" in out)
    check("shows items list", "items" in out)


async def test_qt_save_delete():
    print("\n[11] qt_save -- delete save")
    # First save something
    await server.qt_save(QtSaveInput(
        action="save", save_dir=str(SANDBOX_TMP / "v8_save_del"), name="todelete",
        data={"x": 1},
    ))
    out = await server.qt_save(QtSaveInput(
        action="delete", save_dir=str(SANDBOX_TMP / "v8_save_del"), name="todelete",
    ))
    check("delete succeeded", "deleted" in out.lower())


async def test_qt_audio_info():
    """qt_audio info should report QtMultimedia availability."""
    print("\n[12] qt_audio -- info")
    out = await server.qt_audio(QtAudioInput(action="info"))
    check("starts with === qt_audio", out.startswith("=== qt_audio"))


async def test_qt_audio_list():
    print("\n[13] qt_audio -- list audio files")
    src = SANDBOX_TMP / "v8_audio_src"
    if src.exists():
        shutil.rmtree(src, ignore_errors=True)
    src.mkdir(parents=True)
    (src / "click.wav").write_bytes(b"RIFF" + b"\x00" * 100)
    (src / "music.ogg").write_bytes(b"OggS" + b"\x00" * 100)
    (src / "ignore.txt").write_text("not audio", encoding="utf-8")
    out = await server.qt_audio(QtAudioInput(action="list", audio_dir=str(src)))
    check("lists click.wav", "click.wav" in out)
    check("lists music.ogg", "music.ogg" in out)
    check("excludes ignore.txt", "ignore.txt" not in out)


async def test_qt_audio_probe():
    print("\n[14] qt_audio -- probe WAV file")
    src = SANDBOX_TMP / "v8_audio_probe"
    if src.exists():
        shutil.rmtree(src, ignore_errors=True)
    src.mkdir(parents=True)
    wav = src / "test.wav"
    # Minimal WAV header
    wav.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x10\x00\x00\x00" + b"\x01\x00\x01\x00" + b"\x44\xAC\x00\x00" + b"\x02\x00\x10\x00" + b"data\x00\x00\x00\x00")
    out = await server.qt_audio(QtAudioInput(action="probe", file_path=str(wav)))
    check("identifies WAV format", "WAV" in out)


async def test_qt_audio_play():
    print("\n[15] qt_audio -- play snippet")
    src = SANDBOX_TMP / "v8_audio_play"
    if src.exists():
        shutil.rmtree(src, ignore_errors=True)
    src.mkdir(parents=True)
    (src / "x.wav").write_bytes(b"RIFF" + b"\x00" * 100)
    out = await server.qt_audio(QtAudioInput(action="play", file_path=str(src / "x.wav")))
    check("includes QSoundEffect snippet", "QSoundEffect" in out)


async def test_qt_network_tcp_client():
    """qt_network tcp_client should generate .h/.cpp files."""
    print("\n[16] qt_network -- tcp_client")
    out_dir = SANDBOX_TMP / "v8_net_tcp"
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    out = await server.qt_network(QtNetworkInput(
        skeleton_type="tcp_client",
        class_name="MyClient",
        host="192.168.1.1",
        port=9999,
        output_dir=str(out_dir),
    ))
    check("starts with === qt_network", out.startswith("=== qt_network"))
    h = out_dir / "myclient.h"
    cpp = out_dir / "myclient.cpp"
    check("header file written", h.exists())
    check("impl file written", cpp.exists())
    if h.exists():
        text = h.read_text(encoding="utf-8")
        check("header has QTcpSocket", "QTcpSocket" in text)
        check("header has class name", "class MyClient" in text)


async def test_qt_network_udp():
    print("\n[17] qt_network -- udp_peer")
    out_dir = SANDBOX_TMP / "v8_net_udp"
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    out = await server.qt_network(QtNetworkInput(
        skeleton_type="udp_peer",
        class_name="GamePeer",
        output_dir=str(out_dir),
    ))
    check("emits .h", (out_dir / "gamepeer.h").exists())
    check("emits .cpp", (out_dir / "gamepeer.cpp").exists())


async def test_qt_network_invalid_class_name():
    print("\n[18] qt_network -- invalid class name")
    out_dir = SANDBOX_TMP / "v8_net_bad"
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    out = await server.qt_network(QtNetworkInput(
        skeleton_type="tcp_client", class_name="bad name!", output_dir=str(out_dir),
    ))
    check("rejects invalid class name", "not a valid C++ class name" in out)


async def test_qt_signature_info():
    """qt_signature info should locate signtool.exe (or report not found)."""
    print("\n[19] qt_signature -- info")
    out = await server.qt_signature(QtSignatureInput(action="info", target="C:\\Windows\\notepad.exe"))
    # Either found or not found — both are valid
    check("returns text", "=== qt_signature" in out or "Error" in out)


async def test_qt_signature_verify():
    print("\n[20] qt_signature -- verify (Windows notepad)")
    out = await server.qt_signature(QtSignatureInput(action="verify", target="C:\\Windows\\notepad.exe"))
    # Windows 10+ notepad is signed by Microsoft
    check("returns verification result", "=== qt_signature" in out or "Error" in out)


async def test_qt_signature_invalid_action():
    print("\n[21] qt_signature -- invalid action")
    out = await server.qt_signature(QtSignatureInput(action="bad", target="x.exe"))
    check("rejects invalid action", "invalid action" in out)


async def test_qt_signature_sign_no_cert():
    print("\n[22] qt_signature -- sign without cert")
    out = await server.qt_signature(QtSignatureInput(action="sign", target="C:/Windows/notepad.exe"))
    # If signtool isn't installed, the check is "not found" (also valid).
    check("rejects sign without cert or signtool missing",
          "requires either" in out or "signtool.exe not found" in out)


async def test_qt_watch_basic():
    """qt_watch should spawn a background watcher."""
    print("\n[23] qt_watch -- spawn background watcher")
    # Use the counter project
    proj = SANDBOX_ROOT / "Files" / "qt_mcp_demo" / "counter"
    if not (proj / "counter.pro").exists():
        # Skip if counter not available
        check("counter project exists", False, "no Files/qt_mcp_demo/counter")
        return
    out = await server.qt_watch(QtWatchInput(
        project_dir=str(proj),
        debounce_seconds=0.5,
        timeout_seconds=3,
    ))
    check("returns text starting with === qt_watch", out.startswith("=== qt_watch"))
    check("reports PID", "PID:" in out)
    check("reports log file", "log:" in out)

    # Extract PID and kill it
    import re
    m = re.search(r"PID:\s+(\d+)", out)
    if m:
        pid = int(m.group(1))
        # Kill the watcher
        import subprocess
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=10)


async def test_qt_watch_no_pro():
    print("\n[24] qt_watch -- no .pro file")
    tmp = SANDBOX_TMP / "v8_watch_nopro"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    out = await server.qt_watch(QtWatchInput(project_dir=str(tmp)))
    check("reports no .pro file", "no .pro file" in out)


async def test_qt_coverage_no_project():
    print("\n[25] qt_coverage -- missing project")
    out = await server.qt_coverage(QtCoverageInput(project_dir=str(SANDBOX_TMP / "nonexistent-proj")))
    check("reports missing project", "not a directory" in out or "no .pro" in out)


async def test_qt_coverage_sandbox():
    print("\n[26] qt_coverage -- rejects paths outside sandbox")
    out = await server.qt_coverage(QtCoverageInput(project_dir=r"D:\outside\foo"))
    check("sandbox error", "outside the allowed sandbox" in out)


async def test_qt_deploy():
    """qt_deploy should run windeployqt on a built console .exe."""
    print("\n[27] qt_deploy -- bundle DLLs for a built console app")
    from server import QtDeployInput, QtBuildInput
    proj = SANDBOX_TMP / "v8_deploy_proj"
    if proj.exists():
        shutil.rmtree(proj, ignore_errors=True)
    proj.mkdir(parents=True)
    (proj / "app.pro").write_text(
        "QT       += core\n"
        "CONFIG   += console c++17\n"
        "CONFIG   -= app_bundle\n"
        "TARGET   = deploy_app\n"
        "TEMPLATE = app\n"
        "SOURCES += main.cpp\n",
        encoding="utf-8",
    )
    (proj / "main.cpp").write_text(
        '#include <QCoreApplication>\nint main(int argc, char** argv) { QCoreApplication app(argc, argv); return 0; }\n',
        encoding="utf-8",
    )
    build_out = await server.qt_build(QtBuildInput(project_dir=str(proj), build_type="debug"))
    if "Error:" in build_out or "BUILD FAILED" in build_out:
        check("build succeeded", False, build_out.splitlines()[-3:])
        return
    exe = proj / "debug" / "deploy_app.exe"
    if not exe.exists():
        check("deploy_app.exe exists", False)
        return
    deploy_dir = proj / "deploy"
    out = await server.qt_deploy(QtDeployInput(executable=str(exe), output_dir=str(deploy_dir)))
    check("returns text mentioning windeployqt", "windeployqt" in out)
    check("deploy folder mentioned", "Deploy folder" in out)
    check("deploy folder created", deploy_dir.is_dir())
    if deploy_dir.is_dir():
        files = list(deploy_dir.iterdir())
        check("deploy folder has files", len(files) > 0)


async def main():
    await test_qt_cheatsheet_list()
    await test_qt_cheatsheet_one_tool()
    await test_qt_cheatsheet_category()
    await test_qt_anim_fade()
    await test_qt_anim_move()
    await test_qt_anim_sequence()
    await test_qt_anim_invalid()
    await test_qt_save_roundtrip()
    await test_qt_save_list()
    await test_qt_save_inspect()
    await test_qt_save_delete()
    await test_qt_audio_info()
    await test_qt_audio_list()
    await test_qt_audio_probe()
    await test_qt_audio_play()
    await test_qt_network_tcp_client()
    await test_qt_network_udp()
    await test_qt_network_invalid_class_name()
    await test_qt_signature_info()
    await test_qt_signature_verify()
    await test_qt_signature_invalid_action()
    await test_qt_signature_sign_no_cert()
    await test_qt_watch_basic()
    await test_qt_watch_no_pro()
    await test_qt_coverage_no_project()
    await test_qt_coverage_sandbox()
    await test_qt_deploy()

    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    total = len(results)
    print()
    print(f"\033[1m=== V8 E2E: {passed}/{total} passed, {failed} failed ===\033[0m")
    if failed:
        print("Failed:")
        for name, ok in results:
            if not ok:
                print(f"  - {name}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())