"""Perform one reproducible read-only DataHub MCP evidence pass."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


def result_payload(result: Any) -> dict[str, Any]:
    content: list[Any] = []
    if result.structured_content is None:
        for item in result.content:
            if hasattr(item, "model_dump"):
                content.append(item.model_dump(mode="json"))
            else:
                content.append(str(item))
    return {
        "isError": bool(result.is_error),
        "structuredContent": result.structured_content,
        "content": content,
    }


def nested_values(value: Any, wanted_key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if key.lower() == wanted_key.lower():
                found.append(nested)
            found.extend(nested_values(nested, wanted_key))
    elif isinstance(value, list):
        for item in value:
            found.extend(nested_values(item, wanted_key))
    return found


def summarize_value(value: Any, max_chars: int = 400) -> Any:
    if isinstance(value, str):
        return value if len(value) <= max_chars else value[:max_chars] + "...[trimmed]"
    serialized = json.dumps(value, default=str, ensure_ascii=False)
    if len(serialized) <= max_chars:
        return value
    return serialized[:max_chars] + "...[trimmed]"


def collect_aspect_keys(value: Any) -> dict[str, list[dict[str, Any]]]:
    needles = {
        "ownership": ("ownership", "owners"),
        "domains": ("domain", "domains"),
        "tags": ("tag", "tags"),
        "structured_properties": ("structuredproperties", "structuredproperty"),
        "deprecation": ("deprecation", "deprecated"),
        "replacement": ("replacement", "replacedby"),
    }
    evidence: dict[str, list[dict[str, Any]]] = {key: [] for key in needles}

    def walk(node: Any, path: str = "$") -> None:
        if isinstance(node, dict):
            for key, nested in node.items():
                normalized = key.lower().replace("_", "")
                for aspect, matches in needles.items():
                    if normalized in matches and len(evidence[aspect]) < 2:
                        evidence[aspect].append(
                            {"path": f"{path}.{key}", "value": summarize_value(nested)}
                        )
                walk(nested, f"{path}.{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(value)
    return evidence


def search_summary(payload: dict[str, Any]) -> dict[str, Any]:
    structured = payload.get("structuredContent") or {}
    totals = nested_values(structured, "total")
    return {
        "isError": payload["isError"],
        "total_values": totals[:10],
        "dataset_urns": dataset_urns(structured)[:20],
        "structured_content_excerpt": summarize_value(structured, 1000),
    }


def dataset_urns(value: Any) -> list[str]:
    serialized = json.dumps(value, default=str)
    urns = re.findall(r"urn:li:dataset:\([^\"\\]+?\)", serialized)
    return list(dict.fromkeys(urns))


def has_positive_total(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key.lower() in {"total", "count", "returned"} and isinstance(nested, int) and nested > 0:
                return True
            if has_positive_total(nested):
                return True
    elif isinstance(value, list):
        return any(has_positive_total(item) for item in value)
    return False


async def main(attempt: int) -> None:
    started = datetime.now(timezone.utc).isoformat()
    repo = Path(__file__).resolve().parents[1]
    server = repo / ".venv" / "Scripts" / "mcp-server-datahub.exe"
    env = {
        "DATAHUB_GMS_URL": os.environ["DATAHUB_GMS_URL"],
        "DATAHUB_GMS_TOKEN": os.environ.get("DATAHUB_GMS_TOKEN", ""),
        "TOOLS_IS_MUTATION_ENABLED": "false",
        "TOOLS_IS_USER_ENABLED": "false",
        "DATAHUB_TELEMETRY_ENABLED": "false",
        "PYTHONUTF8": "1",
        "LOGURU_LEVEL": "WARNING",
        "FASTMCP_LOG_LEVEL": "WARNING",
    }
    transport = StdioTransport(str(server), [], env=env, cwd=str(repo))

    async with Client(transport, timeout=90) as client:
        tools = await client.list_tools()
        tool_names = [tool.name for tool in tools]

        catalog_search = result_payload(
            await client.call_tool(
                "search",
                {
                    "query": "*",
                    "filter": (
                        "entity_type = dataset AND owner IS NOT NULL "
                        "AND domain IS NOT NULL AND tag IS NOT NULL"
                    ),
                    "num_results": 10,
                    "offset": 0,
                },
            )
        )
        candidates = dataset_urns(catalog_search)
        if not candidates:
            raise RuntimeError("MCP search returned no eligible dataset URNs")

        selected_urn = candidates[0]
        lineage_direction = "upstream"
        selected_lineage: dict[str, Any] | None = None
        lineage_attempts: list[dict[str, Any]] = []
        for urn in candidates:
            for upstream, direction in ((True, "upstream"), (False, "downstream")):
                lineage = result_payload(
                    await client.call_tool(
                        "get_lineage",
                        {
                            "urn": urn,
                            "upstream": upstream,
                            "max_hops": 1,
                            "max_results": 20,
                            "offset": 0,
                        },
                    )
                )
                positive = has_positive_total(lineage.get("structuredContent"))
                lineage_attempts.append(
                    {"urn": urn, "direction": direction, "positive_result": positive}
                )
                if positive:
                    selected_urn = urn
                    lineage_direction = direction
                    selected_lineage = lineage
                    break
            if selected_lineage is not None:
                break
        if selected_lineage is None:
            selected_lineage = result_payload(
                await client.call_tool(
                    "get_lineage",
                    {
                        "urn": selected_urn,
                        "upstream": True,
                        "max_hops": 1,
                        "max_results": 20,
                        "offset": 0,
                    },
                )
            )

        entity = result_payload(
            await client.call_tool("get_entities", {"urns": [selected_urn]})
        )
        deprecated = result_payload(
            await client.call_tool(
                "search",
                {
                    "query": "*",
                    "filter": "entity_type = dataset AND deprecated = true",
                    "num_results": 10,
                    "offset": 0,
                },
            )
        )
        replacement = result_payload(
            await client.call_tool(
                "search_documents",
                {
                    "query": "/q replacement OR deprecated OR deprecation",
                    "num_results": 10,
                    "offset": 0,
                },
            )
        )

        coverage_text = json.dumps(
            {
                "entity": entity,
                "lineage": selected_lineage,
                "deprecated_search": deprecated,
                "replacement_search": replacement,
            },
            default=str,
        ).lower()
        coverage = {
            "ownership_key_observed": "ownership" in coverage_text or "owners" in coverage_text,
            "lineage_positive_result": has_positive_total(selected_lineage.get("structuredContent")),
            "deprecation_key_or_filter_result_observed": "deprecat" in coverage_text,
            "replacement_key_or_search_result_observed": "replacement" in coverage_text,
            "domains_key_observed": "domain" in coverage_text,
            "tags_key_observed": "tag" in coverage_text,
            "structured_properties_key_observed": "structuredpropert" in coverage_text,
        }

        completed = datetime.now(timezone.utc).isoformat()
        entity_aspects = collect_aspect_keys(entity.get("structuredContent"))
        lineage_totals = nested_values(selected_lineage.get("structuredContent"), "total")
        lineage_urns = dataset_urns(selected_lineage.get("structuredContent"))

        print(
            json.dumps(
                {
                    "attempt": attempt,
                    "started_at_utc": started,
                    "completed_at_utc": completed,
                    "eligible_path": "DataHub MCP Server 0.6.0 over stdio",
                    "gms_url": env["DATAHUB_GMS_URL"],
                    "mutation_tools_enabled": False,
                    "tool_names": tool_names,
                    "selected_dataset_urn": selected_urn,
                    "lineage_direction": lineage_direction,
                    "lineage_attempts": lineage_attempts,
                    "catalog_search": search_summary(catalog_search),
                    "entity_read": {
                        "isError": entity["isError"],
                        "aspect_key_evidence": entity_aspects,
                    },
                    "lineage_read": {
                        "isError": selected_lineage["isError"],
                        "total_values": lineage_totals[:10],
                        "dataset_urns": lineage_urns[:20],
                        "structured_content_excerpt": summarize_value(
                            selected_lineage.get("structuredContent"), 1200
                        ),
                    },
                    "deprecated_dataset_search": search_summary(deprecated),
                    "replacement_document_search": {
                        "isError": replacement["isError"],
                        "total_values": nested_values(
                            replacement.get("structuredContent"), "total"
                        )[:10],
                        "structured_content_excerpt": summarize_value(
                            replacement.get("structuredContent"), 1000
                        ),
                    },
                    "coverage_detection": coverage,
                },
                indent=2,
                default=str,
            )
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", type=int, required=True)
    args = parser.parse_args()
    asyncio.run(main(args.attempt))
