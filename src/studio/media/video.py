from __future__ import annotations

import subprocess
from pathlib import Path

from ..utils import ensure_dir, get_logger, which

logger = get_logger("media.video")


def has_ffmpeg() -> bool:
    return which("ffmpeg") is not None


def _run_ffmpeg(args: list[str]) -> bool:
    cmd = ["ffmpeg", "-y", *args]
    logger.info("Running ffmpeg: %s", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except Exception as exc:
        logger.warning("ffmpeg command failed: %s", exc)
        return False


def frames_to_clip(frames_dir: Path, fps: int, output_path: Path) -> bool:
    ensure_dir(output_path.parent)
    if not has_ffmpeg():
        logger.warning("ffmpeg not found; cannot create clip %s", output_path)
        output_path.with_suffix(".txt").write_text(
            "ffmpeg missing; install ffmpeg to render MP4 clips.\n",
            encoding="utf-8",
        )
        return False

    pattern = str(frames_dir / "frame_%06d.png")
    return _run_ffmpeg(
        [
            "-framerate",
            str(fps),
            "-i",
            pattern,
            "-pix_fmt",
            "yuv420p",
            "-vcodec",
            "libx264",
            str(output_path),
        ]
    )


def concat_clips(clips: list[Path], output_path: Path) -> bool:
    ensure_dir(output_path.parent)
    if not clips:
        logger.warning("No clips provided for concat into %s", output_path)
        return False

    if not has_ffmpeg():
        output_path.with_suffix(".txt").write_text(
            "ffmpeg missing; install ffmpeg to concatenate videos.\n",
            encoding="utf-8",
        )
        return False

    concat_file = output_path.parent / f"{output_path.stem}_concat.txt"
    lines = [f"file '{p.resolve()}'" for p in clips if p.exists()]
    concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok = _run_ffmpeg(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(output_path),
        ]
    )
    return ok


def mux_audio(video_path: Path, audio_path: Path, output_path: Path) -> bool:
    ensure_dir(output_path.parent)
    if not has_ffmpeg():
        output_path.with_suffix(".txt").write_text(
            "ffmpeg missing; install ffmpeg to mux audio and video.\n",
            encoding="utf-8",
        )
        return False
    if not video_path.exists() or not audio_path.exists():
        logger.warning("Missing input for mux: %s %s", video_path, audio_path)
        return False

    return _run_ffmpeg(
        [
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
    )
