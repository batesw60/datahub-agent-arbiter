import json
from pathlib import Path


REQUIRED_KEYS = {
    "verdict",
    "effective_staging_path",
    "repository_path",
    "public_repository_url",
    "environment_versions",
    "files_created",
    "files_modified",
    "commands_executed",
    "eligible_read_path",
    "eligible_read_attempts",
    "aspect_coverage",
    "sdk_supplementation",
    "datahub_health",
    "blockers",
    "scope_verification",
    "next_action",
}


def test_result_json_contract() -> None:
    result_path = Path(__file__).parents[1] / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert REQUIRED_KEYS == set(result)
    assert result["verdict"] in {"PASS", "FAIL", "BLOCKED"}
    assert isinstance(result["next_action"], str) and result["next_action"].strip()
