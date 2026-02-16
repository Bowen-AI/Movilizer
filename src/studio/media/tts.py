from __future__ import annotations

import math
import shutil
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..utils import ensure_dir, get_logger

logger = get_logger("media.tts")


@dataclass
class DialogLineAudio:
    line_id: str
    speaker: str
    start_sec: float
    end_sec: float
    text: str
    wav_path: Path


def _write_wav(path: Path, audio: np.ndarray, sr: int) -> None:
    ensure_dir(path.parent)
    clipped = np.clip(audio, -1.0, 1.0)
    int16 = (clipped * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(int16.tobytes())


def _read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
    return audio, sr


def _synth_tone(text: str, sr: int, duration_sec: float, pitch_hz: float = 160.0) -> np.ndarray:
    n = max(1, int(sr * duration_sec))
    t = np.linspace(0.0, duration_sec, num=n, endpoint=False)
    mod = 0.18 * np.sin(2 * math.pi * 4.0 * t)
    carrier = np.sin(2 * math.pi * (pitch_hz + 22 * mod) * t)
    envelope = np.minimum(1.0, t / 0.04) * np.minimum(1.0, (duration_sec - t + 1e-6) / 0.06)
    # encode rough syllabic pulses from text length
    pulse_rate = max(2.0, min(8.0, len(text.split()) * 0.8))
    pulse = 0.55 + 0.45 * np.maximum(0.0, np.sin(2 * math.pi * pulse_rate * t))
    return 0.25 * carrier * envelope * pulse


def synth_line_wav(
    line: dict[str, Any],
    voice_dir: Path,
    output_dir: Path,
    sample_rate: int,
    pitch_hz: float = 160.0,
) -> DialogLineAudio:
    line_id = str(line["line_id"])
    speaker = str(line["speaker"])
    start_sec = float(line.get("start_sec", 0.0))
    end_sec = float(line.get("end_sec", start_sec + 1.0))
    text = str(line.get("text", ""))

    prerecorded = voice_dir / f"{line_id}.wav"
    out_wav = output_dir / f"{line_id}.wav"
    if prerecorded.exists():
        ensure_dir(out_wav.parent)
        shutil.copy2(prerecorded, out_wav)
        logger.info("Using prerecorded line %s from %s", line_id, prerecorded)
    else:
        duration = max(0.5, end_sec - start_sec)
        audio = _synth_tone(text=text, sr=sample_rate, duration_sec=duration, pitch_hz=pitch_hz)
        _write_wav(out_wav, audio, sample_rate)
        logger.info("Synthesized baseline TTS tone for line %s", line_id)

    return DialogLineAudio(
        line_id=line_id,
        speaker=speaker,
        start_sec=start_sec,
        end_sec=end_sec,
        text=text,
        wav_path=out_wav,
    )


def render_dialog_track(
    dialog_yaml: dict[str, Any],
    project_root: Path,
    output_dir: Path,
    total_duration_sec: float,
    default_sample_rate: int = 24000,
) -> Path:
    ensure_dir(output_dir)
    sample_rate = int(dialog_yaml.get("sample_rate", default_sample_rate))
    lines = dialog_yaml.get("lines", [])
    speakers = dialog_yaml.get("speakers", {})

    line_audio_dir = output_dir / "lines"
    line_entries: list[DialogLineAudio] = []

    for line in lines:
        speaker = str(line.get("speaker", "narrator"))
        voice_cfg = speakers.get(speaker, {})
        profile_path = voice_cfg.get("voice_profile")
        pitch = 160.0
        if profile_path:
            abs_profile = (project_root.parents[1] / profile_path).resolve()
            if abs_profile.exists():
                import yaml

                profile = yaml.safe_load(abs_profile.read_text(encoding="utf-8")) or {}
                pitch = float(profile.get("baseline_pitch_hz", 160.0))

        voice_dir = project_root / "assets" / "audio" / "voices" / speaker
        line_audio = synth_line_wav(
            line=line,
            voice_dir=voice_dir,
            output_dir=line_audio_dir,
            sample_rate=sample_rate,
            pitch_hz=pitch,
        )
        line_entries.append(line_audio)

    total_samples = max(1, int(total_duration_sec * sample_rate))
    mix = np.zeros(total_samples, dtype=np.float32)

    for line in line_entries:
        audio, sr = _read_wav(line.wav_path)
        if sr != sample_rate:
            logger.warning("Sample rate mismatch for %s (%s != %s), naive resample", line.line_id, sr, sample_rate)
            x_old = np.linspace(0.0, 1.0, num=len(audio), endpoint=False)
            x_new = np.linspace(0.0, 1.0, num=int(len(audio) * sample_rate / sr), endpoint=False)
            audio = np.interp(x_new, x_old, audio).astype(np.float32)
        start = int(line.start_sec * sample_rate)
        end = min(total_samples, start + len(audio))
        if start < total_samples and end > start:
            mix[start:end] += audio[: end - start]

    dialog_path = output_dir / "dialog_track.wav"
    _write_wav(dialog_path, mix, sample_rate)
    return dialog_path


def write_srt(dialog_yaml: dict[str, Any], output_path: Path) -> Path:
    ensure_dir(output_path.parent)

    def fmt(sec: float) -> str:
        ms = int(sec * 1000)
        hh = ms // 3600000
        ms -= hh * 3600000
        mm = ms // 60000
        ms -= mm * 60000
        ss = ms // 1000
        ms -= ss * 1000
        return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"

    lines_out = []
    for i, line in enumerate(dialog_yaml.get("lines", []), start=1):
        start = float(line.get("start_sec", 0.0))
        end = float(line.get("end_sec", start + 1.0))
        text = str(line.get("text", ""))
        lines_out.append(str(i))
        lines_out.append(f"{fmt(start)} --> {fmt(end)}")
        lines_out.append(text)
        lines_out.append("")

    output_path.write_text("\n".join(lines_out), encoding="utf-8")
    return output_path
