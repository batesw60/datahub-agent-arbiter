"""Supplement the MCP negative deprecation/replacement test via the DataHub SDK."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from datahub.ingestion.graph.client import DataHubGraph, DataHubGraphConfig
from datahub.metadata.schema_classes import DeprecationClass


URN = "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.ORDER_ENTRY_DB.analytics.order_details,PROD)"


def main() -> None:
    graph = DataHubGraph(
        DataHubGraphConfig(
            server=os.environ["DATAHUB_GMS_URL"],
            token=os.environ.get("DATAHUB_GMS_TOKEN"),
        )
    )
    aspect = graph.get_aspect(URN, DeprecationClass)
    print(
        json.dumps(
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "supplement_only": True,
                "dataset_urn": URN,
                "deprecation_aspect_present": aspect is not None,
                "deprecation_aspect": aspect.to_obj() if aspect is not None else None,
                "sdk_model_fields": [
                    "deprecated",
                    "decommissionTime",
                    "note",
                    "actor",
                    "replacement",
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
