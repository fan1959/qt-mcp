"""Pytest configuration for qt-mcp.

Auto-marks tests based on their directory:
- tests/light/*.py -> 'light' marker (no Qt SDK needed)
- tests/full/*.py  -> 'full' marker (Qt SDK required)

Lets you run:
    pytest -m light                 # fast, no Qt SDK
    pytest -m full                  # requires Qt SDK
    pytest -m "not full"            # everything that runs without Qt SDK

Note: per-test e2e suites that need the JSON footer (e2e_v29+) set
``QT_MCP_JSON=1`` via a module-level autouse fixture, leaving the global
default untouched so existing v13/v18 tests that expect raw output remain
green.
"""
import sys
from pathlib import Path

import pytest

# Make server importable from any test file (avoids needing PYTHONPATH tweaks)
ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))


def pytest_collection_modifyitems(config, items):
    """Apply 'light' or 'full' marker to each collected test based on its file's parent dir."""
    for item in items:
        fspath = Path(str(item.fspath))
        try:
            rel = fspath.relative_to(ROOT / "tests")
        except ValueError:
            continue
        # rel.parts[0] is 'light' or 'full' or other
        if rel.parts and rel.parts[0] in ("light", "full"):
            marker_name = rel.parts[0]
            item.add_marker(pytest.mark.__getattr__(marker_name))


def pytest_addoption(parser):
    parser.addoption(
        "--run-full",
        action="store_true",
        default=False,
        help="Also run tests marked 'full' (requires Qt SDK). Default: light only.",
    )