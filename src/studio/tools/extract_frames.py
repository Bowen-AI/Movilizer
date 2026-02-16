from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from ..utils import ensure_dir, get_logger, setup_logging, which

logger = get_logger("tools.extract_frames")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract video frames to images")
    p.add_argument("--input", required=True, help="Input video path")
    p.add_argument("--output", required=True, help="Output frames directory")
    p.add_argument("--fps", type=float, default=None, help="Optional output FPS")
    p.add_argument("--log_level", default="INFO")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is required for extract_frames.py")

    in_path = Path(args.input).resolve()
    out_dir = ensure_dir(Path(args.output).resolve())

    vf = []
    if args.fps:
        vf = ["-vf", f"fps={args.fps}"]

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(in_path),
        *vf,
        str(out_dir / "frame_%06d.png"),
    ]
    logger.info("Running: %s", " ".join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
