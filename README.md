# DataHub Agent Arbiter

**DataHub Agent Arbiter is a deterministic safety layer for agent actions.** It reads authority and governance context from DataHub, refuses ambiguous or deprecated instructions, permits only a narrowly defined reversible action, and writes decision evidence back to DataHub.

- **Hackathon category:** Agents That Do Real Work
- **DataHub technologies:** DataHub OSS / Core Platform and DataHub MCP Server
- **License:** Apache-2.0
- **Audited platform:** Windows 11, PowerShell, Python 3.11, and Docker Desktop
- **Project status:** Milestones 1A and 1B independently reviewed and passed

## The problem

Agents can retrieve metadata and still make unsafe decisions. A catalog may contain current instructions, deprecated instructions, and equally authoritative sources that disagree. An agent that silently chooses one can execute the wrong action while appearing well informed.

DataHub Agent Arbiter turns DataHub metadata into a deterministic action gate. It requires complete authority metadata, surfaces conflict instead of resolving it silently, blocks deprecated sources even when they have a higher raw rank, and records the decision for the next person or agent.

## What the project demonstrates

The bounded Milestone 1B demonstration uses exactly four synthetic DataHub instruction-source datasets:

| Source | Rank | Directive | State | Expected result |
|---|---:|---|---|---|
| `review-baseline-allow` | 80 | `ALLOW` | Current | Supporting baseline |
| `owner-current-allow` | 100 | `ALLOW` | Current | `ALLOW` when evaluated alone |
| `security-current-block` | 100 | `BLOCK` | Current | `BLOCK` when evaluated alone |
| `legacy-deprecated-allow` | 120 | `ALLOW` | Deprecated, with replacement | `BLOCK / DEPRECATED_AUTHORITY_SOURCE` |

When the rank-100 owner and security sources are evaluated together, the result is `REVIEW_REQUIRED / EQUAL_AUTHORITY_CONFLICT` rather than a silent tie-break.

After a known `ALLOW` decision, the project performs one bounded action:

1. Create `.arbiter-actions/milestone-1b-marker.json`.
2. Hash the marker.
3. Write the decision evidence to DataHub.
4. Read the complete evidence properties back exactly.
5. Remove the marker only if its hash is unchanged.

No arbitrary command execution is available.

## Judge quick path

The fastest review does not require rerunning the full local stack:

1. Read [`MILESTONE_1B.md`](MILESTONE_1B.md) for the acceptance boundary.
2. Inspect [`evidence/milestone-1b-live-demo.json`](evidence/milestone-1b-live-demo.json) for the four decisions, bounded-action reversal, and exact DataHub readback.
3. Inspect [`evidence/milestone-1b-memory-demo.json`](evidence/milestone-1b-memory-demo.json) for the independent in-memory control run.
4. Review [`arbiter/policy.py`](arbiter/policy.py), [`arbiter/catalog.py`](arbiter/catalog.py), and [`arbiter/action.py`](arbiter/action.py) for the policy, DataHub adapter, and reversible action.
5. Run the tests if desired.

### Accepted evidence identities

| Artifact | SHA-256 |
|---|---|
| Memory demonstration | `2ca209c7417d7bfb2a0b0852cfe4569924afe2fef954333da3c4f51b5ee50564` |
| Live DataHub demonstration | `6a7d2bbcf03398540c6aac17dfe6663e8bee7193491d8713fbc0827063db782c` |
| Decision evidence | `b1f6d3f5470a6a2085ae94bad5873362ce9704c85e2a3cc03707fa48d6a9f805` |
| Reversible marker | `7aea40381e657775aa67ab8bf7dc9cea1f32f9010af60813d225a9fffee8de0f` |

## Supported platform

The accepted live demonstration was run on:

- Windows 11 / PowerShell
- Python `3.11.7`
- Docker Desktop with DataHub Core `v1.6.0`
- `acryl-datahub==1.6.0.15`
- `mcp-server-datahub==0.6.0`

Other platforms may work, but they were not part of the accepted live evidence. The project is intended to run on a desktop computer with Docker available.

## Standalone boundary

Runtime behavior is standalone. It does not depend on Airtable, Agent Bridge, Unified AI Work System, Zapier, OneDrive projects, external private systems, personal data, or sensitive data. The demonstration uses official DataHub sample metadata and four synthetic instruction sources created specifically for this project.

## Setup

From Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --requirement requirements.txt
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\datahub.exe docker quickstart `
  --version v1.6.0 `
  --quickstart-compose-file .\config\docker-compose.datahub-v1.6.0.yml `
  --accept-version-default
```

The pinned compose file is the official DataHub `v1.6.0` quickstart compose file. The default quickstart credentials are `datahub` / `datahub`. Set `DATAHUB_GMS_TOKEN` for unattended use; otherwise the scripts exchange `DATAHUB_USERNAME` and `DATAHUB_PASSWORD` for a one-day local token without persisting it.

## Run the project

### Fast deterministic control run

```powershell
.\.venv\Scripts\python.exe .\scripts\milestone_1b.py `
  --catalog memory `
  --repo-root . `
  --output .\evidence\milestone-1b-memory-demo.local.json
```

Use a `.local.json` output name to preserve the accepted evidence files.

### Live local-DataHub run

```powershell
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe .\scripts\milestone_1b.py `
  --catalog live `
  --repo-root . `
  --output .\evidence\milestone-1b-live-demo.local.json
```

The live run bootstraps the four synthetic source entities, reads them back through the DataHub MCP path, evaluates all four scenarios, performs and reverses the bounded marker action, writes decision evidence, and verifies exact readback.

### Tests

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

Accepted result: `pip check` passed and **21 tests passed**.

## Deterministic policy order

The policy engine evaluates stop conditions before authority rank:

1. No applicable source: `BLOCK`.
2. Wrong action scope: `BLOCK`.
3. Missing required authority metadata: `BLOCK`.
4. Deprecated source: `BLOCK`, with replacement URN when available.
5. Opposing directives at the same highest authority rank: `REVIEW_REQUIRED`.
6. Otherwise, return the single highest-ranked directive.

This ordering prevents a deprecated high-rank source from overriding a current source and prevents equal-authority conflict from being silently resolved.

## Repository map

```text
arbiter/
  action.py       bounded marker creation and hash-checked reversal
  catalog.py      in-memory and live DataHub adapters
  fixtures.py     four synthetic instruction sources and scenarios
  models.py       canonical source and decision models
  policy.py       deterministic fail-closed arbitration
config/
  arbiter_structured_properties.yaml
  docker-compose.datahub-v1.6.0.yml
evidence/
  milestone-1b-memory-demo.json
  milestone-1b-live-demo.json
scripts/
  milestone_1b.py
tests/
  test_milestone_1b.py
```

Milestone 1A evidence and scripts remain in the repository because they establish the repeated MCP metadata-read prerequisite used by Milestone 1B.

## Scope and limitations

This is a reviewed hackathon vertical slice, not a production authorization service.

- It supports one action: `CREATE_REPOSITORY_MARKER`.
- Instruction sources are synthetic and contain no personal data.
- The action is repository-local and reversible.
- The policy is explicit and deterministic; it does not infer authority from natural language.
- DataHub unavailability, incomplete metadata, writeback failure, readback mismatch, or marker mutation stops execution.
- No GUI, hosted service, arbitrary command runner, or private-system integration is included.

These limits are deliberate. They make the safety claim testable: the project shows that an agent can use DataHub context to act, refuse, escalate, and leave durable evidence without quietly inventing conflict-resolution rules.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
