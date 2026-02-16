from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass
class ShotEvalContext:
    run_id: str
    project: str
    scene: str
    shot: str
    shot_dir: Path
    frames: list[Path]
    clip_path: Path
    prompt: str
    negative_prompt: str
    metadata: dict[str, Any]


class Judge(Protocol):
    name: str

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        ...
