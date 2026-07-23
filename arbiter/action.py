from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

MARKER_RELATIVE_PATH = Path(".arbiter-actions") / "milestone-1b-marker.json"


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def create_marker(repo_root: Path, payload: dict[str, Any]) -> tuple[Path, str]:
    path = repo_root.resolve() / MARKER_RELATIVE_PATH
    expected = canonical_bytes(payload)
    if path.exists():
        existing = path.read_bytes()
        if existing != expected:
            raise RuntimeError(f"Refusing to overwrite nonmatching marker: {path}")
        return path, sha256_bytes(existing)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(expected)
    return path, sha256_bytes(expected)


def revert_marker(repo_root: Path, expected_sha256: str) -> Path:
    path = repo_root.resolve() / MARKER_RELATIVE_PATH
    if not path.exists():
        raise RuntimeError(f"Marker does not exist: {path}")
    observed = sha256_bytes(path.read_bytes())
    if observed != expected_sha256:
        raise RuntimeError(
            f"Refusing to remove changed marker: expected {expected_sha256}, observed {observed}"
        )
    path.unlink()
    try:
        path.parent.rmdir()
    except OSError:
        pass
    return path
