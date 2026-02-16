from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from ..utils import ensure_dir, get_logger, load_json, save_json
from .audio import ClippingJudge, LoudnessJudge
from .base import ShotEvalContext
from .image import (
    DiversityJudge,
    IdentitySimilarityJudge,
    PromptAdherenceJudge,
    QualityJudge,
    SafetyJudge,
)
from .video import ClipStabilityJudge, FlickerJudge, TemporalIdentityConsistencyJudge

logger = get_logger("judges.runner")


def _collect_shots(run_root: Path) -> list[tuple[str, str, str, Path]]:
    out: list[tuple[str, str, str, Path]] = []
    if not run_root.exists():
        return out

    for project_dir in sorted(p for p in run_root.iterdir() if p.is_dir()):
        for scene_dir in sorted(p for p in project_dir.iterdir() if p.is_dir()):
            if scene_dir.name in {"compiled", "audio"}:
                continue
            for shot_dir in sorted(p for p in scene_dir.iterdir() if p.is_dir()):
                if shot_dir.name.startswith("shot_"):
                    out.append((project_dir.name, scene_dir.name, shot_dir.name, shot_dir))
    return out


def evaluate_run(output_root: Path, run_id: str) -> Path:
    run_root = output_root / run_id
    eval_root = output_root / "eval" / run_id
    ensure_dir(eval_root)

    judges = [
        IdentitySimilarityJudge(),
        PromptAdherenceJudge(),
        QualityJudge(),
        DiversityJudge(),
        SafetyJudge(),
        TemporalIdentityConsistencyJudge(),
        ClipStabilityJudge(),
        FlickerJudge(),
        LoudnessJudge(),
        ClippingJudge(),
    ]

    shot_rows: list[dict[str, Any]] = []
    per_shot_scores: dict[str, Any] = {}

    for project, scene, shot, shot_dir in _collect_shots(run_root):
        frames = sorted((shot_dir / "frames").glob("frame_*.png"))
        metadata_path = shot_dir / "metadata.json"
        metadata = load_json(metadata_path) if metadata_path.exists() else {}

        ctx = ShotEvalContext(
            run_id=run_id,
            project=project,
            scene=scene,
            shot=shot,
            shot_dir=shot_dir,
            frames=frames,
            clip_path=shot_dir / "clip.mp4",
            prompt=str(metadata.get("compiled_prompt", "")),
            negative_prompt=str(metadata.get("compiled_negative_prompt", "")),
            metadata=metadata,
        )

        scores: dict[str, float] = {}
        for judge in judges:
            try:
                scores.update(judge.evaluate(ctx))
            except Exception as exc:
                logger.warning("Judge %s failed on %s/%s/%s: %s", judge.name, project, scene, shot, exc)

        aggregate = float(sum(scores.values()) / max(1, len(scores)))
        row = {
            "run_id": run_id,
            "project": project,
            "scene": scene,
            "shot": shot,
            "aggregate": aggregate,
            **scores,
        }
        shot_rows.append(row)
        key = f"{project}/{scene}/{shot}"
        per_shot_scores[key] = row

    leaderboard_path = eval_root / "leaderboard.csv"
    if shot_rows:
        fields = sorted({k for row in shot_rows for k in row.keys()})
        with leaderboard_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(shot_rows)
    else:
        leaderboard_path.write_text("run_id,project,scene,shot,aggregate\n", encoding="utf-8")

    save_json(eval_root / "scores.json", per_shot_scores)

    # Per-project and per-scene summaries.
    project_summary: dict[str, list[float]] = {}
    scene_summary: dict[str, list[float]] = {}
    for row in shot_rows:
        project_summary.setdefault(row["project"], []).append(float(row["aggregate"]))
        scene_summary.setdefault(f"{row['project']}/{row['scene']}", []).append(float(row["aggregate"]))

    save_json(
        eval_root / "project_scores.json",
        {k: sum(v) / len(v) for k, v in project_summary.items()},
    )
    save_json(
        eval_root / "scene_scores.json",
        {k: sum(v) / len(v) for k, v in scene_summary.items()},
    )

    logger.info("Evaluation complete: %s", eval_root)
    return eval_root
