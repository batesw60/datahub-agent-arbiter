# Milestone 1A Run Log

## Run identity and verdict

- Run type: manual Codex recovery
- Date: 2026-07-21
- Authorized working area: `D:\OneDrive\1.2 AI General\DataHub Agent Arbiter`
- Effective staging path: `D:\OneDrive\1.2 AI General\DataHub Agent Arbiter\datahub-agent-arbiter-m1a-2026-07-21`
- Repository path: `D:\OneDrive\1.2 AI General\DataHub Agent Arbiter\datahub-agent-arbiter-m1a-2026-07-21\datahub-agent-arbiter`
- Initial recovery verdict: **BLOCKED** (cleared at `2026-07-21T18:30:11.3494969Z`)
- Final Milestone 1A verdict: **PASS**
- Final reason: DataHub OSS `v1.6.0` is healthy and DataHub MCP Server 0.6.0 completed consecutive timestamped reads of real official-sample metadata. The original Docker blocker and all subsequent recovery evidence are preserved below.

The previous Agent Bridge sandbox failure is not treated as implementation evidence. It created no project files, executed no successful project command, did not start DataHub, and performed no eligible read.

## Timestamped execution evidence

### 1. Read-only path inspection

Timestamp: immediately before `2026-07-21T18:19:29Z`.

Command:

```powershell
$base = 'D:\OneDrive\1.2 AI General\DataHub Agent Arbiter'; if (Test-Path -LiteralPath $base) { Get-Item -LiteralPath $base | Format-List FullName,Attributes,CreationTime,LastWriteTime; Get-ChildItem -LiteralPath $base -Force | Select-Object Name,FullName,Mode,Length,LastWriteTime } else { Write-Output 'AUTHORIZED_WORKING_AREA_MISSING' }; $stage = Join-Path $base 'datahub-agent-arbiter-m1a-2026-07-21'; $repo = Join-Path $stage 'datahub-agent-arbiter'; Write-Output ('STAGE_EXISTS=' + (Test-Path -LiteralPath $stage)); Write-Output ('REPO_EXISTS=' + (Test-Path -LiteralPath $repo))
```

Trimmed output:

```text
AUTHORIZED_WORKING_AREA_MISSING
STAGE_EXISTS=False
REPO_EXISTS=False
```

No conflict existed. The authorized directory, staging directory, repository, `scripts`, and `tests` were then created with `New-Item -ItemType Directory`; no existing content was overwritten, moved, renamed, or deleted.

Repository initialization command:

```powershell
git init -b main
```

The first sandboxed attempt at approximately `2026-07-21T18:25Z` failed with `.git: Permission denied`. Recovery used narrowly elevated filesystem permission for the same exact command and succeeded:

```text
Initialized empty Git repository in D:/OneDrive/1.2 AI General/DataHub Agent Arbiter/datahub-agent-arbiter-m1a-2026-07-21/datahub-agent-arbiter/.git/
```

The elevated helper runs under a different Windows SID, so a later ordinary `git status --short` reported Git's `dubious ownership` protection. No global Git configuration was changed; final status verification used a one-command `safe.directory` override only.

### 2. Environment audit

Command sequence:

```powershell
python --version
docker version
docker info
docker compose version
git --version
[System.IO.DriveInfo]::new('D')
gh --version
gh auth status
```

Relevant trimmed outputs:

```text
2026-07-21T18:19:29.8615230Z  Python 3.11.7
2026-07-21T18:19:29.8880235Z  Docker client 27.3.1, API 1.47, context default
2026-07-21T18:19:30.3886647Z  docker info: Server section absent
WARNING: Error loading config file: C:\Users\William Frescas\.docker\config.json: Access is denied.
error during connect: open //./pipe/docker_engine: The system cannot find the file specified.
2026-07-21T18:19:31.9037087Z  Docker Compose v2.29.7-desktop.1
2026-07-21T18:19:32.1359393Z  git version 2.40.0.windows.1
2026-07-21T18:19:32.5082524Z  gh version 2.96.0 (2026-07-02)
2026-07-21T18:19:32.7102539Z  gh auth status: token for batesw60 is invalid
2026-07-21T18:20:32.4248817Z  Docker Desktop file/product version 4.35.1.173168
2026-07-21T18:20:32.4738817Z  com.docker.service: Stopped; StartType: Manual
2026-07-21T18:20:32.4948900Z  D: total 2,048,391,114,752 bytes; free 1,596,117,204,992 bytes (1486.5 GiB)
```

Docker processes `Docker Desktop` and `com.docker.backend` were absent. No GUI was launched and Docker was not installed or reconfigured.

## Version selection and official compatibility evidence

Selected released versions:

| Component | Pin | Evidence and compatibility rationale |
|---|---:|---|
| DataHub OSS | `v1.6.0` | Official 1.6.0 quickstart documents the exact pin command `datahub docker quickstart --version v1.6.0`. |
| `acryl-datahub[datahub-rest]` | `1.6.0.6` | Final compatible pin. Dependency resolution proved Agent Context Kit 1.6.0.15 requires this exact version; MCP Server 0.6.0 accepts it through `acryl-datahub>=1.3.1.7`. The initial latest-version selection of 1.6.0.15 is preserved in the resumed-run recovery narrative. |
| DataHub MCP Server | `0.6.0` | PyPI lists 0.6.0 as the latest release. Its official tagged `pyproject.toml` requires Python `>=3.11` and `acryl-datahub>=1.3.1.7`; Python 3.11.7 and SDK 1.6.0.15 satisfy those constraints. |
| Agent Context Kit | `1.6.0.15` | PyPI lists 1.6.0.15 as the latest stable release, aligned with `acryl-datahub` 1.6.0.15; requires Python `>=3.9`. |

Official sources consulted on 2026-07-21:

- DataHub Quickstart 1.6.0: https://docs.datahub.com/docs/quickstart
- DataHub MCP Server guide 1.6.0: https://docs.datahub.com/docs/features/feature-guides/mcp
- DataHub OSS releases: https://github.com/datahub-project/datahub/releases
- MCP Server 0.6.0 tagged dependency declaration: https://raw.githubusercontent.com/acryldata/mcp-server-datahub/v0.6.0/pyproject.toml
- `acryl-datahub` release history: https://pypi.org/project/acryl-datahub/
- `mcp-server-datahub` release history: https://pypi.org/project/mcp-server-datahub/
- Agent Context Kit release and Python requirements: https://pypi.org/project/datahub-agent-context/

The official quickstart requires Docker and Compose v2, a launched Docker engine, Python 3.10+, and at least 13 GB disk. Python, Compose, and disk requirements pass; the launched-engine requirement fails. The MCP guide confirms the self-hosted MCP server is available for DataHub Core and reads from the GMS endpoint.

## Startup, health, and recovery attempts

- Intended exact startup command: `.\.venv\Scripts\datahub.exe docker quickstart --version v1.6.0 --accept-version-default`
- Startup command executed: **no**
- Recovery attempts: environment/status checks only; no GUI or service start was attempted because the brief identifies a missing human-only prerequisite as a hard stop.
- Container status: not created/not inspected because startup could not begin.
- Health checks: not run.
- Localhost UI availability: not tested; DataHub was not started.
- Sample metadata: not loaded.

Exact prerequisite: the repository owner must launch Docker Desktop and wait until its Linux container engine is running such that `docker info` returns a populated `Server` section and `//./pipe/docker_engine` is reachable. Docker should have at least the official tested allocation of 2 CPUs, 8 GB RAM, 2 GB swap, and 13 GB disk.

## Initial blocked-run eligible metadata-read evidence

- Primary eligible path: DataHub MCP Server 0.6.0, planned but not attempted.
- Fallback eligible path: Agent Context Kit 1.6.0.15, planned only if MCP cannot work against the pinned deployment; not attempted.
- Eligible read attempt 1: not performed.
- Eligible read attempt 2: not performed.
- SDK supplementation: none.

No MCP failure occurred; therefore the Agent Context Kit fallback rule was not triggered. The blocking prerequisite prevented DataHub from existing as a read target.

Aspect-by-aspect coverage:

| Aspect | Status | Evidence |
|---|---|---|
| Ownership | Not tested — blocked | No eligible read target. |
| Lineage | Not tested — blocked | No eligible read target. |
| Deprecation | Not tested — blocked | No eligible read target. |
| Replacement information | Not tested — blocked | No eligible read target. |
| Domains | Not tested — blocked | No eligible read target. |
| Tags | Not tested — blocked | No eligible read target. |
| Structured properties | Not tested — blocked | No eligible read target. |

Because local DataHub is not healthy and two consecutive eligible reads do not exist, PASS is prohibited. FAIL is inappropriate because no compatible configuration was fully executed. The correct verdict is BLOCKED.

## GitHub publication

GitHub publication is independently **BLOCKED**. `gh auth status` reported an invalid token for the active account, so no repository creation, push, public-visibility check, or license-detection check was attempted. This publication blocker does not change the local blocker reasoning.

## Files created or modified

Created:

- `.git/config`
- `.git/description`
- `.git/HEAD`
- `.git/hooks/applypatch-msg.sample`
- `.git/hooks/commit-msg.sample`
- `.git/hooks/fsmonitor-watchman.sample`
- `.git/hooks/post-update.sample`
- `.git/hooks/pre-applypatch.sample`
- `.git/hooks/pre-commit.sample`
- `.git/hooks/pre-merge-commit.sample`
- `.git/hooks/pre-push.sample`
- `.git/hooks/pre-rebase.sample`
- `.git/hooks/pre-receive.sample`
- `.git/hooks/prepare-commit-msg.sample`
- `.git/hooks/push-to-checkout.sample`
- `.git/hooks/update.sample`
- `.git/info/exclude`
- `.gitignore`
- `LICENSE`
- `README.md`
- `RUN_LOG.md`
- `requirements.txt`
- `result.json`
- `scripts/mcp_probe.py`
- `scripts/mcp_read.py`
- `scripts/sdk_supplement.py`
- `scripts/verify_environment.ps1`
- `tests/test_result_schema.py`

Generated ignored runtime directories: `.venv/` (isolated dependency environment) and `.runtime-home/` (local DataHub CLI state). Their contents are dependency/runtime artifacts, not copied project implementation material.

Modified during the resumed run: `.gitignore`, `README.md`, `RUN_LOG.md`, `requirements.txt`, and `result.json`.

## Final scope verification

- Every created file is inside the authorized repository path.
- No Unified AI Work System implementation material was read or copied.
- No dependency on Unified AI Work System, HQ, Airtable, Agent Bridge, Zapier, personal data, or sensitive data was introduced.
- No synthetic Arbiter entity was created.
- No `policy.py`, policy decision logic, action gating, writeback, GUI, video, integration, or Milestone 1B work was created.
- This log contains reproducible commands, timestamps, outputs, errors, recovery reasoning, version evidence, eligible-path status, aspect coverage, and file accounting.

Validation commands:

```powershell
$raw = Get-Content -Raw -LiteralPath '.\result.json'; $null = $raw | ConvertFrom-Json -ErrorAction Stop
$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest -q -p no:cacheprovider
git -c safe.directory='D:/OneDrive/1.2 AI General/DataHub Agent Arbiter/datahub-agent-arbiter-m1a-2026-07-21/datahub-agent-arbiter' status --short
```

Validation output: `result.json: valid JSON`; required JSON keys missing: none; `1 passed in 0.01s`; final Git status listed the eight project paths as untracked (`scripts/` and `tests/` are directory summaries) because no commit was authorized.

## Resumed run — cleared prerequisite and final PASS

### Docker prerequisite cleared

At `2026-07-21T18:29:48.5171010Z`, the ordinary sandbox could see the Docker client but received `Access is denied` for the Docker config and engine named pipe. This was a sandbox boundary, not an engine failure. The same read-only checks were retried with narrow Docker permission.

Exact command sequence:

```powershell
docker context show
docker version
docker info
docker compose version
```

Successful evidence at `2026-07-21T18:30:11.3494969Z`:

```text
context: desktop-linux
client: 27.3.1
server: Docker Desktop 4.35.1 (173168), Engine 27.3.1
OS/Arch: linux/amd64; Architecture: x86_64
CPUs: 24; Total Memory: 31.22 GiB
Docker Compose: v2.29.7-desktop.1
```

### Dependency installation and compatibility correction

The environment was created with:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The first install failed because pip could not verify this host's HTTPS proxy certificate. A retry using only official PyPI hosts reached dependency resolution:

```powershell
.\.venv\Scripts\python.exe -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

That resolution proved the original SDK pin was not jointly installable: Agent Context Kit `1.6.0.15` requires `acryl-datahub[datahub-rest]==1.6.0.6`. `requirements.txt` was corrected from SDK `1.6.0.15` to `1.6.0.6`; MCP Server 0.6.0 accepts `acryl-datahub>=1.3.1.7`. The corrected released set installed successfully. `pip-system-certs==5.3` was pinned so Python HTTPS clients could use the Windows certificate store behind the proxy.

Installed eligible versions:

```text
DataHub CLI / acryl-datahub: 1.6.0.6
mcp-server-datahub: 0.6.0
datahub-agent-context: 1.6.0.15
Python: 3.11.7
```

### Pinned DataHub startup and recovery

All DataHub CLI state was redirected to `.runtime-home` inside the authorized repository. Exact startup command:

```powershell
$env:USERPROFILE='<repository>\.runtime-home'
$env:HOME='<repository>\.runtime-home'
$env:DATAHUB_TELEMETRY_ENABLED='false'
.\.venv\Scripts\datahub.exe docker quickstart --version v1.6.0 --accept-version-default
```

The first startup attempt selected the correct plan (`composefile_git_ref='v1.6.0'`, `docker_tag='v1.6.0'`, `mysql_tag='8.2'`) but failed to download the compose file because of the proxy certificate. After installing the pinned certificate helper, the identical command pulled the official images and started every service. The CLI then exited nonzero only while printing the final Unicode `✔` under CP-1252; direct health checks proved startup had completed.

Health evidence at `2026-07-21T18:39:47.0686328Z` and final stability evidence at `2026-07-21T18:48:50.1772380Z`:

```text
datahub-datahub-actions-quickstart-1   acryldata/datahub-actions:v1.6.0-slim     running
datahub-frontend-quickstart-1          acryldata/datahub-frontend-react:v1.6.0   healthy
datahub-datahub-gms-quickstart-1       acryldata/datahub-gms:v1.6.0              healthy
datahub-system-update-quickstart-1     acryldata/datahub-upgrade:v1.6.0          exited 0 (expected one-time job)
datahub-kafka-broker-1                 confluentinc/cp-kafka:8.0.0               healthy
datahub-mysql-1                        mysql:8.2                                  healthy
datahub-opensearch-1                   opensearchproject/opensearch:2.19.3        healthy
datahub docker check: ✔ No issues detected
GMS http://localhost:8080/health: HTTP 200
UI http://localhost:9002: HTTP 200, Content-Type text/html
```

### Official sample metadata

Exact documented commands:

```powershell
.\.venv\Scripts\datahub.exe init --username datahub --password datahub
.\.venv\Scripts\datahub.exe datapack load showcase-ecommerce
```

CLI initialization succeeded at `2026-07-21T18:40:12.0976782Z`. The Windows datapack invocation downloaded all three official files but failed because its file source treated the Windows `C:` prefix as a filesystem scheme (`KeyError: Did not find a registered class for c`). The same official datapack was retried without modification through the already-running official DataHub Linux actions container:

```powershell
docker exec datahub-datahub-actions-quickstart-1 datahub datapack load showcase-ecommerce
```

The Linux retry completed at approximately `2026-07-21T18:41:42Z`:

```text
Data pack 'showcase-ecommerce' loaded successfully.
File 1: 12 events; 5 structured-property definitions
File 2: real catalog entities including 67 datasets, 55 upstreamLineage aspects,
        20 dataset ownership aspects, 16 dataset domains, 67 dataset globalTags,
        and 67 dataset structuredProperties aspects
File 3: 56 events including 18 documents
```

No synthetic Arbiter entity was created; only DataHub's official sample was loaded.

### Primary eligible path: DataHub MCP Server

The primary path worked, so Agent Context Kit fallback was not attempted. MCP Server ran over stdio with `TOOLS_IS_MUTATION_ENABLED=false` and `TOOLS_IS_USER_ENABLED=false`. Published read tools were:

```text
search, get_lineage, get_dataset_queries, get_entities, list_schema_fields,
get_lineage_paths_between, search_documents, grep_documents
```

Reproducible command form (the local token was loaded from `.runtime-home/.datahubenv` without logging it):

```powershell
$env:DATAHUB_GMS_URL='http://localhost:8080'
$env:DATAHUB_GMS_TOKEN='<loaded locally; redacted>'
.\.venv\Scripts\python.exe .\scripts\mcp_read.py --attempt 1
.\.venv\Scripts\python.exe .\scripts\mcp_read.py --attempt 2
.\.venv\Scripts\python.exe .\scripts\mcp_read.py --attempt 3
```

#### Eligible read 1 — success

- Started: `2026-07-21T18:45:33.836517+00:00`
- Completed: `2026-07-21T18:45:37.449587+00:00`
- Dataset: `urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.ORDER_ENTRY_DB.analytics.order_details,PROD)`
- Search: 5 real datasets matched owner + domain + tag requirements.
- Lineage: positive upstream result.
- Entity read: success; returned populated governance and structured-property metadata.

#### Eligible read 2 — consecutive success

- Started: `2026-07-21T18:46:38.397344+00:00`
- Completed: `2026-07-21T18:46:41.408831+00:00`
- Same real dataset and MCP path.
- Search: 5 qualifying datasets.
- Lineage: positive upstream result.
- Entity read: success with populated ownership, domain, tags, and structured properties.

#### Coverage pass 3 — success

- Started: `2026-07-21T18:47:30.044670+00:00`
- Completed: `2026-07-21T18:47:32.966477+00:00`
- Upstream lineage total: 11 real datasets, including orders, order items, products, customers, promotions, addresses, countries, inventories, product categories, regions, and warehouses.
- Mutation tools remained disabled.

Aspect coverage from the eligible MCP path:

| Aspect | Result | Exact trimmed evidence |
|---|---|---|
| Ownership | Populated | `ownership.owners` returned DataHub SE Team and Data Platform Team ownership records. |
| Lineage | Populated | `get_lineage` returned `upstreams.total = 11` and 11 dataset URNs. |
| Deprecation | Explicitly tested; no populated official-sample record | MCP `search` with `deprecated = true` succeeded and returned `total = 0`; facet `Deprecated=true` count 0. |
| Replacement information | Explicitly tested; no populated official-sample record | MCP document search `/q replacement OR deprecated OR deprecation` succeeded and returned `total = 0`. |
| Domains | Populated | Domain URN `urn:li:domain:b2fd91.1caf2b7c-ca73-4708-bdec-6687d78cab0e`, name `Data Platform Team`. |
| Tags | Populated | `PII_Data` and `Authoritative Source`. |
| Structured properties | Populated | `showcase.dataFreshnessSla` with value `Daily`; additional structured-property entries were returned. |

### SDK supplementation

The SDK was not used to satisfy either eligible read. It supplemented only the negative deprecation/replacement test:

```powershell
.\.venv\Scripts\python.exe .\scripts\sdk_supplement.py
```

At `2026-07-21T18:48:14.185253+00:00`, the SDK confirmed that the selected dataset has no `Deprecation` aspect. The released model exposes `deprecated`, `decommissionTime`, `note`, `actor`, and `replacement`, confirming the absence is sample data state rather than an untested field.

### Final reasoning

Local Milestone 1A is **PASS** because DataHub is healthy, the primary eligible MCP path successfully retrieved real metadata, attempts 1 and 2 succeeded consecutively with separate timestamps, and exact aspect-by-aspect evidence is preserved. Agent Context Kit was correctly not attempted because MCP worked. GitHub publication alone remains BLOCKED by the invalid GitHub CLI token and does not invalidate the local PASS.

### Final validation

Executed after updating the final evidence:

```text
result.json: valid JSON; verdict=PASS; eligible attempts=3; healthy=true
pytest: 1 passed in 0.01s
files outside authorized working area: 0
project-created policy.py files (excluding dependency/runtime directories): 0
token-shaped strings in project/evidence files (excluding runtime secrets): 0
```

The only `policy.py` anywhere below the repository is the third-party `.venv/Lib/site-packages/win32com/server/policy.py` installed transitively by the pinned environment; no Arbiter policy file or logic exists.
