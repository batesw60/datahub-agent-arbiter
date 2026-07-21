# DataHub Agent Arbiter

DataHub Agent Arbiter is a standalone hackathon project that tests whether an agent can obtain real, repeatable metadata context from a local open-source DataHub catalog before later authority-arbitration work begins.

## Standalone boundary

This repository is independently runnable. It does not read, copy, import, modify, or depend on Unified AI Work System, Airtable, Agent Bridge, Zapier, OneDrive projects, personal data, or sensitive data. Only official DataHub sample metadata is permitted in Milestone 1A.

## Current milestone

Milestone 1A only: bring up a pinned local DataHub stack, perform two consecutive qualifying read-only requests through the DataHub MCP Server, and document verified metadata coverage. This milestone intentionally contains no synthetic Arbiter entities, policy logic, action gating, decision writeback, or GUI.

## Setup status

Milestone 1A: **PASS**. DataHub Core v1.6.0 is healthy locally, the UI responds, official sample metadata is present, and the DataHub MCP Server returned the same real entity metadata twice consecutively. The technical and publication gates have passed; only final independent verification of the corrected Milestone 1A evidence package remains before Milestone 1B.

Public repository: [`batesw60/datahub-agent-arbiter`](https://github.com/batesw60/datahub-agent-arbiter). GitHub reports it as public with default branch `main` and detects `LICENSE` as Apache License 2.0 (`Apache-2.0`). See `RUN_LOG.md` for timestamped command evidence and `result.json` for the structured outcome.

## Why this project exists

DataHub provides metadata context, but DataHub Agent Arbiter adds deterministic authority arbitration before agent actions. Milestone 1A proves only the metadata-context prerequisite; authority arbitration is outside this milestone.

## Pinned components

- DataHub Core: `v1.6.0`
- `acryl-datahub`: `1.6.0.15`
- DataHub MCP Server (`mcp-server-datahub`): `0.6.0`
- Python: `3.11.7` on the audited host

The versions were selected from the official [DataHub 1.6.0 documentation](https://docs.datahub.com/), [DataHub Core releases](https://github.com/datahub-project/datahub/releases/tag/v1.6.0), [DataHub MCP documentation](https://docs.datahub.com/docs/features/feature-guides/mcp), [MCP Server tags](https://github.com/acryldata/mcp-server-datahub/tags), and PyPI release records for [`acryl-datahub`](https://pypi.org/project/acryl-datahub/) and [`mcp-server-datahub`](https://pypi.org/project/mcp-server-datahub/0.6.0/).

Compatibility basis: MCP Server 0.6.0 requires Python 3.11+ and declares `acryl-datahub>=1.3.1.7`; the selected CLI/SDK is a stable patch release in the same `1.6.0` line as DataHub Core. Compatibility uncertainty is limited to patch-level CLI changes after the Core `v1.6.0` tag; the qualifying test verifies the combination rather than assuming it.

## Setup

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --requirement requirements.txt
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\datahub.exe docker quickstart --version v1.6.0 --quickstart-compose-file .\config\docker-compose.datahub-v1.6.0.yml --accept-version-default
```

The pinned compose file is the official DataHub `v1.6.0` quickstart compose file (SHA-256 `ba39d779cd0e066553b5f4673384ece3d6a872e2245983525fc71e2ece1b5077`). The default quickstart credentials are `datahub` / `datahub`. For unattended use, set `DATAHUB_GMS_TOKEN`; otherwise the scripts exchange `DATAHUB_USERNAME` / `DATAHUB_PASSWORD` (defaulting to the documented quickstart credentials) for a one-day token without persisting it.

Run the qualifying reads:

```powershell
.\.venv\Scripts\python.exe .\scripts\first_agent_context_read.py --attempt 1 --output .\evidence\agent-context-read-1.json
.\.venv\Scripts\python.exe .\scripts\first_agent_context_read.py --attempt 2 --output .\evidence\agent-context-read-2.json
.\.venv\Scripts\python.exe .\scripts\metadata_coverage_read.py --output .\evidence\metadata-coverage.json
```

The first two commands must be run consecutively. They use MCP over stdio and invoke the read-only `get_entities` tool. Mutation tools are explicitly disabled.

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

## Verified metadata coverage

| Metadata | Result | Eligible MCP operation |
|---|---|---|
| Ownership | `DIRECTLY_AVAILABLE` | `get_entities` |
| Lineage | `AVAILABLE_WITH_ADDITIONAL_QUERY` | `get_lineage` (one upstream and one downstream entity verified) |
| Deprecation status | `NOT_VERIFIED` | `get_entities` plus `search` with `deprecated = true`; the official sample returned zero deprecated entities |
| Replacement reference | `NOT_AVAILABLE` | MCP 0.6.0's deprecation fragment has no replacement field |
| Domain | `DIRECTLY_AVAILABLE` | `get_entities` |
| Tags | `DIRECTLY_AVAILABLE` | `get_entities` |
| Structured properties | `DIRECTLY_AVAILABLE` | `get_entities` |
| Description or documentation | `DIRECTLY_AVAILABLE` | `get_entities` |

No Python SDK aspect supplement was required. The CLI/SDK library is used only to perform the documented local credential exchange; all qualifying metadata and coverage reads use MCP tools.
