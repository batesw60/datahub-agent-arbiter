from __future__ import annotations

from dataclasses import replace
import inspect
from pathlib import Path

import pytest

from arbiter.action import MARKER_RELATIVE_PATH, create_marker, revert_marker
from arbiter.catalog import (
    PROPERTY_DEFINITIONS,
    InMemoryCatalog,
    LiveDataHubCatalog,
    _find_custom_properties,
    _source_from_metadata,
)
from arbiter.fixtures import ACTION, OWNER_ALLOW, SOURCE_BY_ID, SOURCES
from arbiter.models import Decision
from arbiter.policy import evaluate_authority
from scripts.milestone_1b import run_demo


def test_exactly_four_synthetic_sources() -> None:
    assert len(SOURCES) == 4
    assert len({source.urn for source in SOURCES}) == 4


def test_allow_decision() -> None:
    evidence = evaluate_authority(ACTION, [SOURCE_BY_ID["owner-current-allow"]])
    assert evidence.decision is Decision.ALLOW
    assert evidence.reason_code == "AUTHORITATIVE_ALLOW"


def test_explicit_block_decision() -> None:
    evidence = evaluate_authority(ACTION, [SOURCE_BY_ID["security-current-block"]])
    assert evidence.decision is Decision.BLOCK
    assert evidence.reason_code == "AUTHORITATIVE_BLOCK"


def test_equal_authority_conflict_requires_review() -> None:
    evidence = evaluate_authority(
        ACTION,
        [
            SOURCE_BY_ID["owner-current-allow"],
            SOURCE_BY_ID["security-current-block"],
        ],
    )
    assert evidence.decision is Decision.REVIEW_REQUIRED
    assert evidence.reason_code == "EQUAL_AUTHORITY_CONFLICT"


def test_deprecated_source_blocks_and_names_replacement() -> None:
    evidence = evaluate_authority(
        ACTION, [SOURCE_BY_ID["legacy-deprecated-allow"]]
    )
    assert evidence.decision is Decision.BLOCK
    assert evidence.reason_code == "DEPRECATED_AUTHORITY_SOURCE"
    assert evidence.replacement_urns == (OWNER_ALLOW,)


def test_incomplete_metadata_blocks() -> None:
    incomplete = replace(
        SOURCE_BY_ID["owner-current-allow"], metadata_complete=False
    )
    evidence = evaluate_authority(ACTION, [incomplete])
    assert evidence.decision is Decision.BLOCK
    assert evidence.reason_code == "INCOMPLETE_AUTHORITY_METADATA"


def test_evaluation_is_order_independent() -> None:
    first = evaluate_authority(
        ACTION,
        [
            SOURCE_BY_ID["owner-current-allow"],
            SOURCE_BY_ID["security-current-block"],
        ],
    )
    second = evaluate_authority(
        ACTION,
        [
            SOURCE_BY_ID["security-current-block"],
            SOURCE_BY_ID["owner-current-allow"],
        ],
    )
    assert first.canonical() == second.canonical()
    assert first.sha256() == second.sha256()


def test_marker_create_and_revert(tmp_path: Path) -> None:
    path, digest = create_marker(tmp_path, {"decision": "ALLOW"})
    assert path.exists()
    revert_marker(tmp_path, digest)
    assert not path.exists()


def test_marker_refuses_nonmatching_overwrite(tmp_path: Path) -> None:
    path = tmp_path / MARKER_RELATIVE_PATH
    path.parent.mkdir(parents=True)
    path.write_text("unrelated\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Refusing to overwrite"):
        create_marker(tmp_path, {"decision": "ALLOW"})


def test_in_memory_writeback_roundtrip() -> None:
    catalog = InMemoryCatalog()
    catalog.bootstrap(SOURCES)
    target = SOURCE_BY_ID["owner-current-allow"]
    evidence = evaluate_authority(ACTION, [target])
    catalog.write_decision_evidence(target, evidence)
    readback = catalog.read_decision_evidence(target.urn)
    assert readback["arbiter.last_decision.sha256"] == evidence.sha256()


def test_demo_passes_and_leaves_repository_clean(tmp_path: Path) -> None:
    result = run_demo(InMemoryCatalog(), tmp_path)
    assert result["status"] == "PASS"
    assert result["synthetic_instruction_source_count"] == 4
    assert result["bounded_action"]["reverted"] is True
    assert not (tmp_path / MARKER_RELATIVE_PATH).exists()

def test_live_deprecation_emission_supplies_actor() -> None:
    """Lock the required DataHub deprecation audit actor into the live adapter."""
    from datahub.metadata.schema_classes import DeprecationClass

    source = SOURCE_BY_ID["legacy-deprecated-allow"]
    aspect = DeprecationClass(
        deprecated=source.deprecated,
        note=f"Replaced by {source.replacement_urn}",
        actor=source.owner_urn,
    )
    assert aspect.actor == source.owner_urn
    assert "actor=source.owner_urn" in inspect.getsource(
        LiveDataHubCatalog._emit_source
    )

def test_structured_property_definition_retry_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = LiveDataHubCatalog("http://localhost:8080", "token")
    posts: list[tuple[str, dict[str, object]]] = []

    def fake_get(path: str) -> dict[str, object]:
        encoded_urn = path.split("/structuredProperty/", 1)[1].split(
            "/propertyDefinition", 1
        )[0]
        import urllib.parse

        urn = urllib.parse.unquote(encoded_urn)
        qualified_name = urn.removeprefix("urn:li:structuredProperty:")
        definition = next(
            item
            for item in PROPERTY_DEFINITIONS
            if item[0] == qualified_name
        )
        _, value_type, display_name = definition
        return {
            "value": {
                "qualifiedName": qualified_name,
                "valueType": f"urn:li:dataType:datahub.{value_type}",
                "description": f"DataHub Agent Arbiter {display_name.lower()}",
                "displayName": display_name,
                "cardinality": "SINGLE",
                "entityTypes": ["urn:li:entityType:datahub.dataset"],
                "immutable": False,
            }
        }

    monkeypatch.setattr(catalog, "_openapi_get_optional", fake_get)
    monkeypatch.setattr(
        catalog,
        "_openapi_post",
        lambda path, payload: posts.append((path, payload)),
    )

    catalog._ensure_structured_property_definitions()
    assert posts == []


def test_structured_property_definition_is_created_when_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = LiveDataHubCatalog("http://localhost:8080", "token")
    posts: list[tuple[str, dict[str, object]]] = []

    monkeypatch.setattr(catalog, "_openapi_get_optional", lambda path: None)
    monkeypatch.setattr(
        catalog,
        "_openapi_post",
        lambda path, payload: posts.append((path, payload)),
    )

    catalog._ensure_structured_property_definitions()
    assert len(posts) == len(PROPERTY_DEFINITIONS)

def _mcp_metadata(
    source_id: str,
    *,
    include_deprecation: bool,
) -> dict[str, object]:
    source = SOURCE_BY_ID[source_id]
    metadata: dict[str, object] = {
        "properties": {
            "customProperties": [
                {"key": "arbiter.source_id", "value": source.source_id},
                {"key": "arbiter.action_scope", "value": source.action_scope},
                {"key": "arbiter.directive", "value": source.directive.value},
                {
                    "key": "arbiter.authority_rank",
                    "value": str(source.authority_rank),
                },
                {
                    "key": "arbiter.deprecated",
                    "value": str(source.deprecated).lower(),
                },
                {
                    "key": "arbiter.replacement_urn",
                    "value": source.replacement_urn or "",
                },
                {
                    "key": "arbiter.lineage_upstreams",
                    "value": __import__("json").dumps(
                        list(source.lineage_upstreams)
                    ),
                },
            ]
        },
        "ownership": {"owners": [{"owner": {"urn": source.owner_urn}}]},
        "tags": {"tags": [{"tag": {"urn": f"urn:li:tag:{source.tags[0]}"}}]},
        "structuredProperties": {"properties": [{"values": [{"stringValue": "x"}]}]},
        "domain": {"domain": {"urn": source.domain_urn}},
    }
    if include_deprecation:
        metadata["deprecation"] = {
            "deprecated": source.deprecated,
            "actor": source.owner_urn,
        }
    return metadata


def test_mcp_custom_properties_list_is_normalized() -> None:
    metadata = _mcp_metadata(
        "owner-current-allow",
        include_deprecation=False,
    )
    custom = _find_custom_properties(metadata)
    assert custom is not None
    assert custom["arbiter.directive"] == "ALLOW"
    assert custom["arbiter.authority_rank"] == "100"


def test_active_mcp_source_is_complete_without_false_deprecation_aspect() -> None:
    template = SOURCE_BY_ID["owner-current-allow"]
    source = _source_from_metadata(
        template,
        _mcp_metadata(
            "owner-current-allow",
            include_deprecation=False,
        ),
        {"upstreams": {"total": 1}},
        {"downstreams": {"total": 0}},
    )
    assert source.metadata_complete is True
    assert source.directive.value == "ALLOW"
    assert evaluate_authority(ACTION, [source]).decision is Decision.ALLOW


def test_deprecated_mcp_source_requires_deprecation_aspect() -> None:
    template = SOURCE_BY_ID["legacy-deprecated-allow"]
    source = _source_from_metadata(
        template,
        _mcp_metadata(
            "legacy-deprecated-allow",
            include_deprecation=False,
        ),
        {"upstreams": {"total": 1}},
        {"downstreams": {"total": 0}},
    )
    assert source.metadata_complete is False
    evidence = evaluate_authority(ACTION, [source])
    assert evidence.decision is Decision.BLOCK
    assert evidence.reason_code == "INCOMPLETE_AUTHORITY_METADATA"

class _CaptureEmitter:
    def __init__(self) -> None:
        self.proposals: list[object] = []

    def emit(self, proposal: object) -> None:
        self.proposals.append(proposal)


def test_dataset_structured_properties_use_sdk_upsert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = LiveDataHubCatalog("http://localhost:8080", "token")
    emitter = _CaptureEmitter()
    source = SOURCE_BY_ID["owner-current-allow"]

    monkeypatch.setattr(catalog, "_emitter", lambda: emitter)
    monkeypatch.setattr(
        catalog,
        "_openapi_post",
        lambda path, payload: (_ for _ in ()).throw(
            AssertionError("dataset structured properties must not use OpenAPI CREATE")
        ),
    )

    catalog._set_structured_properties(source)

    assert len(emitter.proposals) == 1
    proposal = emitter.proposals[0]
    assert proposal.changeType == "UPSERT"
    assert proposal.entityUrn == source.urn

    assignments = {
        assignment.propertyUrn: assignment.values
        for assignment in proposal.aspect.properties
    }
    assert assignments[
        "urn:li:structuredProperty:io.datahub.arbiter.authorityRank"
    ] == [100.0]
    assert assignments[
        "urn:li:structuredProperty:io.datahub.arbiter.directive"
    ] == ["ALLOW"]
    assert assignments[
        "urn:li:structuredProperty:io.datahub.arbiter.actionScope"
    ] == ["CREATE_REPOSITORY_MARKER"]


def test_dataset_structured_properties_upsert_is_retry_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = LiveDataHubCatalog("http://localhost:8080", "token")
    emitter = _CaptureEmitter()
    source = SOURCE_BY_ID["legacy-deprecated-allow"]

    monkeypatch.setattr(catalog, "_emitter", lambda: emitter)

    catalog._set_structured_properties(source)
    catalog._set_structured_properties(source)

    assert len(emitter.proposals) == 2
    assert all(proposal.changeType == "UPSERT" for proposal in emitter.proposals)

    first = emitter.proposals[0].aspect.to_obj()
    second = emitter.proposals[1].aspect.to_obj()
    assert first == second

    assignments = {
        assignment.propertyUrn: assignment.values
        for assignment in emitter.proposals[0].aspect.properties
    }
    assert assignments[
        "urn:li:structuredProperty:io.datahub.arbiter.replacementUrn"
    ] == [source.replacement_urn]

