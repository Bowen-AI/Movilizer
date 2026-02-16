from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from .base import ShotEvalContext


def _load(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0


class TemporalIdentityConsistencyJudge:
    name = "temporal_identity_consistency"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        if len(ctx.frames) < 2:
            return {self.name: 0.8}
        vals: list[float] = []
        prev = _load(ctx.frames[0])
        for frame in ctx.frames[1: min(len(ctx.frames), 20)]:
            cur = _load(frame)
            vals.append(1.0 - float(np.mean(np.abs(cur - prev))))
            prev = cur
        score = float(np.clip(np.mean(vals), 0.0, 1.0))
        return {self.name: score}


class ClipStabilityJudge:
    name = "clip_stability"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        if len(ctx.frames) < 2:
            return {self.name: 0.8}
        diffs: list[float] = []
        for i in range(1, min(len(ctx.frames), 20)):
            a = _load(ctx.frames[i - 1])
            b = _load(ctx.frames[i])
            diffs.append(float(np.std(b - a)))
        score = float(np.clip(1.0 - np.mean(diffs) * 2.0, 0.0, 1.0))
        return {self.name: score}


class FlickerJudge:
    name = "flicker"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        if len(ctx.frames) < 3:
            return {self.name: 0.1}
        means = []
        for frame in ctx.frames[: min(len(ctx.frames), 30)]:
            arr = _load(frame)
            means.append(float(arr.mean()))
        diffs = np.abs(np.diff(np.asarray(means)))
        score = float(np.clip(np.mean(diffs) * 6.0, 0.0, 1.0))
        return {self.name: score}
