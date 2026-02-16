from __future__ import annotations

from pathlib import Path
from typing import Any

from ..utils import load_json, save_json, stable_hash


def _cache_file(compiled_dir: Path) -> Path:
    return compiled_dir / "cache_state.json"


def compute_signature(payload: dict[str, Any]) -> str:
    return stable_hash(payload)


def read_cache(compiled_dir: Path) -> dict[str, Any]:
    p = _cache_file(compiled_dir)
    if not p.exists():
        return {}
    return load_json(p)


def write_cache(compiled_dir: Path, state: dict[str, Any]) -> None:
    save_json(_cache_file(compiled_dir), state)


def should_skip(
    compiled_dir: Path,
    task_key: str,
    signature: str,
    required_outputs: list[Path],
    resume: bool,
) -> bool:
    if not resume:
        return False
    state = read_cache(compiled_dir)
    if state.get(task_key) != signature:
        return False
    return all(p.exists() for p in required_outputs)


def update_task_signature(compiled_dir: Path, task_key: str, signature: str) -> None:
    state = read_cache(compiled_dir)
    state[task_key] = signature
    write_cache(compiled_dir, state)
