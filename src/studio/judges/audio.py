from __future__ import annotations

from pathlib import Path

from .base import ShotEvalContext


class LoudnessJudge:
    name = "loudness"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        stats = ctx.metadata.get("audio_stats", {})
        lufs = float(stats.get("lufs", -30.0))
        target = float(ctx.metadata.get("loudness_target_lufs", -16.0))
        delta = abs(lufs - target)
        score = max(0.0, 1.0 - delta / 20.0)
        return {self.name: score}


class ClippingJudge:
    name = "clipping"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        clip_ratio = float(ctx.metadata.get("audio_stats", {}).get("clipping_ratio", 0.0))
        return {self.name: max(0.0, 1.0 - clip_ratio * 50.0)}
