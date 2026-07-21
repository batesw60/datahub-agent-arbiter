# DataHub Agent Arbiter — Milestone 1A

Standalone recovery scaffold for validating read-only agent access to a local DataHub OSS catalog. This repository contains only Milestone 1A evidence and reproducibility helpers. It has no dependency on Unified AI Work System, HQ, Airtable, Agent Bridge, Zapier, personal data, or sensitive data.

## Current result

`PASS` on 2026-07-21 for local Milestone 1A. Docker Desktop was restarted, DataHub OSS `v1.6.0` became healthy, the official `showcase-ecommerce` datapack loaded, and DataHub MCP Server 0.6.0 completed three successful real-metadata reads. Attempts 1 and 2 were consecutive and separately timestamped. GitHub publication remains an independently blocked substep because the configured GitHub CLI token is invalid.

See `RUN_LOG.md` for timestamps, exact commands, trimmed outputs, official compatibility evidence, and scope verification. `result.json` is the machine-readable result.

## Pinned compatibility set

- DataHub OSS: `v1.6.0`
- `acryl-datahub[datahub-rest]`: `1.6.0.6`
- DataHub MCP Server: `mcp-server-datahub==0.6.0` (primary eligible path)
- Agent Context Kit: `datahub-agent-context==1.6.0.15` (fallback eligible path)

The official DataHub 1.6.0 quickstart documents `datahub docker quickstart --version v1.6.0`. MCP Server 0.6.0 requires Python 3.11+ and `acryl-datahub>=1.3.1.7`. Agent Context Kit 1.6.0.15 requires `acryl-datahub[datahub-rest]==1.6.0.6`, so the corrected SDK pin satisfies both eligible technologies while remaining in the 1.6.0 release family.

## Reproduction after the prerequisite is restored

Run from this repository in PowerShell. These commands are recorded but were not executed during this blocked run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip wheel setuptools
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\datahub.exe docker quickstart --version v1.6.0 --accept-version-default
.\.venv\Scripts\datahub.exe init --username datahub --password datahub
.\.venv\Scripts\datahub.exe datapack load showcase-ecommerce
```

The `showcase-ecommerce` datapack is the official sample documented by DataHub. After DataHub is healthy, configure the primary self-hosted MCP path with `DATAHUB_GMS_URL=http://localhost:8080` and a local DataHub token, keep mutation tools disabled, and perform two separately timestamped reads. Attempt Agent Context Kit only if MCP cannot work against the pinned deployment.

## Scope exclusions

This milestone deliberately does not include policy logic, ALLOW/BLOCK/REVIEW_REQUIRED decisions, action gating, decision writeback, a GUI, a submission video, integrations, or synthetic Arbiter entities.

## License

Apache License 2.0. See `LICENSE`.
