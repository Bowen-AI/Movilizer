from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ..utils import get_logger, list_files, save_json, setup_logging

logger = get_logger("tools.dataset_report")


def build_dataset_report(dataset_root: Path) -> dict[str, Any]:
    train_images_dir = dataset_root / "train" / "images"
    train_caps_dir = dataset_root / "train" / "captions"
    reg_dir = dataset_root / "reg"

    images = list_files(train_images_dir, patterns=("*.jpg", "*.jpeg", "*.png", "*.webp"))
    captions = list_files(train_caps_dir, patterns=("*.txt",))

    cap_stems = {p.stem for p in captions}
    img_stems = {p.stem for p in images}

    missing_caption = sorted(img_stems - cap_stems)
    orphan_caption = sorted(cap_stems - img_stems)

    reg_images = list_files(reg_dir, patterns=("*.jpg", "*.jpeg", "*.png", "*.webp")) if reg_dir.exists() else []

    return {
        "dataset_root": str(dataset_root),
        "train_images": len(images),
        "train_captions": len(captions),
        "reg_images": len(reg_images),
        "missing_caption_count": len(missing_caption),
        "orphan_caption_count": len(orphan_caption),
        "missing_caption_stems": missing_caption,
        "orphan_caption_stems": orphan_caption,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dataset report for identity LoRA data")
    p.add_argument("--dataset_root", required=True)
    p.add_argument("--output", default=None)
    p.add_argument("--log_level", default="INFO")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    report = build_dataset_report(Path(args.dataset_root).resolve())
    if args.output:
        save_json(Path(args.output).resolve(), report)
        logger.info("Report written to %s", args.output)
    else:
        import json

        print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
