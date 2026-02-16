from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from ..utils import ensure_dir, get_logger

logger = get_logger("models.diffusion")


@dataclass
class DiffusionConfig:
    base_id: str
    refiner_id: str | None = None
    use_refiner: bool = False
    precision: str = "bf16"
    enable_xformers: bool = True
    attention_slicing: bool = True


class VideoPlugin:
    name = "base"

    def render(self, shot: dict[str, Any], frame_indices: list[int], output_frames_dir: Path) -> list[Path]:
        raise NotImplementedError


class NativeVideoStubPlugin(VideoPlugin):
    name = "native_video_stub"

    def render(self, shot: dict[str, Any], frame_indices: list[int], output_frames_dir: Path) -> list[Path]:
        logger.info("Using native video stub plugin for shot %s", shot.get("shot_id"))
        width, height = shot.get("resolution", [1024, 1024])
        produced: list[Path] = []
        for idx in frame_indices:
            img = Image.new("RGB", (int(width), int(height)), color=(15, 20, 30))
            draw = ImageDraw.Draw(img)
            draw.text((30, 30), f"VideoStub {shot.get('shot_id')} frame={idx}", fill=(180, 220, 255))
            draw.text((30, 70), shot.get("prompt", ""), fill=(220, 220, 220))
            out = output_frames_dir / f"frame_{idx:06d}.png"
            img.save(out)
            produced.append(out)
        return produced


class DiffusionGenerator:
    def __init__(self, config: DiffusionConfig) -> None:
        self.config = config
        self._diffusers_pipeline = None
        self._diffusers_ready = False
        self._attempted = False

    def _try_load_diffusers(self) -> None:
        if self._attempted:
            return
        self._attempted = True
        try:
            import torch  # noqa: F401
            from diffusers import DiffusionPipeline

            self._diffusers_pipeline = DiffusionPipeline.from_pretrained(
                self.config.base_id,
                torch_dtype=None,
                local_files_only=True,
            )
            self._diffusers_ready = True
            logger.info("Loaded local diffusers pipeline for %s", self.config.base_id)
        except Exception as exc:
            logger.warning(
                "Diffusers pipeline unavailable (%s). Falling back to synthetic renderer.",
                exc,
            )
            self._diffusers_ready = False

    def _synthetic_frame(
        self,
        prompt: str,
        negative_prompt: str,
        seed: int,
        width: int,
        height: int,
        frame_idx: int,
        output_path: Path,
    ) -> None:
        random.seed(seed + frame_idx)
        np.random.seed((seed + frame_idx) % (2**32 - 1))

        base = np.zeros((height, width, 3), dtype=np.uint8)
        hue = abs(hash(prompt)) % 255
        base[:, :, 0] = (hue + frame_idx * 3) % 255
        base[:, :, 1] = (100 + frame_idx * 2) % 255
        base[:, :, 2] = (180 + frame_idx) % 255

        noise = np.random.randint(0, 35, size=(height, width, 3), dtype=np.uint8)
        arr = np.clip(base + noise, 0, 255)

        img = Image.fromarray(arr, mode="RGB")
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, width, 130), fill=(0, 0, 0, 170))
        draw.text((16, 10), f"prompt: {prompt[:110]}", fill=(255, 255, 255))
        draw.text((16, 40), f"negative: {negative_prompt[:110]}", fill=(230, 230, 230))
        draw.text((16, 70), f"seed={seed} frame={frame_idx}", fill=(255, 220, 180))

        # simple vignette
        px = img.load()
        cx, cy = width / 2.0, height / 2.0
        maxd = math.sqrt(cx * cx + cy * cy)
        for y in range(0, height, 4):
            for x in range(0, width, 4):
                d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / maxd
                factor = max(0.5, 1.0 - 0.45 * d)
                r, g, b = px[x, y]
                px[x, y] = (int(r * factor), int(g * factor), int(b * factor))

        img.save(output_path)

    def generate_frame(
        self,
        prompt: str,
        negative_prompt: str,
        seed: int,
        width: int,
        height: int,
        output_path: Path,
        frame_idx: int = 0,
        generation_kwargs: dict[str, Any] | None = None,
    ) -> Path:
        ensure_dir(output_path.parent)
        self._try_load_diffusers()
        if self._diffusers_ready:
            # Deterministic fallback still used intentionally to avoid hidden downloads.
            logger.info(
                "Diffusers is available but synthetic path is used by default for reproducibility/offline safety. "
                "Set STUDIO_ALLOW_MODEL_EXEC=1 and extend this method for real sampling."
            )
        self._synthetic_frame(
            prompt=prompt,
            negative_prompt=negative_prompt,
            seed=seed,
            width=width,
            height=height,
            frame_idx=frame_idx,
            output_path=output_path,
        )
        return output_path

    def generate_frames_for_shot(
        self,
        shot: dict[str, Any],
        prompt: str,
        negative_prompt: str,
        frame_indices: list[int],
        output_frames_dir: Path,
        generation_kwargs: dict[str, Any] | None = None,
    ) -> list[Path]:
        ensure_dir(output_frames_dir)
        width, height = shot.get("resolution", [1024, 1024])
        shot_seed = int(shot.get("generation", {}).get("seed", 0))
        method = shot.get("generation", {}).get("method", "image_only")
        plugin = shot.get("generation", {}).get("plugin", "native_video_stub")

        if method == "video_plugin":
            if plugin == "native_video_stub":
                return NativeVideoStubPlugin().render(shot, frame_indices, output_frames_dir)

        out: list[Path] = []
        for idx in frame_indices:
            p = output_frames_dir / f"frame_{idx:06d}.png"
            self.generate_frame(
                prompt=prompt,
                negative_prompt=negative_prompt,
                seed=shot_seed,
                width=int(width),
                height=int(height),
                output_path=p,
                frame_idx=idx,
                generation_kwargs=generation_kwargs,
            )
            out.append(p)
        return out
