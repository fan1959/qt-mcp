import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

"""E2E test for the newly added tools: qt_pro_edit / qt_moc_check / qt_deps.

Also exercises the upgraded qt_build error categorization by deliberately
breaking a scaffolded project and verifying the hint block appears.
"""
import asyncio
import shutil
import sys
import textwrap
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
    if res.isError or "Error" in text:
        if not expect_error:
            raise RuntimeError(f"{tool} failed unexpectedly:\n{text}")
    return text


async def main():
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    work = TMP_ROOT / f"e2e_new_{uuid.uuid4().hex[:8]}"
    work.mkdir(parents=True, exist_ok=True)
    proj = work / "demo"
    print(f"Workdir: {work}")

    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    try:
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()

                # ---- 1) qt_pro_edit: list / get / append / set / remove ----
                print("\n# ---- qt_pro_edit ----", flush=True)
                await call(s, "qt_scaffold", name="demo", template="widget", output_dir=str(proj))
                pro = str(proj / "demo.pro")

                t = await call(s, "qt_pro_edit", pro_file=pro, action="list")
                assert "QT" in t and "core" in t, "list should show QT += core"

                t = await call(s, "qt_pro_edit", pro_file=pro, action="get", variable="QT")
                assert "core" in t, "get QT should show core"

                t = await call(s, "qt_pro_edit", pro_file=pro, action="append",
                               variable="QT", values=["network", "testlib"])
                assert "network" in t, "append should report network added"

                t = await call(s, "qt_pro_edit", pro_file=pro, action="get", variable="QT")
                assert "network" in t and "testlib" in t, "QT should now include network and testlib"

                t = await call(s, "qt_pro_edit", pro_file=pro, action="remove",
                               variable="QT", values=["testlib"])
                # Verify by re-listing — testlib must be gone from QT.
                t = await call(s, "qt_pro_edit", pro_file=pro, action="get", variable="QT")
                assert "testlib" not in t, f"testlib should be removed from QT:\n{t}"
                assert "network" in t, f"network should still be in QT:\n{t}"

                t = await call(s, "qt_pro_edit", pro_file=pro, action="set",
                               variable="DEFINES", values=["MY_APP_VERSION=1", "NDEBUG"])
                t = await call(s, "qt_pro_edit", pro_file=pro, action="get", variable="DEFINES")
                assert "MY_APP_VERSION=1" in t and "NDEBUG" in t, "DEFINES should be set"

                # Sandbox rejection: qt_pro_edit on a path outside the sandbox
                await call(s, "qt_pro_edit", expect_error=True,
                           pro_file=r"D:\outside\foo.pro", action="list")

                # ---- 2) qt_moc_check: a good header and a broken one ----
                print("\n# ---- qt_moc_check ----", flush=True)
                good_h = proj / "good.h"
                good_h.write_text(textwrap.dedent("""\
                    #pragma once
                    #include <QObject>
                    class Counter : public QObject {
                        Q_OBJECT
                    public:
                        explicit Counter(QObject* parent = nullptr);
                        int value() const;
                    signals:
                        void valueChanged(int v);
                    public slots:
                        void setValue(int v);
                    private:
                        int m_value = 0;
                    };
                """), encoding="utf-8")
                t = await call(s, "qt_moc_check", header=str(good_h))
                assert "moc OK" in t, f"good header should pass moc:\n{t}"

                # Broken: QWidget subclass with no Q_OBJECT
                broken_h = proj / "broken.h"
                broken_h.write_text(textwrap.dedent("""\
                    #pragma once
                    #include <QWidget>
                    class Bad : public QWidget {
                    public:
                        explicit Bad(QWidget* parent = nullptr);
                    };
                """), encoding="utf-8")
                t = await call(s, "qt_moc_check", expect_error=True, header=str(broken_h))
                # moc should report "no relevant classes" — verify hint surfaces it
                assert "no relevant classes" in t.lower() or "q_object" in t.lower(), \
                    f"broken header should be flagged:\n{t}"

                # ---- 3) qt_build error categorization ----
                print("\n# ---- qt_build error categorization ----", flush=True)
                # For the widget template, class name is the upper-cased project name ("Demo").
                # Add a bad source that references an undeclared symbol.
                bad_cpp = proj / "demowindow.cpp"
                bad_cpp.write_text(textwrap.dedent("""\
                    #include "demowindow.h"
                    #include "ui_demowindow.h"
                    Demo::Demo(QWidget* parent) : QWidget(parent), ui(new Ui::Demo) {
                        ui->setupUi(this);
                        int x = undeclared_symbol;  // intentional error
                    }
                    Demo::~Demo() { delete ui; }
                """), encoding="utf-8")
                t = await call(s, "qt_build", expect_error=True,
                              project_dir=str(proj), build_type="debug", jobs=2)
                assert "Category:" in t, f"qt_build output should include a Category line:\n{t}"
                print(f"  -> error categorized: {[l for l in t.splitlines() if 'Category' in l][0]}")

                # ---- 4) qt_deps: needs a real build ----
                print("\n# ---- qt_deps ----", flush=True)
                # Revert the broken file
                bad_cpp.write_text(textwrap.dedent("""\
                    #include "demowindow.h"
                    #include "ui_demowindow.h"
                    Demo::Demo(QWidget* parent) : QWidget(parent), ui(new Ui::Demo) {
                        ui->setupUi(this);
                    }
                    Demo::~Demo() { delete ui; }
                """), encoding="utf-8")
                await call(s, "qt_clean", project_dir=str(proj))
                await call(s, "qt_build", project_dir=str(proj), build_type="debug", jobs=2)
                exe = next(proj.rglob("*.exe"))
                t = await call(s, "qt_deps", executable=str(exe), qt_only=True)
                assert "Qt5Core.dll" in t, f"Qt5Core.dll should be in the Qt deps list:\n{t}"
                assert "Qt5Widgets.dll" in t, f"Qt5Widgets.dll should also be present:\n{t}"
                print(f"  -> Qt deps: {[l for l in t.splitlines() if 'Qt5' in l][:5]}")

                # qt_only=False shows everything (kernel32, msvcrt, ...)
                t = await call(s, "qt_deps", executable=str(exe), qt_only=False)
                assert "KERNEL32.dll" in t or "kernel32.dll" in t.lower(), \
                    f"qt_only=False should show KERNEL32.dll:\n{t}"

                # Sandbox rejection for deps
                await call(s, "qt_deps", expect_error=True, executable=r"D:\outside\foo.exe")

        print("\n=== NEW TOOLS E2E PASSED ===")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
