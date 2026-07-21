"""List the read-only tools published by the pinned DataHub MCP server."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


async def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    server = repo / ".venv" / "Scripts" / "mcp-server-datahub.exe"
    env = {
        "DATAHUB_GMS_URL": os.environ["DATAHUB_GMS_URL"],
        "DATAHUB_GMS_TOKEN": os.environ.get("DATAHUB_GMS_TOKEN", ""),
        "TOOLS_IS_MUTATION_ENABLED": "false",
        "TOOLS_IS_USER_ENABLED": "false",
        "DATAHUB_TELEMETRY_ENABLED": "false",
        "PYTHONUTF8": "1",
    }
    transport = StdioTransport(str(server), [], env=env, cwd=str(repo))
    async with Client(transport, timeout=60) as client:
        tools = await client.list_tools()
        print(
            json.dumps(
                [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema,
                    }
                    for tool in tools
                ],
                indent=2,
                default=str,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
