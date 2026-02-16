from __future__ import annotations

import argparse
from pathlib import Path

from ..utils import ensure_dir, get_logger, list_files, setup_logging

logger = get_logger("tools.auto_caption")


def infer_caption_from_filename(stem: str, token: str) -> str:
    base = stem.replace("_", " ").replace("-", " ").strip()
    if not base:
        base = "portrait"
    return f"{token} {base}, high quality portrait"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Baseline auto-captioning from filenames")
    p.add_argument("--images", required=True, help="Directory of images")
    p.add_argument("--captions", required=True, help="Output captions directory")
    p.add_argument("--token", default="<me>")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--log_level", default="INFO")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    img_dir = Path(args.images).resolve()
    cap_dir = ensure_dir(Path(args.captions).resolve())

    images = list_files(img_dir, patterns=("*.jpg", "*.jpeg", "*.png", "*.webp"))
    for image in images:
        caption_path = cap_dir / f"{image.stem}.txt"
        if caption_path.exists() and not args.overwrite:
            continue
        caption = infer_caption_from_filename(image.stem, args.token)
        caption_path.write_text(caption + "\n", encoding="utf-8")

    logger.info("Wrote %s captions to %s", len(images), cap_dir)


if __name__ == "__main__":
    main()
