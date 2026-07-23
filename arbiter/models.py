from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class Directive(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


class Decision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class InstructionSource:
    source_id: str
    urn: str
    name: str
    action_scope: str
    directive: Directive
    authority_rank: int
    owner_urn: str
    domain_urn: str
    tags: tuple[str, ...]
    lineage_upstreams: tuple[str, ...]
    deprecated: bool = False
    replacement_urn: str | None = None
    metadata_complete: bool = True

    def canonical(self) -> dict[str, Any]:
        value = asdict(self)
        value["directive"] = self.directive.value
        value["tags"] = list(self.tags)
        value["lineage_upstreams"] = list(self.lineage_upstreams)
        return value


@dataclass(frozen=True)
class DecisionEvidence:
    action: str
    decision: Decision
    reason_code: str
    source_urns: tuple[str, ...]
    authoritative_rank: int | None
    replacement_urns: tuple[str, ...] = ()

    def canonical(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "decision": self.decision.value,
            "reason_code": self.reason_code,
            "source_urns": list(self.source_urns),
            "authoritative_rank": self.authoritative_rank,
            "replacement_urns": list(self.replacement_urns),
        }

    def sha256(self) -> str:
        payload = json.dumps(
            self.canonical(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
