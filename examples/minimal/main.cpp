// Minimal Qt 5 console app driven by qt-mcp.
//
// Build:   qmake hello.pro && mingw32-make
// Run:     ./debug/hello.exe --name World
//
// Or via Claude + qt-mcp:
//   "Scaffold console_app here, build, run with --name World."

#include <QCoreApplication>
#include <QCommandLineParser>
#include <QTextStream>

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);
    QCoreApplication::setApplicationName("hello");
    QCoreApplication::setApplicationVersion("0.1.0");

    QCommandLineParser parser;
    parser.setApplicationDescription("Minimal qt-mcp example: prints a greeting.");
    parser.addHelpOption();
    parser.addVersionOption();
    QCommandLineOption nameOpt(QStringList() << "n" << "name",
        "Whom to greet.", "name", "World");
    parser.addOption(nameOpt);
    parser.process(app);

    QTextStream out(stdout);
    out << "Hello, " << parser.value(nameOpt) << "!\n";
    return 0;
}