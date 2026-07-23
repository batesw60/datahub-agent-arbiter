"""Perform one qualifying read through the self-hosted DataHub MCP Server."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_GMS_URL = "http://localhost:8080"
DEFAULT_SAMPLE_URN = (
    "urn:li:dataset:(urn:li:dataPlatform:dbt,"
    "b2fd91.order_entry_db.order_entry.promotions,PROD)"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _unwrap_result(value: Any) -> Any:
    while isinstance(value, dict) and set(value) == {"result"}:
        value = value["result"]
    return value


def result_payload(result: Any) -> Any:
    """Return the JSON-compatible payload produced by an MCP tool call."""
    from mcp.types import TextContent

    if result.isError:
        detail = "\n".join(
            part.text for part in result.content if isinstance(part, TextContent)
        )
        raise RuntimeError(f"MCP tool returned an error: {detail}")

    if result.structuredContent is not None:
        return _unwrap_result(result.structuredContent)

    text = "\n".join(
        part.text for part in result.content if isinstance(part, TextContent)
    )
    if not text:
        raise RuntimeError("MCP tool returned neither structured content nor text")
    try:
        return _unwrap_result(json.loads(text))
    except json.JSONDecodeError:
        return text


def find_first_key(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        if key in value and value[key] not in (None, "", [], {}):
            return value[key]
        for child in value.values():
            found = find_first_key(child, key)
            if found not in (None, "", [], {}):
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_first_key(child, key)
            if found not in (None, "", [], {}):
                return found
    return None


def entity_name(metadata: Any) -> str:
    properties = find_first_key(metadata, "properties")
    if isinstance(properties, dict) and properties.get("name"):
        return str(properties["name"])
    name = find_first_key(metadata, "name")
    return str(name) if name else "UNKNOWN"


def resolve_token(gms_url: str) -> tuple[str, str]:
    from datahub.cli.cli_utils import generate_access_token

    supplied = os.environ.get("DATAHUB_GMS_TOKEN")
    if supplied:
        return supplied, "DATAHUB_GMS_TOKEN"

    username = os.environ.get("DATAHUB_USERNAME", "datahub")
    password = os.environ.get("DATAHUB_PASSWORD", "datahub")
    _, generated = generate_access_token(
        username=username,
        password=password,
        gms_url=gms_url,
        validity="ONE_DAY",
    )
    return generated, "QUICKSTART_CREDENTIAL_EXCHANGE"


class McpDataHubReader:
    def __init__(self, gms_url: str, token: str) -> None:
        from mcp import StdioServerParameters

        server_env = os.environ.copy()
        server_env.update(
            {
                "DATAHUB_GMS_URL": gms_url,
                "DATAHUB_GMS_TOKEN": token,
                "PYTHONUTF8": "1",
                "DATAHUB_TELEMETRY_ENABLED": "false",
                "TOOLS_IS_MUTATION_ENABLED": "false",
            }
        )
        self.parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server_datahub"],
            env=server_env,
        )

    async def call(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client

        async with stdio_client(self.parameters) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                available = {tool.name for tool in (await session.list_tools()).tools}
                if tool_name not in available:
                    raise RuntimeError(
                        f"Required MCP tool {tool_name!r} is unavailable; "
                        f"available tools: {sorted(available)}"
                    )
                return result_payload(await session.call_tool(tool_name, arguments))


async def run(args: argparse.Namespace) -> dict[str, Any]:
    token, token_source = resolve_token(args.gms_url)
    reader = McpDataHubReader(args.gms_url, token)
    metadata = await reader.call("get_entities", {"urns": args.urn})
    output = {
        "milestone": "1A",
        "status": "PASS",
        "timestamp": utc_now(),
        "read_attempt": args.attempt,
        "eligible_technology": "DataHub MCP Server",
        "eligible_tool_operation": "get_entities",
        "transport": "stdio",
        "mcp_server_version": "0.6.0",
        "datahub_gms_url": args.gms_url,
        "authentication": token_source,
        "entity_urn": args.urn,
        "entity_name": entity_name(metadata),
        "metadata": metadata,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", type=int, required=True, choices=(1, 2))
    parser.add_argument("--urn", default=DEFAULT_SAMPLE_URN)
    parser.add_argument("--gms-url", default=os.environ.get("DATAHUB_GMS_URL", DEFAULT_GMS_URL))
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    output = asyncio.run(run(parse_args()))
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
