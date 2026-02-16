from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .models.lora import LoRAMath
from .tools.dataset_report import build_dataset_report
from .utils import ensure_dir, get_git_hash, get_logger, load_yaml, save_json, setup_logging

logger = get_logger("train_identity")


def _check_heavy_deps() -> tuple[bool, str]:
    try:
        import accelerate  # noqa: F401
        import diffusers  # noqa: F401
        import torch  # noqa: F401

        return True, ""
    except Exception as exc:
        return False, str(exc)


def _sample_image(output_dir: Path, step: int, token: str = "<me>") -> None:
    img = Image.new("RGB", (768, 768), color=(20 + (step * 3) % 120, 40, 70))
    draw = ImageDraw.Draw(img)
    draw.text((30, 30), f"Training sample step={step}", fill=(255, 255, 255))
    draw.text((30, 70), f"identity token {token}", fill=(220, 220, 220))
    out = output_dir / f"sample_{step:06d}.png"
    img.save(out)


def _mock_train(config: dict[str, Any], out_dir: Path, resume_from: Path | None) -> Path:
    train_cfg = config.get("train", {})
    lora_cfg = config.get("lora", {})

    max_steps = int(train_cfg.get("max_train_steps", 100))
    save_every = int(train_cfg.get("save_every_steps", 50))
    sample_every = int(train_cfg.get("sample_every_steps", 50))

    state_path = out_dir / "train_state.json"
    start_step = 0

    if resume_from and (resume_from / "train_state.json").exists():
        resume_state = json.loads((resume_from / "train_state.json").read_text(encoding="utf-8"))
        start_step = int(resume_state.get("step", 0))
        logger.info("Resuming mock training from step %s", start_step)

    samples_dir = ensure_dir(out_dir / "samples")
    checkpoints_dir = ensure_dir(out_dir / "checkpoints")

    random.seed(int(config.get("seed", 42)))

    for step in range(start_step + 1, max_steps + 1):
        loss = 1.0 / (1 + 0.03 * step) + random.uniform(-0.02, 0.02)
        if step % sample_every == 0:
            _sample_image(samples_dir, step)
        if step % save_every == 0:
            ckpt = checkpoints_dir / f"step_{step:06d}.json"
            ckpt.write_text(
                json.dumps({"step": step, "mock_loss": loss}, indent=2),
                encoding="utf-8",
            )
        state_path.write_text(json.dumps({"step": step, "loss": loss}, indent=2), encoding="utf-8")

    lora_math = LoRAMath(rank=int(lora_cfg.get("rank", 16)), alpha=float(lora_cfg.get("alpha", 32)))
    final_path = out_dir / "final_lora.safetensors"
    final_payload = {
        "format": "mock_safetensors",
        "note": "fallback artifact generated because full diffusers training is optional",
        "lora_math": lora_math.description(),
        "rank": lora_math.rank,
        "alpha": lora_math.alpha,
        "dropout": float(lora_cfg.get("dropout", 0.0)),
        "git_hash": get_git_hash(),
    }
    final_path.write_text(json.dumps(final_payload, indent=2), encoding="utf-8")
    return final_path


def _real_train_stub(config: dict[str, Any], out_dir: Path, resume_from: Path | None) -> Path:
    # This path is intentionally conservative: it validates environment and then delegates
    # to a reproducible mock loop unless user extends with a full diffusers trainer.
    logger.info(
        "Heavy dependencies detected. Baseline trainer remains mock by default for offline reproducibility. "
        "Replace _real_train_stub with a full diffusers+accelerate SDXL LoRA loop when model weights are available locally."
    )
    return _mock_train(config=config, out_dir=out_dir, resume_from=resume_from)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train identity LoRA for SDXL")
    p.add_argument("--config", required=True)
    p.add_argument("--log_level", default="INFO")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    cfg = load_yaml(args.config)
    out_dir = ensure_dir(cfg.get("output_dir", "outputs/train/default"))
    resume_from = Path(cfg["resume_from"]).resolve() if cfg.get("resume_from") else None

    report = build_dataset_report(Path(cfg["train"]["dataset_root"]))
    save_json(out_dir / "dataset_report.json", report)

    heavy_ok, heavy_error = _check_heavy_deps()
    if not heavy_ok:
        logger.warning("Heavy training dependencies unavailable (%s). Falling back to mock LoRA training.", heavy_error)
        logger.warning("Install torch/diffusers/accelerate for full SDXL LoRA fine-tuning.")
        final = _mock_train(cfg, out_dir, resume_from)
    else:
        final = _real_train_stub(cfg, out_dir, resume_from)

    save_json(
        out_dir / "train_summary.json",
        {
            "run_name": cfg.get("run_name", "unnamed"),
            "output_dir": str(out_dir),
            "final_lora": str(final),
            "git_hash": get_git_hash(),
        },
    )
    logger.info("Training complete. Final LoRA artifact: %s", final)


if __name__ == "__main__":
    main()
