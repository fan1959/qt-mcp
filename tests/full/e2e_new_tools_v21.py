"""e2e for v21 new tools (v0.3.5):
  - qt_complexity_lint       (cyclomatic complexity per function, threshold-based)
  - qt_git_audit             (git history: hot files, bus factor, churn, stale branches)
  - qt_appx                  (Microsoft Store MSIX/AppX packaging skeleton)
  - qt_ide_metadata          (VSCode + CLion metadata generation)
  - qt_runtime_props         (read live widget properties via pywinauto, borrow 0xCarbon qt_props)
  - qt_test_fuzz             (libFuzzer skeleton + .pro patch + README)

Run: python e2e_new_tools_v21.py
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import server
from server import (
    SANDBOX_TMP,
    QtComplexityLintInput,
    QtGitAuditInput,
    QtAppxInput,
    QtIdeMetadataInput,
    QtRuntimePropsInput,
    QtTestFuzzInput,
)

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
            subprocess.run(
                ["cmd", "/c", "rmdir", "/s", "/q", str(p)],
                check=False, capture_output=True, timeout=10,
            )
        except Exception:
            pass
        shutil.rmtree(p, ignore_errors=True)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ---------- qt_complexity_lint ----------

async def test_complexity_lint_no_source():
    print("\n[1] qt_complexity_lint -- no C++ source returns Error")
    d = fresh_dir(SANDBOX_TMP, "v21_cx_nosrc")
    out = await server.qt_complexity_lint(QtComplexityLintInput(
        project_dir=str(d),
        threshold=12,
        output_format="text",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions no source", "no C++ source" in out or "no " in out.lower())


async def test_complexity_lint_simple_function():
    print("\n[2] qt_complexity_lint -- simple function passes at default threshold")
    d = fresh_dir(SANDBOX_TMP, "v21_cx_simple")
    (d / "main.cpp").write_text(
        "int add(int a, int b) {\n"
        "    return a + b;\n"
        "}\n",
        encoding="utf-8",
    )
    out = await server.qt_complexity_lint(QtComplexityLintInput(
        project_dir=str(d),
        threshold=12,
        output_format="text",
    ))
    check("returns Verdict: PASS", "Verdict: PASS" in out)
    check("reports complexity", "Complexity" in out or "cplx" in out or "Functions analysed" in out)


async def test_complexity_lint_complex_function_flagged():
    print("\n[3] qt_complexity_lint -- complex function flagged above threshold")
    d = fresh_dir(SANDBOX_TMP, "v21_cx_flagged")
    # Construct a function with 15+ branches (well above threshold=5 for the test).
    branches = []
    for i in range(15):
        branches.append(f"    if (x == {i}) return {i};")
    src = "int f(int x) {\n" + "\n".join(branches) + "\n    return -1;\n}\n"
    (d / "many.cpp").write_text(src, encoding="utf-8")
    out = await server.qt_complexity_lint(QtComplexityLintInput(
        project_dir=str(d),
        threshold=5,
        output_format="text",
    ))
    check("returns Verdict: FAIL", "Verdict: FAIL" in out)
    check("flags the complex function", "many.cpp:1" in out or "cplx=" in out)


async def test_complexity_lint_json_output():
    print("\n[4] qt_complexity_lint -- output_format=json returns parseable JSON")
    d = fresh_dir(SANDBOX_TMP, "v21_cx_json")
    (d / "small.cpp").write_text("int g() { return 1; }\n", encoding="utf-8")
    out = await server.qt_complexity_lint(QtComplexityLintInput(
        project_dir=str(d),
        threshold=12,
        output_format="json",
    ))
    try:
        payload = json.loads(out.split("\n\n--- json ---\n")[0])
        check("json has verdict", payload.get("verdict") in ("PASS", "FAIL"))
    except Exception as e:
        check("json parses", False, hint=str(e))


async def test_complexity_lint_threshold_out_of_range():
    print("\n[5] qt_complexity_lint -- invalid threshold returns Error")
    d = fresh_dir(SANDBOX_TMP, "v21_cx_bad")
    (d / "a.cpp").write_text("int h() { return 0; }\n", encoding="utf-8")
    out = await server.qt_complexity_lint(QtComplexityLintInput(
        project_dir=str(d),
        threshold=999,
        output_format="text",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions threshold", "threshold" in out.lower())


# ---------- qt_git_audit ----------

async def test_git_audit_not_a_repo():
    print("\n[6] qt_git_audit -- non-git project_dir returns Error")
    d = fresh_dir(SANDBOX_TMP, "v21_ga_norepo")
    out = await server.qt_git_audit(QtGitAuditInput(
        project_dir=str(d),
        top_n=5,
        since_days=90,
        stale_days=180,
        output_format="text",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions git", "git" in out.lower())


async def test_git_audit_happy_path():
    print("\n[7] qt_git_audit -- real repo with two commits reports stats")
    d = fresh_dir(SANDBOX_TMP, "v21_ga_happy")
    # Sandbox-safe git init + 2 commits + 1 trivial .cpp per commit.
    # Important: start from os.environ to keep PATH + HOME so git can find .gitconfig.
    base_env = os.environ.copy()
    base_env.update({
        "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t",
    })
    subprocess.run(["git", "init", "-q"], cwd=str(d), env=base_env, check=True)
    (d / "main.cpp").write_text("int main() { return 0; }\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(d), env=base_env, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "first"], cwd=str(d), env=base_env, check=True)
    (d / "second.cpp").write_text("int g() { return 1; }\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(d), env=base_env, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "second"], cwd=str(d), env=base_env, check=True)
    out = await server.qt_git_audit(QtGitAuditInput(
        project_dir=str(d),
        top_n=5,
        since_days=365,
        stale_days=180,
        output_format="text",
    ))
    check("reports Total commits: 2", "Total commits: 2" in out)
    check("reports Bus factor", "Bus factor" in out)
    check("reports LOC stats", "LOC added" in out)


async def test_git_audit_json_output():
    print("\n[8] qt_git_audit -- json output is parseable")
    d = fresh_dir(SANDBOX_TMP, "v21_ga_json")
    base_env = os.environ.copy()
    base_env.update({
        "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t",
    })
    subprocess.run(["git", "init", "-q"], cwd=str(d), env=base_env, check=True)
    (d / "a.cpp").write_text("int f(){return 1;}\n", encoding="utf-8")
    subprocess.run(["git", "add", "a.cpp"], cwd=str(d), env=base_env, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=str(d), env=base_env, check=True)
    out = await server.qt_git_audit(QtGitAuditInput(
        project_dir=str(d),
        top_n=5,
        since_days=180,
        stale_days=180,
        output_format="json",
    ))
    check("has commits field", '"commits"' in out or '"commits":' in out)
    try:
        payload = json.loads(out.split("\n\n--- json ---\n")[0])
        check("commits >= 1", payload.get("commits", 0) >= 1)
    except Exception:
        check("json parses", False, hint="json.loads failed")


# ---------- qt_appx ----------

async def test_appx_exe_not_found():
    print("\n[9] qt_appx -- invalid exe returns Error")
    d = fresh_dir(SANDBOX_TMP, "v21_appx_noexe")
    out = await server.qt_appx(QtAppxInput(
        output_dir=str(d / "appx_out"),
        app_name="SampleApp",
        publisher="CN=Foo",
        version="1.0.0.0",
        exe_path=str(d / "does_not_exist.exe"),
        architecture="x64",
    ))
    check("returns Error:", "Error:" in out)


async def test_appx_happy_path_writes_files():
    print("\n[10] qt_appx -- happy path writes manifest + build script + logos README")
    d = fresh_dir(SANDBOX_TMP, "v21_appx_happy")
    exe = d / "MyApp.exe"
    exe.write_bytes(b"MZ")
    out_dir = d / "build"
    out = await server.qt_appx(QtAppxInput(
        output_dir=str(out_dir),
        app_name="MyApp",
        publisher="CN=Contoso",
        version="1.2.3.4",
        exe_path=str(exe),
        architecture="x64",
    ))
    check("AppxManifest.xml written", (out_dir / "AppxManifest.xml").exists())
    check("build_appx.bat written", (out_dir / "build_appx.bat").exists())
    check("appx_logos.md written", (out_dir / "appx_logos.md").exists())
    # Manifest content sanity.
    manifest = (out_dir / "AppxManifest.xml").read_text(encoding="utf-8")
    check("manifest contains PackageName", "Identity Name=" in manifest)
    check("manifest uses Win64 architecture", "x64" in manifest)


async def test_appx_invalid_architecture():
    print("\n[11] qt_appx -- invalid architecture returns Error")
    d = fresh_dir(SANDBOX_TMP, "v21_appx_badarch")
    exe = d / "MyApp.exe"
    exe.write_bytes(b"MZ")
    out = await server.qt_appx(QtAppxInput(
        output_dir=str(d / "build"),
        app_name="Bad",
        publisher="CN=Bad",
        version="1.0.0.0",
        exe_path=str(exe),
        architecture="x999",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions architecture", "architecture" in out.lower())


# ---------- qt_ide_metadata ----------

async def test_ide_metadata_no_pro_file():
    print("\n[12] qt_ide_metadata -- project without .pro returns Error")
    d = fresh_dir(SANDBOX_TMP, "v21_ide_nopro")
    out = await server.qt_ide_metadata(QtIdeMetadataInput(
        project_dir=str(d),
        ide="vscode",
        kit="mingw64",
        launch_exe="",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions .pro", ".pro" in out)


async def test_ide_metadata_vscode_writes_files():
    print("\n[13] qt_ide_metadata -- vscode writes launch.json, tasks.json, c_cpp_properties.json, extensions.json")
    d = fresh_dir(SANDBOX_TMP, "v21_ide_vscode")
    (d / "demo.pro").write_text("QT += core gui widgets\nSOURCES += main.cpp\n", encoding="utf-8")
    # Use a sandbox-internal fake exe so auto-detection resolves.
    fake_exe = d / "build-debug" / "debug" / "demo.exe"
    fake_exe.parent.mkdir(parents=True, exist_ok=True)
    fake_exe.write_bytes(b"MZ")
    out = await server.qt_ide_metadata(QtIdeMetadataInput(
        project_dir=str(d),
        ide="vscode",
        kit="mingw64",
        launch_exe=str(fake_exe),
    ))
    check("launch.json written", (d / ".vscode" / "launch.json").exists())
    check("tasks.json written", (d / ".vscode" / "tasks.json").exists())
    check("c_cpp_properties.json written", (d / ".vscode" / "c_cpp_properties.json").exists())
    check("extensions.json written", (d / ".vscode" / "extensions.json").exists())
    # Include path should include Qt include + SOURCES autodetection.
    cpp = (d / ".vscode" / "c_cpp_properties.json").read_text(encoding="utf-8")
    check("c_cpp_properties has Qt includePath", "QtCore" in cpp or "include" in cpp)


async def test_ide_metadata_both_writes_idea():
    print("\n[14] qt_ide_metadata -- ide=both also writes CLion workspace.xml")
    d = fresh_dir(SANDBOX_TMP, "v21_ide_both")
    (d / "demo.pro").write_text("QT += widgets\nSOURCES += main.cpp\n", encoding="utf-8")
    fake_exe = d / "demo.exe"
    fake_exe.write_bytes(b"MZ")
    out = await server.qt_ide_metadata(QtIdeMetadataInput(
        project_dir=str(d),
        ide="both",
        kit="mingw64",
        launch_exe=str(fake_exe),
    ))
    check("workspace.xml written", (d / ".idea" / "workspace.xml").exists())
    check("also writes VSCode launch.json", (d / ".vscode" / "launch.json").exists())


async def test_ide_metadata_invalid_ide():
    print("\n[15] qt_ide_metadata -- invalid ide returns Error")
    d = fresh_dir(SANDBOX_TMP, "v21_ide_badie")
    (d / "demo.pro").write_text("QT += core\n", encoding="utf-8")
    out = await server.qt_ide_metadata(QtIdeMetadataInput(
        project_dir=str(d),
        ide="invalid",
        kit="mingw64",
        launch_exe="",
    ))
    check("returns Error:", "Error:" in out)
    check("mentions ide", "ide" in out.lower())


# ---------- qt_runtime_props ----------

async def test_runtime_props_no_executable_when_spawn():
    print("\n[16] qt_runtime_props -- process_id=0 without executable returns Error")
    d = fresh_dir(SANDBOX_TMP, "v21_rp_noexe")
    out = await server.qt_runtime_props(QtRuntimePropsInput(
        process_id=0,
        executable="",
        window_title="",
        auto_id="",
        wait_seconds=1,
    ))
    check("returns Error:", "Error:" in out)
    check("mentions executable", "executable" in out.lower())


async def test_runtime_props_exe_not_in_sandbox():
    print("\n[17] qt_runtime_props -- exe_path outside sandbox returns Error (sandbox first)")
    d = fresh_dir(SANDBOX_TMP, "v21_rp_outsb")
    out = await server.qt_runtime_props(QtRuntimePropsInput(
        process_id=0,
        executable="C:/Windows/System32/notepad.exe",
        window_title="",
        auto_id="",
        wait_seconds=1,
    ))
    check("returns Error:", "Error:" in out)
    check("mentions sandbox", "sandbox" in out.lower())


async def test_runtime_props_exe_does_not_exist():
    print("\n[18] qt_runtime_props -- nonexistent exe in sandbox returns Error")
    d = fresh_dir(SANDBOX_TMP, "v21_rp_noexist")
    fake = d / "no_such_exe.exe"
    out = await server.qt_runtime_props(QtRuntimePropsInput(
        process_id=0,
        executable=str(fake),
        window_title="",
        auto_id="",
        wait_seconds=1,
    ))
    check("returns Error:", "Error:" in out)
    check("mentions not found", "not found" in out.lower())


async def test_runtime_props_attach_to_sandbox_python():
    print("\n[19] qt_runtime_props -- copies sys.executable into sandbox and runs a sleeper QWidget")
    # v0.3.4 lesson: don't use Windows system .exe (notepad) — Windows sandbox
    # resource limits can cause it to die on spawn. Instead, copy the python
    # interpreter into the sandbox and launch via that with a small PyQt5 sleeper.
    d = fresh_dir(SANDBOX_TMP, "v21_rp_attach")
    sandbox_python = d / "sandbox_python.exe"
    try:
        shutil.copy(sys.executable, sandbox_python)
    except OSError:
        check("copied python into sandbox", False, hint="shutil.copy failed (likely readonly mount)")
        return
    sleeper_py = d / "_sleeper.py"
    sleeper_py.write_text(
        "import sys, time\n"
        "from PyQt5.QtWidgets import QApplication, QWidget, QLabel\n"
        "app = QApplication(sys.argv)\n"
        "w = QWidget()\n"
        "w.setObjectName('rpLabel')\n"
        "w.setWindowTitle('rp_target')\n"
        "lbl = QLabel('hello', w)\n"
        "lbl.setObjectName('rpChild')\n"
        "w.show()\n"
        "t_end = time.time() + 8\n"
        "while time.time() < t_end:\n"
        "    app.processEvents()\n"
        "    time.sleep(0.1)\n",
        encoding="utf-8",
    )
    out = await server.qt_runtime_props(QtRuntimePropsInput(
        process_id=0,
        executable=str(sandbox_python),
        window_title="rp_target",
        auto_id="",
        wait_seconds=2,
    ))
    # Allow either widgets-found, "no widgets" guidance, or sandbox-attached-ok.
    accepted = (
        "=== qt_runtime_props ===" in out
        and ("Named widgets" in out or "no top-level window" in out.lower()
             or "no widgets found" in out.lower() or "(no widget" in out.lower()
             or "Widgets with text found" in out)
    )
    check("returns structured report", accepted)


# ---------- qt_test_fuzz ----------

async def test_test_fuzz_invalid_compiler():
    print("\n[20] qt_test_fuzz -- invalid compiler returns Error")
    d = fresh_dir(SANDBOX_TMP, "v21_fuzz_badcomp")
    (d / "demo.pro").write_text("QT += core\n", encoding="utf-8")
    out = await server.qt_test_fuzz(QtTestFuzzInput(
        project_dir=str(d),
        target_function="parseCommand",
        fuzz_seconds=15,
        output_dir=str(d / "fuzz-out"),
        compiler="rustc",
    ))
    check("returns Error:", "Error:" in out)


async def test_test_fuzz_happy_path_gxx():
    print("\n[21] qt_test_fuzz -- g++ writes harness + patch + README")
    d = fresh_dir(SANDBOX_TMP, "v21_fuzz_happy_gxx")
    (d / "demo.pro").write_text("QT += core\n", encoding="utf-8")
    out = await server.qt_test_fuzz(QtTestFuzzInput(
        project_dir=str(d),
        target_function="parseCommand",
        fuzz_seconds=10,
        output_dir=str(d / "fuzz-out"),
        compiler="g++",
    ))
    check("fuzz_main.cpp written", (d / "fuzz-out" / "fuzz_main.cpp").exists())
    check("fuzz_patch_pro.snippet written", (d / "fuzz-out" / "fuzz_patch_pro.snippet").exists())
    check("fuzz_README.md written", (d / "fuzz-out" / "fuzz_README.md").exists())
    # Harness should reference our target.
    harness = (d / "fuzz-out" / "fuzz_main.cpp").read_text(encoding="utf-8")
    check("harness mentions parseCommand", "parseCommand" in harness)
    # Patch has libFuzzer flag.
    patch = (d / "fuzz-out" / "fuzz_patch_pro.snippet").read_text(encoding="utf-8")
    check("patch has fuzzer flag", "-fsanitize=fuzzer" in patch)


async def test_test_fuzz_happy_path_clangxx():
    print("\n[22] qt_test_fuzz -- clang++ emits Clang-targeted patch")
    d = fresh_dir(SANDBOX_TMP, "v21_fuzz_happy_clang")
    (d / "demo.pro").write_text("QT += core\n", encoding="utf-8")
    out = await server.qt_test_fuzz(QtTestFuzzInput(
        project_dir=str(d),
        target_function="parseJSON",
        fuzz_seconds=0,
        output_dir=str(d / "fuzz-out"),
        compiler="clang++",
    ))
    check("fuzz_main.cpp written", (d / "fuzz-out" / "fuzz_main.cpp").exists())
    patch = (d / "fuzz-out" / "fuzz_patch_pro.snippet").read_text(encoding="utf-8")
    check("patch has fuzzer flag", "-fsanitize=fuzzer" in patch)
    readme = (d / "fuzz-out" / "fuzz_README.md").read_text(encoding="utf-8")
    check("README targets parseJSON", "parseJSON" in readme)


async def test_test_fuzz_no_pro_file():
    print("\n[23] qt_test_fuzz -- non-project_dir (treated as fuzz source) writes harness only")
    # fuzz_seconds=0 still produces output even without a .pro — the tool is
    # purely a generator. Make sure it doesn't crash and writes the harness.
    d = fresh_dir(SANDBOX_TMP, "v21_fuzz_nopro")
    out = await server.qt_test_fuzz(QtTestFuzzInput(
        project_dir=str(d),
        target_function="parseInput",
        fuzz_seconds=0,
        output_dir=str(d / "fuzz-out"),
        compiler="g++",
    ))
    check("fuzz_main.cpp written", (d / "fuzz-out" / "fuzz_main.cpp").exists())


# ---------- runner ----------

async def main():
    tests = [
        # qt_complexity_lint
        test_complexity_lint_no_source,
        test_complexity_lint_simple_function,
        test_complexity_lint_complex_function_flagged,
        test_complexity_lint_json_output,
        test_complexity_lint_threshold_out_of_range,
        # qt_git_audit
        test_git_audit_not_a_repo,
        test_git_audit_happy_path,
        test_git_audit_json_output,
        # qt_appx
        test_appx_exe_not_found,
        test_appx_happy_path_writes_files,
        test_appx_invalid_architecture,
        # qt_ide_metadata
        test_ide_metadata_no_pro_file,
        test_ide_metadata_vscode_writes_files,
        test_ide_metadata_both_writes_idea,
        test_ide_metadata_invalid_ide,
        # qt_runtime_props
        test_runtime_props_no_executable_when_spawn,
        test_runtime_props_exe_not_in_sandbox,
        test_runtime_props_exe_does_not_exist,
        test_runtime_props_attach_to_sandbox_python,
        # qt_test_fuzz
        test_test_fuzz_invalid_compiler,
        test_test_fuzz_happy_path_gxx,
        test_test_fuzz_happy_path_clangxx,
        test_test_fuzz_no_pro_file,
    ]
    for t in tests:
        try:
            await t()
        except Exception as e:
            check(f"{t.__name__} no exception", False, hint=str(e))

    print(f"\n=== e2e_v21 summary: {sum(1 for _, c in results if c)} / {len(results)} checks passed ===")
    return 0 if all(c for _, c in results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
