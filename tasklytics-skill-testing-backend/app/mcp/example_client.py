"""Example MCP client call against mcp_server.py - demonstrates consuming
the get_productivity_stats tool over MCP's stdio transport.

Run: python app/mcp/example_client.py
"""

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server_script = os.path.join(os.path.dirname(__file__), "mcp_server.py")
    # sys.executable, not the bare string "python" - avoids relying on
    # PATH resolving to the right interpreter (e.g. Windows' Store alias
    # shim intercepting a bare "python" call instead of a real interpreter).
    server_params = StdioServerParameters(command=sys.executable, args=[server_script])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "get_productivity_stats",
                arguments={"tasks": [
                    {"completed": True},
                    {"completed": False},
                    {"completed": True},
                ]},
            )
            print(result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
