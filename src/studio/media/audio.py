from __future__ import annotations

import math
import subprocess
import wave
from pathlib import Path

import numpy as np

from ..utils import ensure_dir, get_logger, which

logger = get_logger("media.audio")


def _read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
    return audio, sr


def _write_wav(path: Path, audio: np.ndarray, sr: int) -> None:
    ensure_dir(path.parent)
    clipped = np.clip(audio, -1.0, 1.0)
    data = (clipped * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(data.tobytes())


def _to_lufs_approx(audio: np.ndarray) -> float:
    if len(audio) == 0:
        return -120.0
    rms = float(np.sqrt(np.mean(np.square(audio)) + 1e-9))
    return 20.0 * math.log10(rms + 1e-9)


def _normalize_to_lufs(audio: np.ndarray, target_lufs: float) -> np.ndarray:
    cur = _to_lufs_approx(audio)
    gain_db = target_lufs - cur
    gain = 10 ** (gain_db / 20.0)
    return audio * gain


def _ffmpeg_mix(dialog_path: Path, music_path: Path, output_path: Path, target_lufs: float, ducking_db: float) -> bool:
    if which("ffmpeg") is None:
        return False

    ensure_dir(output_path.parent)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(music_path),
        "-i",
        str(dialog_path),
        "-filter_complex",
        (
            f"[0:a][1:a]sidechaincompress=threshold=0.05:ratio=8:level_sc=1:makeup={abs(ducking_db):.1f}[ducked];"
            f"[ducked][1:a]amix=inputs=2:weights='0.8 1.0',loudnorm=I={target_lufs}:TP=-1.5:LRA=11"
        ),
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except Exception as exc:
        logger.warning("ffmpeg mix failed: %s", exc)
        return False


def mix_dialog_and_music(
    dialog_path: Path,
    music_path: Path,
    output_path: Path,
    target_lufs: float = -16.0,
    ducking_db: float = -8.0,
    fade_in_sec: float = 0.3,
    fade_out_sec: float = 0.5,
) -> Path:
    if _ffmpeg_mix(dialog_path, music_path, output_path, target_lufs, ducking_db):
        return output_path

    logger.info("Using numpy fallback for audio mixing")
    dialog, sr_d = _read_wav(dialog_path)
    music, sr_m = _read_wav(music_path)
    if sr_d != sr_m:
        logger.warning("Sample rate mismatch in audio mix (%s vs %s); naive resample music", sr_d, sr_m)
        x_old = np.linspace(0.0, 1.0, num=len(music), endpoint=False)
        x_new = np.linspace(0.0, 1.0, num=int(len(music) * sr_d / sr_m), endpoint=False)
        music = np.interp(x_new, x_old, music).astype(np.float32)
    sr = sr_d

    n = max(len(dialog), len(music))
    dialog_pad = np.zeros(n, dtype=np.float32)
    music_pad = np.zeros(n, dtype=np.float32)
    dialog_pad[: len(dialog)] = dialog
    music_pad[: len(music)] = music

    dialog_env = np.clip(np.abs(dialog_pad) * 4.0, 0.0, 1.0)
    duck = 1.0 - (abs(ducking_db) / 20.0) * dialog_env
    duck = np.clip(duck, 0.2, 1.0)

    mix = dialog_pad + 0.7 * music_pad * duck

    fade_in_samples = int(max(0.0, fade_in_sec) * sr)
    fade_out_samples = int(max(0.0, fade_out_sec) * sr)

    if fade_in_samples > 0:
        mix[:fade_in_samples] *= np.linspace(0.0, 1.0, num=fade_in_samples, endpoint=True)
    if fade_out_samples > 0:
        mix[-fade_out_samples:] *= np.linspace(1.0, 0.0, num=fade_out_samples, endpoint=True)

    mix = _normalize_to_lufs(mix, target_lufs)
    _write_wav(output_path, mix, sr)
    return output_path


def audio_stats(path: Path) -> dict[str, float]:
    audio, _ = _read_wav(path)
    lufs = _to_lufs_approx(audio)
    clipping_ratio = float(np.mean(np.abs(audio) >= 0.999)) if len(audio) else 0.0
    return {"lufs": lufs, "clipping_ratio": clipping_ratio}
