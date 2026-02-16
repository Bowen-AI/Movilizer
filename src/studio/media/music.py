from __future__ import annotations

import math
import wave
from pathlib import Path
from typing import Any

import numpy as np

from ..utils import ensure_dir, get_logger, load_yaml

logger = get_logger("media.music")


def _write_wav(path: Path, audio: np.ndarray, sr: int) -> None:
    ensure_dir(path.parent)
    audio = np.clip(audio, -1.0, 1.0)
    int16 = (audio * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(int16.tobytes())


def _synth_music(duration_sec: float, sr: int, tags: list[str]) -> np.ndarray:
    n = max(1, int(duration_sec * sr))
    t = np.linspace(0.0, duration_sec, num=n, endpoint=False)
    base_freq = 90.0 if any("neon" in tag for tag in tags) else 120.0

    pad = 0.22 * np.sin(2 * math.pi * base_freq * t)
    pad += 0.15 * np.sin(2 * math.pi * (base_freq * 1.5) * t)

    beat_freq = 2.0 if any("rain" in tag for tag in tags) else 1.5
    beat = (np.sin(2 * math.pi * beat_freq * t) > 0.75).astype(np.float32)
    beat_env = 0.5 + 0.5 * np.sin(2 * math.pi * 0.2 * t)

    return 0.35 * pad + 0.12 * beat * beat_env


def choose_music_track(music_catalog_path: Path, scene_prompt: str) -> tuple[str | None, list[str]]:
    if not music_catalog_path.exists():
        return None, []

    catalog = load_yaml(music_catalog_path)
    tracks = catalog.get("tracks", [])
    prompt_tokens = set(scene_prompt.lower().replace(",", " ").split())

    best_path = None
    best_tags: list[str] = []
    best_score = -1

    for track in tracks:
        tags = [str(t).lower() for t in track.get("tags", [])]
        score = sum(1 for tag in tags if tag in prompt_tokens)
        if score > best_score:
            best_score = score
            best_path = str(track.get("path"))
            best_tags = tags
    return best_path, best_tags


def render_music_track(
    project_root: Path,
    scene_prompt: str,
    duration_sec: float,
    output_path: Path,
    sample_rate: int = 24000,
) -> Path:
    ensure_dir(output_path.parent)
    catalog_path = project_root / "assets" / "audio" / "music_library" / "catalog.yaml"
    selected, tags = choose_music_track(catalog_path, scene_prompt)

    # Baseline path: synthesize locally even when catalog references external files.
    if selected:
        logger.info("Selected music track reference: %s (tags=%s)", selected, tags)
    else:
        logger.info("No catalog track matched; synthesizing baseline music.")

    audio = _synth_music(duration_sec=duration_sec, sr=sample_rate, tags=tags)
    _write_wav(output_path, audio, sample_rate)
    return output_path
