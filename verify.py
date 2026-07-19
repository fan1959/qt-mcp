"""Quick verification: spawn qt-mcp server, list tools, call qt_env.

Usage: python verify.py
"""

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


SERVER = Path(__file__).parent / "server.py"


async def main() -> int:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"=== {len(tools.tools)} tools registered ===")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description.splitlines()[0] if t.description else '(no desc)'}")

            print()
            print("=== Calling qt_env ===")
            res = await session.call_tool("qt_env", arguments={})
            print(res.content[0].text)

            return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))