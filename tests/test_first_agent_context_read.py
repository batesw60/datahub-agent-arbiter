from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from first_agent_context_read import entity_name, find_first_key  # noqa: E402


def test_find_first_key_recurses() -> None:
    value = {"outer": [{"properties": {"description": "real metadata"}}]}
    assert find_first_key(value, "description") == "real metadata"


def test_entity_name_prefers_properties_name() -> None:
    value = {"urn": "urn:li:dataset:test", "properties": {"name": "orders"}}
    assert entity_name(value) == "orders"
