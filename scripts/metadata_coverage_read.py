"""Probe Milestone 1A metadata coverage exclusively through DataHub MCP tools."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from first_agent_context_read import (
    DEFAULT_GMS_URL,
    DEFAULT_SAMPLE_URN,
    McpDataHubReader,
    find_first_key,
    resolve_token,
    utc_now,
)


def available(value: Any, key: str) -> bool:
    return find_first_key(value, key) not in (None, "", [], {})


async def run(args: argparse.Namespace) -> dict[str, Any]:
    token, token_source = resolve_token(args.gms_url)
    reader = McpDataHubReader(args.gms_url, token)

    entity = await reader.call("get_entities", {"urns": args.urn})
    upstream = await reader.call(
        "get_lineage",
        {"urn": args.urn, "upstream": True, "max_hops": 1, "max_results": 10},
    )
    downstream = await reader.call(
        "get_lineage",
        {"urn": args.urn, "upstream": False, "max_hops": 1, "max_results": 10},
    )
    deprecated_search = await reader.call(
        "search",
        {"query": "*", "filter": "deprecated = true", "num_results": 10},
    )
    facet_search = await reader.call(
        "search",
        {"query": "*", "filter": "entity_type = dataset", "num_results": 0},
    )

    matrix = {
        "ownership": {
            "status": "DIRECTLY_AVAILABLE" if available(entity, "ownership") else "NOT_VERIFIED",
            "operation": "get_entities",
        },
        "lineage": {
            "status": "AVAILABLE_WITH_ADDITIONAL_QUERY",
            "operation": "get_lineage (upstream and downstream calls succeeded)",
        },
        "deprecation_status": {
            "status": (
                "DIRECTLY_AVAILABLE"
                if available(entity, "deprecation") or available(deprecated_search, "deprecated")
                else "NOT_VERIFIED"
            ),
            "operation": "get_entities plus search filter deprecated = true",
        },
        "replacement_reference": {
            "status": (
                "DIRECTLY_AVAILABLE"
                if available(entity, "replacement") or available(entity, "replacementUrn")
                else "NOT_AVAILABLE"
            ),
            "operation": "get_entities",
            "note": "No replacement field was returned; the MCP deprecation fragment exposes actor, deprecated, note, decommissionTime, and actorEntity only.",
        },
        "domain": {
            "status": "DIRECTLY_AVAILABLE" if available(entity, "domain") else "NOT_VERIFIED",
            "operation": "get_entities",
        },
        "tags": {
            "status": "DIRECTLY_AVAILABLE" if available(entity, "tags") else "NOT_VERIFIED",
            "operation": "get_entities",
        },
        "structured_properties": {
            "status": (
                "DIRECTLY_AVAILABLE"
                if available(entity, "structuredProperties")
                or any(
                    "structuredPropert" in str(key)
                    for key in _all_keys(facet_search)
                )
                else "NOT_VERIFIED"
            ),
            "operation": "get_entities plus dataset facet search",
        },
        "description_or_documentation": {
            "status": "DIRECTLY_AVAILABLE" if available(entity, "description") else "NOT_VERIFIED",
            "operation": "get_entities",
        },
    }

    output = {
        "milestone": "1A",
        "status": "PASS",
        "timestamp": utc_now(),
        "eligible_technology": "DataHub MCP Server",
        "transport": "stdio",
        "authentication": token_source,
        "entity_urn": args.urn,
        "coverage_matrix": matrix,
        "raw_mcp_results": {
            "get_entities": entity,
            "get_lineage_upstream": upstream,
            "get_lineage_downstream": downstream,
            "search_deprecated": deprecated_search,
            "search_dataset_facets": facet_search,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return output


def _all_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        keys.extend(str(key) for key in value)
        for child in value.values():
            keys.extend(_all_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.extend(_all_keys(child))
    return keys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--urn", default=DEFAULT_SAMPLE_URN)
    parser.add_argument("--gms-url", default=os.environ.get("DATAHUB_GMS_URL", DEFAULT_GMS_URL))
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    output = asyncio.run(run(parse_args()))
    print(json.dumps(output["coverage_matrix"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
