from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from ..utils import ensure_dir, get_logger, list_files, setup_logging

logger = get_logger("tools.face_crop_align")


def center_crop(img: Image.Image, size: int) -> Image.Image:
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    crop = img.crop((left, top, left + side, top + side))
    return crop.resize((size, size), Image.Resampling.LANCZOS)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Optional face crop/align baseline (center-crop fallback)")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--size", type=int, default=1024)
    p.add_argument("--log_level", default="INFO")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    in_dir = Path(args.input).resolve()
    out_dir = ensure_dir(Path(args.output).resolve())

    images = list_files(in_dir, patterns=("*.jpg", "*.jpeg", "*.png"))
    for image in images:
        img = Image.open(image).convert("RGB")
        cropped = center_crop(img, args.size)
        cropped.save(out_dir / image.name)

    logger.info("Wrote %s aligned images to %s", len(images), out_dir)


if __name__ == "__main__":
    main()
