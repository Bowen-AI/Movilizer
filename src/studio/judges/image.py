from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from .base import ShotEvalContext


def _load_image(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0


def _safe_mean(values: list[float], default: float = 0.0) -> float:
    return float(np.mean(values)) if values else default


class IdentitySimilarityJudge:
    name = "identity_similarity"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        if len(ctx.frames) < 2:
            return {self.name: 0.7}

        sims: list[float] = []
        prev = _load_image(ctx.frames[0])
        for f in ctx.frames[1: min(len(ctx.frames), 12)]:
            cur = _load_image(f)
            sim = 1.0 - float(np.mean(np.abs(cur - prev)))
            sims.append(max(0.0, min(1.0, sim)))
            prev = cur
        return {self.name: _safe_mean(sims, 0.7)}


class PromptAdherenceJudge:
    name = "prompt_adherence"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        prompt = ctx.prompt.lower()
        tokens = [t for t in prompt.replace(",", " ").split() if len(t) > 3]
        # Heuristic proxy: more specific prompt vocabulary tends to score higher.
        richness = min(1.0, len(set(tokens)) / 25.0)
        return {self.name: float(0.4 + 0.6 * richness)}


class QualityJudge:
    name = "quality"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        scores: list[float] = []
        for f in ctx.frames[: min(len(ctx.frames), 16)]:
            img = _load_image(f)
            gray = np.mean(img, axis=2)
            sharpness = float(np.var(np.gradient(gray)[0]) + np.var(np.gradient(gray)[1]))
            score = min(1.0, sharpness * 10.0)
            scores.append(score)
        return {self.name: _safe_mean(scores, 0.5)}


class DiversityJudge:
    name = "diversity"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        if len(ctx.frames) < 2:
            return {self.name: 0.1}

        diffs: list[float] = []
        sampled = ctx.frames[:: max(1, len(ctx.frames) // 8)]
        arrs = [_load_image(p) for p in sampled]
        for i in range(1, len(arrs)):
            diffs.append(float(np.mean(np.abs(arrs[i] - arrs[i - 1]))))
        score = min(1.0, _safe_mean(diffs, 0.0) * 4.0)
        return {self.name: score}


class SafetyJudge:
    name = "safety"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        prompt = f"{ctx.prompt} {ctx.negative_prompt}".lower()
        banned = ["nsfw", "nudity", "gore"]
        bad_hits = sum(1 for word in banned if word in prompt)
        return {self.name: 1.0 if bad_hits == 0 else max(0.0, 1.0 - bad_hits * 0.5)}
