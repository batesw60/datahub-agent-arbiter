from __future__ import annotations

from .models import Directive, InstructionSource

ACTION = "CREATE_REPOSITORY_MARKER"
PLATFORM = "file"
DOMAIN_URN = "urn:li:domain:datahub-agent-arbiter"
OWNER_URN = "urn:li:corpuser:datahub-agent-arbiter-owner"


def dataset_urn(name: str) -> str:
    return f"urn:li:dataset:(urn:li:dataPlatform:{PLATFORM},datahub-agent-arbiter.{name},PROD)"


REVIEW_BASELINE = dataset_urn("review-baseline-allow")
OWNER_ALLOW = dataset_urn("owner-current-allow")
SECURITY_BLOCK = dataset_urn("security-current-block")
LEGACY_ALLOW = dataset_urn("legacy-deprecated-allow")


SOURCES: tuple[InstructionSource, ...] = (
    InstructionSource(
        source_id="review-baseline-allow",
        urn=REVIEW_BASELINE,
        name="Review Baseline Allow",
        action_scope=ACTION,
        directive=Directive.ALLOW,
        authority_rank=80,
        owner_urn=OWNER_URN,
        domain_urn=DOMAIN_URN,
        tags=("arbiter", "instruction-source", "review-baseline"),
        lineage_upstreams=(),
    ),
    InstructionSource(
        source_id="owner-current-allow",
        urn=OWNER_ALLOW,
        name="Owner Current Allow",
        action_scope=ACTION,
        directive=Directive.ALLOW,
        authority_rank=100,
        owner_urn=OWNER_URN,
        domain_urn=DOMAIN_URN,
        tags=("arbiter", "instruction-source", "owner-authority"),
        lineage_upstreams=(REVIEW_BASELINE,),
    ),
    InstructionSource(
        source_id="security-current-block",
        urn=SECURITY_BLOCK,
        name="Security Current Block",
        action_scope=ACTION,
        directive=Directive.BLOCK,
        authority_rank=100,
        owner_urn=OWNER_URN,
        domain_urn=DOMAIN_URN,
        tags=("arbiter", "instruction-source", "security-authority"),
        lineage_upstreams=(REVIEW_BASELINE,),
    ),
    InstructionSource(
        source_id="legacy-deprecated-allow",
        urn=LEGACY_ALLOW,
        name="Legacy Deprecated Allow",
        action_scope=ACTION,
        directive=Directive.ALLOW,
        authority_rank=120,
        owner_urn=OWNER_URN,
        domain_urn=DOMAIN_URN,
        tags=("arbiter", "instruction-source", "deprecated"),
        lineage_upstreams=(OWNER_ALLOW,),
        deprecated=True,
        replacement_urn=OWNER_ALLOW,
    ),
)

SOURCE_BY_ID = {source.source_id: source for source in SOURCES}
SCENARIOS: dict[str, tuple[str, ...]] = {
    "allow": ("owner-current-allow",),
    "block": ("security-current-block",),
    "review": ("owner-current-allow", "security-current-block"),
    "deprecated": ("legacy-deprecated-allow",),
}
EXPECTED = {
    "allow": "ALLOW",
    "block": "BLOCK",
    "review": "REVIEW_REQUIRED",
    "deprecated": "BLOCK",
}
