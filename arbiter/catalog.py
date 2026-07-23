from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from dataclasses import replace
from typing import Any, Protocol

from .fixtures import DOMAIN_URN, OWNER_URN
from .models import DecisionEvidence, Directive, InstructionSource

PROPERTY_PREFIX = "io.datahub.arbiter"
PROPERTY_DEFINITIONS = (
    (f"{PROPERTY_PREFIX}.authorityRank", "number", "Authority Rank"),
    (f"{PROPERTY_PREFIX}.directive", "string", "Directive"),
    (f"{PROPERTY_PREFIX}.actionScope", "string", "Action Scope"),
    (f"{PROPERTY_PREFIX}.replacementUrn", "string", "Replacement URN"),
)


class Catalog(Protocol):
    def bootstrap(self, sources: Iterable[InstructionSource]) -> None: ...
    def read_sources(self, urns: Iterable[str]) -> tuple[InstructionSource, ...]: ...
    def write_decision_evidence(
        self, target: InstructionSource, evidence: DecisionEvidence
    ) -> None: ...
    def read_decision_evidence(self, target_urn: str) -> dict[str, str]: ...


class InMemoryCatalog:
    def __init__(self) -> None:
        self.sources: dict[str, InstructionSource] = {}
        self.evidence: dict[str, dict[str, str]] = {}

    def bootstrap(self, sources: Iterable[InstructionSource]) -> None:
        self.sources = {source.urn: source for source in sources}

    def read_sources(self, urns: Iterable[str]) -> tuple[InstructionSource, ...]:
        return tuple(self.sources[urn] for urn in urns)

    def write_decision_evidence(
        self, target: InstructionSource, evidence: DecisionEvidence
    ) -> None:
        self.evidence[target.urn] = _evidence_properties(evidence)

    def read_decision_evidence(self, target_urn: str) -> dict[str, str]:
        return dict(self.evidence[target_urn])


class LiveDataHubCatalog:
    def __init__(self, gms_url: str, token: str) -> None:
        self.gms_url = gms_url.rstrip("/")
        self.token = token
        self._source_templates: dict[str, InstructionSource] = {}

    @classmethod
    def from_env(cls) -> "LiveDataHubCatalog":
        from scripts.first_agent_context_read import resolve_token

        gms_url = os.environ.get("DATAHUB_GMS_URL", "http://localhost:8080")
        token, _ = resolve_token(gms_url)
        return cls(gms_url, token)

    def bootstrap(self, sources: Iterable[InstructionSource]) -> None:
        source_tuple = tuple(sources)
        self._source_templates = {source.urn: source for source in source_tuple}
        self._emit_supporting_entities(source_tuple)
        self._ensure_structured_property_definitions()
        for source in source_tuple:
            self._emit_source(source)
            self._set_structured_properties(source)

    def read_sources(self, urns: Iterable[str]) -> tuple[InstructionSource, ...]:
        from scripts.first_agent_context_read import McpDataHubReader

        requested = tuple(urns)
        reader = McpDataHubReader(self.gms_url, self.token)

        async def read_all() -> tuple[InstructionSource, ...]:
            results: list[InstructionSource] = []
            for urn in requested:
                metadata = await reader.call("get_entities", {"urns": urn})
                upstream = await reader.call(
                    "get_lineage",
                    {"urn": urn, "upstream": True, "max_hops": 1, "max_results": 10},
                )
                downstream = await reader.call(
                    "get_lineage",
                    {"urn": urn, "upstream": False, "max_hops": 1, "max_results": 10},
                )
                template = self._source_templates.get(urn)
                if template is None:
                    raise RuntimeError(f"No source template registered for {urn}")
                results.append(
                    _source_from_metadata(template, metadata, upstream, downstream)
                )
            return tuple(results)

        return asyncio.run(read_all())

    def write_decision_evidence(
        self, target: InstructionSource, evidence: DecisionEvidence
    ) -> None:
        custom = _source_custom_properties(target)
        custom.update(_evidence_properties(evidence))
        self._emit_dataset_properties(target, custom)

    def read_decision_evidence(self, target_urn: str) -> dict[str, str]:
        from scripts.first_agent_context_read import McpDataHubReader

        reader = McpDataHubReader(self.gms_url, self.token)
        metadata = asyncio.run(reader.call("get_entities", {"urns": target_urn}))
        custom = _find_custom_properties(metadata)
        if custom is None:
            raise RuntimeError(f"No customProperties returned for {target_urn}")
        prefix = "arbiter.last_decision."
        return {
            str(key): str(value)
            for key, value in custom.items()
            if str(key).startswith(prefix)
        }

    def _emitter(self):
        from datahub.emitter.rest_emitter import DatahubRestEmitter

        return DatahubRestEmitter(gms_server=self.gms_url, token=self.token)

    def _emit_supporting_entities(
        self, sources: tuple[InstructionSource, ...]
    ) -> None:
        from datahub.emitter.mce_builder import make_domain_urn, make_tag_urn
        from datahub.emitter.mcp import MetadataChangeProposalWrapper
        from datahub.metadata.schema_classes import (
            DomainPropertiesClass,
            TagPropertiesClass,
        )

        emitter = self._emitter()
        emitter.emit(
            MetadataChangeProposalWrapper(
                entityUrn=make_domain_urn("datahub-agent-arbiter"),
                aspect=DomainPropertiesClass(
                    name="DataHub Agent Arbiter",
                    description="Synthetic authority sources for the standalone hackathon demo.",
                ),
            )
        )
        for tag in sorted({tag for source in sources for tag in source.tags}):
            emitter.emit(
                MetadataChangeProposalWrapper(
                    entityUrn=make_tag_urn(tag),
                    aspect=TagPropertiesClass(
                        name=tag, description="DataHub Agent Arbiter synthetic metadata"
                    ),
                )
            )

    def _emit_source(self, source: InstructionSource) -> None:
        from datahub.emitter.mce_builder import make_tag_urn
        from datahub.emitter.mcp import MetadataChangeProposalWrapper
        from datahub.metadata.schema_classes import (
            DatasetLineageTypeClass,
            DeprecationClass,
            DomainsClass,
            GlobalTagsClass,
            OwnerClass,
            OwnershipClass,
            OwnershipTypeClass,
            TagAssociationClass,
            UpstreamClass,
            UpstreamLineageClass,
        )

        emitter = self._emitter()
        self._emit_dataset_properties(source, _source_custom_properties(source))
        aspects = [
            OwnershipClass(
                owners=[
                    OwnerClass(
                        owner=source.owner_urn, type=OwnershipTypeClass.DATAOWNER
                    )
                ]
            ),
            GlobalTagsClass(
                tags=[TagAssociationClass(tag=make_tag_urn(tag)) for tag in source.tags]
            ),
            DomainsClass(domains=[source.domain_urn]),
            DeprecationClass(
                deprecated=source.deprecated,
                note=(
                    f"Replaced by {source.replacement_urn}"
                    if source.replacement_urn
                    else "Current synthetic instruction source"
                ),
                actor=source.owner_urn,
            ),
            UpstreamLineageClass(
                upstreams=[
                    UpstreamClass(
                        dataset=upstream, type=DatasetLineageTypeClass.TRANSFORMED
                    )
                    for upstream in source.lineage_upstreams
                ]
            ),
        ]
        for aspect in aspects:
            emitter.emit(
                MetadataChangeProposalWrapper(entityUrn=source.urn, aspect=aspect)
            )

    def _emit_dataset_properties(
        self, source: InstructionSource, custom_properties: dict[str, str]
    ) -> None:
        from datahub.emitter.mcp import MetadataChangeProposalWrapper
        from datahub.metadata.schema_classes import DatasetPropertiesClass

        description = (
            f"Synthetic instruction source {source.source_id}. "
            f"Directive={source.directive.value}; rank={source.authority_rank}; "
            f"scope={source.action_scope}."
        )
        self._emitter().emit(
            MetadataChangeProposalWrapper(
                entityUrn=source.urn,
                aspect=DatasetPropertiesClass(
                    name=source.name,
                    description=description,
                    customProperties=custom_properties,
                ),
            )
        )

    def _ensure_structured_property_definitions(self) -> None:
        for qualified_name, value_type, display_name in PROPERTY_DEFINITIONS:
            urn = f"urn:li:structuredProperty:{qualified_name}"
            payload = {
                "qualifiedName": qualified_name,
                "valueType": f"urn:li:dataType:datahub.{value_type}",
                "description": f"DataHub Agent Arbiter {display_name.lower()}",
                "displayName": display_name,
                "cardinality": "SINGLE",
                "entityTypes": ["urn:li:entityType:datahub.dataset"],
            }
            path = (
                f"/openapi/v2/entity/structuredProperty/"
                f"{urllib.parse.quote(urn, safe='')}/propertyDefinition"
            )
            existing = self._openapi_get_optional(path)
            if existing is None:
                self._openapi_post(path, payload)
                continue

            existing_value = existing.get("value", existing)
            mismatches = {
                key: {
                    "expected": expected_value,
                    "observed": existing_value.get(key),
                }
                for key, expected_value in payload.items()
                if existing_value.get(key) != expected_value
            }
            if mismatches:
                raise RuntimeError(
                    f"Existing structured property definition does not match {urn}: "
                    f"{json.dumps(mismatches, sort_keys=True)}"
                )

    def _set_structured_properties(self, source: InstructionSource) -> None:
        """Replace the complete structuredProperties aspect with an SDK UPSERT."""
        from datahub.emitter.mcp import MetadataChangeProposalWrapper
        from datahub.metadata.schema_classes import (
            StructuredPropertiesClass,
            StructuredPropertyValueAssignmentClass,
        )

        properties = [
            StructuredPropertyValueAssignmentClass(
                propertyUrn=(
                    f"urn:li:structuredProperty:"
                    f"{PROPERTY_PREFIX}.authorityRank"
                ),
                values=[float(source.authority_rank)],
            ),
            StructuredPropertyValueAssignmentClass(
                propertyUrn=(
                    f"urn:li:structuredProperty:"
                    f"{PROPERTY_PREFIX}.directive"
                ),
                values=[source.directive.value],
            ),
            StructuredPropertyValueAssignmentClass(
                propertyUrn=(
                    f"urn:li:structuredProperty:"
                    f"{PROPERTY_PREFIX}.actionScope"
                ),
                values=[source.action_scope],
            ),
        ]
        if source.replacement_urn:
            properties.append(
                StructuredPropertyValueAssignmentClass(
                    propertyUrn=(
                        f"urn:li:structuredProperty:"
                        f"{PROPERTY_PREFIX}.replacementUrn"
                    ),
                    values=[source.replacement_urn],
                )
            )

        self._emitter().emit(
            MetadataChangeProposalWrapper(
                entityUrn=source.urn,
                changeType="UPSERT",
                aspect=StructuredPropertiesClass(properties=properties),
            )
        )

    def _openapi_headers(self, *, content_type: bool = False) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if content_type:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _openapi_get_optional(self, path: str) -> Any | None:
        request = urllib.request.Request(
            f"{self.gms_url}{path}",
            headers=self._openapi_headers(),
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 404:
                return None
            raise RuntimeError(
                f"DataHub OpenAPI GET failed with HTTP {exc.code} for {path}: {body}"
            ) from exc
        return json.loads(body) if body else None

    def _openapi_post(self, path: str, payload: dict[str, Any]) -> Any:
        request = urllib.request.Request(
            f"{self.gms_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers=self._openapi_headers(content_type=True),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"DataHub OpenAPI POST failed with HTTP {exc.code} for {path}: {body}"
            ) from exc
        return json.loads(body) if body else None


def _source_custom_properties(source: InstructionSource) -> dict[str, str]:
    return {
        "arbiter.source_id": source.source_id,
        "arbiter.action_scope": source.action_scope,
        "arbiter.directive": source.directive.value,
        "arbiter.authority_rank": str(source.authority_rank),
        "arbiter.owner_urn": source.owner_urn,
        "arbiter.deprecated": str(source.deprecated).lower(),
        "arbiter.replacement_urn": source.replacement_urn or "",
        "arbiter.lineage_upstreams": json.dumps(list(source.lineage_upstreams)),
        "arbiter.schema_version": "1",
    }


def _evidence_properties(evidence: DecisionEvidence) -> dict[str, str]:
    prefix = "arbiter.last_decision."
    return {
        f"{prefix}action": evidence.action,
        f"{prefix}decision": evidence.decision.value,
        f"{prefix}reason_code": evidence.reason_code,
        f"{prefix}source_urns": json.dumps(list(evidence.source_urns)),
        f"{prefix}authoritative_rank": (
            "" if evidence.authoritative_rank is None else str(evidence.authoritative_rank)
        ),
        f"{prefix}replacement_urns": json.dumps(list(evidence.replacement_urns)),
        f"{prefix}sha256": evidence.sha256(),
    }



def _find_custom_properties(value: Any) -> dict[str, Any] | None:
    """Normalize DataHub customProperties from MCP list or mapping form."""
    if isinstance(value, dict):
        if "customProperties" in value:
            candidate = value["customProperties"]
            if isinstance(candidate, dict):
                return {str(key): item for key, item in candidate.items()}
            if isinstance(candidate, list):
                normalized: dict[str, Any] = {}
                for item in candidate:
                    if not isinstance(item, dict):
                        continue
                    key = item.get("key")
                    if key is None:
                        continue
                    normalized[str(key)] = item.get("value")
                if normalized:
                    return normalized
        for child in value.values():
            found = _find_custom_properties(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_custom_properties(child)
            if found is not None:
                return found
    return None

def _find_first_mapping(value: Any, key: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        candidate = value.get(key)
        if isinstance(candidate, dict):
            return candidate
        for child in value.values():
            found = _find_first_mapping(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_first_mapping(child, key)
            if found is not None:
                return found
    return None


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(child, key) for child in value.values())
    if isinstance(value, list):
        return any(_contains_key(child, key) for child in value)
    return False


def _nonempty(value: Any) -> bool:
    if value in (None, "", [], {}):
        return False
    if isinstance(value, dict):
        return any(_nonempty(child) for child in value.values())
    if isinstance(value, list):
        return any(_nonempty(child) for child in value)
    return True


def _source_from_metadata(
    template: InstructionSource, metadata: Any, upstream: Any, downstream: Any
) -> InstructionSource:
    custom = _find_custom_properties(metadata)
    if custom is None:
        return replace(template, metadata_complete=False)
    try:
        directive = Directive(str(custom["arbiter.directive"]))
        rank = int(str(custom["arbiter.authority_rank"]))
        deprecated = str(custom["arbiter.deprecated"]).lower() == "true"
        lineage_upstreams = tuple(
            json.loads(str(custom.get("arbiter.lineage_upstreams", "[]")))
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return replace(template, metadata_complete=False)

    # DataHub MCP may omit the deprecation aspect when deprecated is false.
    # The explicit arbiter.deprecated custom property is authoritative for the
    # active case; a deprecated source must still expose the deprecation aspect.
    deprecation_complete = (
        _contains_key(metadata, "deprecation")
        if deprecated
        else "arbiter.deprecated" in custom
    )
    metadata_complete = all(
        (
            _contains_key(metadata, "ownership"),
            _contains_key(metadata, "domain"),
            _contains_key(metadata, "tags"),
            _contains_key(metadata, "structuredProperties"),
            deprecation_complete,
            _nonempty(upstream) or _nonempty(downstream),
        )
    )
    return replace(
        template,
        directive=directive,
        authority_rank=rank,
        deprecated=deprecated,
        replacement_urn=str(custom.get("arbiter.replacement_urn") or "") or None,
        lineage_upstreams=lineage_upstreams,
        metadata_complete=metadata_complete,
    )
