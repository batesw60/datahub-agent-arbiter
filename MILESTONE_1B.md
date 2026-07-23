# Milestone 1B — Bounded Authority-Arbitration Vertical Slice

## Final status

**PASS — closed July 22, 2026.**

The implementation, evidence, dependencies, tests, and corrected live read-only DataHub verification completed independent review. Publication is a separate repository operation and does not change the accepted implementation behavior or evidence identities.

## Goal

Prove that four synthetic DataHub instruction sources can be read as authority context, evaluated deterministically, used to gate one reversible local action, and receive exact decision evidence back in DataHub.

## Implemented behavior

1. Exactly four synthetic instruction-source datasets are registered.
2. Each source carries ownership, domain, tags, documentation, lineage, deprecation metadata, custom properties, and typed structured properties.
3. The deterministic scenarios produce:
   - `ALLOW`
   - authoritative `BLOCK`
   - `REVIEW_REQUIRED / EQUAL_AUTHORITY_CONFLICT`
   - deprecated-source `BLOCK / DEPRECATED_AUTHORITY_SOURCE`, including a replacement URN
4. Incomplete authority metadata fails closed.
5. The marker action executes only after `ALLOW`.
6. The marker is removed only when its content hash remains unchanged.
7. Decision evidence is written to DataHub and the complete property set is read back exactly.
8. `pip check` passes.
9. All 21 repository tests pass.
10. Runtime has no Airtable, Agent Bridge, Unified AI Work System, Zapier, external private system, or personal-data dependency.

## Accepted evidence

| Evidence | SHA-256 |
|---|---|
| `evidence/milestone-1b-memory-demo.json` | `2ca209c7417d7bfb2a0b0852cfe4569924afe2fef954333da3c4f51b5ee50564` |
| `evidence/milestone-1b-live-demo.json` | `6a7d2bbcf03398540c6aac17dfe6663e8bee7193491d8713fbc0827063db782c` |
| Decision evidence | `b1f6d3f5470a6a2085ae94bad5873362ce9704c85e2a3cc03707fa48d6a9f805` |
| Reversible marker | `7aea40381e657775aa67ab8bf7dc9cea1f32f9010af60813d225a9fffee8de0f` |

Reviewed repository baseline before publication:

```text
1406db27f4557f65c0d4c5184ad88d6274aded3a
```

## Demonstrated source set

| Source ID | Rank | Directive | Special condition |
|---|---:|---|---|
| `review-baseline-allow` | 80 | `ALLOW` | Baseline source |
| `owner-current-allow` | 100 | `ALLOW` | Known bounded-action authorization |
| `security-current-block` | 100 | `BLOCK` | Equal-rank conflict with owner source |
| `legacy-deprecated-allow` | 120 | `ALLOW` | Deprecated; replacement is `owner-current-allow` |

The deprecated source blocks despite having the highest raw rank. The two current rank-100 sources require review when evaluated together.

## Readback scope

`decision_evidence_readback` intentionally verifies the DataHub write/read round trip for the known `owner-current-allow` decision used by the reversible marker action. It is not represented as arbitration over all four sources. The separate combined-source scenario verifies that `owner-current-allow` plus `security-current-block` produces `REVIEW_REQUIRED / EQUAL_AUTHORITY_CONFLICT`.

## Stop conditions

Stop without executing the action when:

- DataHub is unavailable.
- A required source cannot be read.
- Required authority metadata is missing.
- A source is deprecated.
- Equal highest-ranked sources conflict.
- The marker already exists with different content.
- Decision-evidence writeback fails.
- Readback differs from the written evidence.
- The marker changes before reversal.

## Reproduction commands

Memory control:

```powershell
.\.venv\Scripts\python.exe .\scripts\milestone_1b.py `
  --catalog memory `
  --repo-root . `
  --output .\evidence\milestone-1b-memory-demo.local.json
```

Live local DataHub:

```powershell
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe .\scripts\milestone_1b.py `
  --catalog live `
  --repo-root . `
  --output .\evidence\milestone-1b-live-demo.local.json
```

Validation:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

## Explicit exclusions

No GUI, deployment, arbitrary command execution, multi-action workflow, natural-language policy inference, external service calls, personal data, production catalog entities, or integration with private work systems.
