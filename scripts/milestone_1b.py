"""Run the bounded Milestone 1B authority-arbitration vertical slice."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arbiter.action import create_marker, revert_marker
from arbiter.catalog import InMemoryCatalog, LiveDataHubCatalog
from arbiter.fixtures import (
    ACTION,
    EXPECTED,
    OWNER_ALLOW,
    SCENARIOS,
    SOURCE_BY_ID,
    SOURCES,
)
from arbiter.models import Decision
from arbiter.policy import evaluate_authority


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_demo(catalog, repo_root: Path) -> dict[str, Any]:
    catalog.bootstrap(SOURCES)
    decisions: dict[str, dict[str, Any]] = {}
    for scenario, source_ids in SCENARIOS.items():
        urns = tuple(SOURCE_BY_ID[source_id].urn for source_id in source_ids)
        sources = catalog.read_sources(urns)
        evidence = evaluate_authority(ACTION, sources)
        if evidence.decision.value != EXPECTED[scenario]:
            raise RuntimeError(
                f"Scenario {scenario} expected {EXPECTED[scenario]}, "
                f"observed {evidence.decision.value}"
            )
        decisions[scenario] = evidence.canonical() | {"sha256": evidence.sha256()}

    allow_sources = catalog.read_sources((OWNER_ALLOW,))
    allow_evidence = evaluate_authority(ACTION, allow_sources)
    if allow_evidence.decision is not Decision.ALLOW:
        raise RuntimeError("Bounded action is permitted only after an ALLOW decision")

    marker_payload = {
        "milestone": "1B",
        "action": ACTION,
        "decision_evidence": allow_evidence.canonical(),
        "decision_sha256": allow_evidence.sha256(),
    }
    marker_path, marker_sha256 = create_marker(repo_root, marker_payload)
    target = SOURCE_BY_ID["owner-current-allow"]
    catalog.write_decision_evidence(target, allow_evidence)
    readback = catalog.read_decision_evidence(target.urn)
    if readback.get("arbiter.last_decision.sha256") != allow_evidence.sha256():
        raise RuntimeError("DataHub decision-evidence readback did not match")
    reverted_path = revert_marker(repo_root, marker_sha256)

    return {
        "milestone": "1B",
        "status": "PASS",
        "timestamp": utc_now(),
        "synthetic_instruction_source_count": len(SOURCES),
        "decisions": decisions,
        "bounded_action": {
            "path": str(marker_path.relative_to(repo_root.resolve())),
            "sha256": marker_sha256,
            "created": True,
            "reverted": not reverted_path.exists(),
        },
        "datahub_writeback": {
            "target_urn": target.urn,
            "evidence_sha256": allow_evidence.sha256(),
            "readback_exact": True,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog", choices=("memory", "live"), default="live"
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    catalog = (
        InMemoryCatalog()
        if args.catalog == "memory"
        else LiveDataHubCatalog.from_env()
    )
    output = run_demo(catalog, args.repo_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
