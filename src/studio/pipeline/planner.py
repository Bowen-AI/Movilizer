from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ShotTask:
    project: str
    scene: str
    shot: str
    scene_path: Path
    output_dir: Path
    compile_only: bool = False


@dataclass
class SceneTask:
    project: str
    scene: str
    scene_path: Path
    output_dir: Path
    shots: list[ShotTask] = field(default_factory=list)


@dataclass
class RunPlan:
    run_id: str
    workspace_path: Path
    scene_tasks: list[SceneTask] = field(default_factory=list)

    def flat_shot_tasks(self) -> list[ShotTask]:
        out: list[ShotTask] = []
        for scene_task in self.scene_tasks:
            out.extend(scene_task.shots)
        return out
