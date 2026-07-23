from __future__ import annotations

from collections.abc import Iterable

from .models import Decision, DecisionEvidence, Directive, InstructionSource


def evaluate_authority(
    action: str, sources: Iterable[InstructionSource]
) -> DecisionEvidence:
    ordered = tuple(sorted(sources, key=lambda source: source.urn))
    if not ordered:
        return DecisionEvidence(
            action=action,
            decision=Decision.BLOCK,
            reason_code="NO_AUTHORITY_SOURCE",
            source_urns=(),
            authoritative_rank=None,
        )

    wrong_scope = tuple(source for source in ordered if source.action_scope != action)
    if wrong_scope:
        return DecisionEvidence(
            action=action,
            decision=Decision.BLOCK,
            reason_code="ACTION_SCOPE_MISMATCH",
            source_urns=tuple(source.urn for source in wrong_scope),
            authoritative_rank=None,
        )

    incomplete = tuple(source for source in ordered if not source.metadata_complete)
    if incomplete:
        return DecisionEvidence(
            action=action,
            decision=Decision.BLOCK,
            reason_code="INCOMPLETE_AUTHORITY_METADATA",
            source_urns=tuple(source.urn for source in incomplete),
            authoritative_rank=max(source.authority_rank for source in incomplete),
        )

    deprecated = tuple(source for source in ordered if source.deprecated)
    if deprecated:
        replacements = tuple(
            sorted(
                {
                    source.replacement_urn
                    for source in deprecated
                    if source.replacement_urn
                }
            )
        )
        return DecisionEvidence(
            action=action,
            decision=Decision.BLOCK,
            reason_code="DEPRECATED_AUTHORITY_SOURCE",
            source_urns=tuple(source.urn for source in deprecated),
            authoritative_rank=max(source.authority_rank for source in deprecated),
            replacement_urns=replacements,
        )

    highest_rank = max(source.authority_rank for source in ordered)
    controlling = tuple(
        source for source in ordered if source.authority_rank == highest_rank
    )
    directives = {source.directive for source in controlling}

    if len(directives) > 1:
        return DecisionEvidence(
            action=action,
            decision=Decision.REVIEW_REQUIRED,
            reason_code="EQUAL_AUTHORITY_CONFLICT",
            source_urns=tuple(source.urn for source in controlling),
            authoritative_rank=highest_rank,
        )

    directive = next(iter(directives))
    decision = Decision.ALLOW if directive is Directive.ALLOW else Decision.BLOCK
    return DecisionEvidence(
        action=action,
        decision=decision,
        reason_code=(
            "AUTHORITATIVE_ALLOW"
            if decision is Decision.ALLOW
            else "AUTHORITATIVE_BLOCK"
        ),
        source_urns=tuple(source.urn for source in controlling),
        authoritative_rank=highest_rank,
    )
