"""Generate a tiny synthetic MP4 sample clip for prototype validation."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate a synthetic sample video")
    p.add_argument("--output", default="outputs/sample_prototype.mp4", help="Output MP4 path")
    p.add_argument("--fps", type=int, default=24, help="Frames per second")
    p.add_argument("--seconds", type=float, default=2.0, help="Duration in seconds")
    p.add_argument("--width", type=int, default=640, help="Frame width")
    p.add_argument("--height", type=int, default=360, help="Frame height")
    return p


def generate_sample_video(output: Path, fps: int, seconds: float, width: int, height: int) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    frame_count = max(1, int(fps * seconds))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output), fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError("Could not open VideoWriter for MP4 output")

    for idx in range(frame_count):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        blue = int(255 * idx / frame_count)
        green = int(255 * (1 - idx / frame_count))
        frame[:, :] = (blue, green, 80)

        x = 30 + int((width - 120) * (idx / max(1, frame_count - 1)))
        cv2.rectangle(frame, (x, height // 3), (x + 90, (height // 3) + 90), (240, 240, 240), -1)
        cv2.putText(frame, "Movilizer Prototype", (20, height - 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (25, 25, 25), 2)

        writer.write(frame)

    writer.release()
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError("Sample video generation failed")
    return output


def main() -> None:
    args = build_parser().parse_args()
    path = generate_sample_video(
        output=Path(args.output),
        fps=args.fps,
        seconds=args.seconds,
        width=args.width,
        height=args.height,
    )
    print(path)


if __name__ == "__main__":
    main()
