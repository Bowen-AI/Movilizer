from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from .utils import get_logger, save_yaml, setup_logging

logger = get_logger("tweak")


INLINE_REPLACE = re.compile(r"replace_prompt:\s*'([^']+)'\s*->\s*'([^']+)'", re.IGNORECASE)
INLINE_FRAME = re.compile(r"frame_range\s*=\s*(\d+)\s*[-:]\s*(\d+)", re.IGNORECASE)
INLINE_CFG = re.compile(r"cfg\s*=\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)
INLINE_STEPS = re.compile(r"steps\s*=\s*(\d+)", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create/apply non-destructive scene/shot patches")
    p.add_argument("--workspace", default="workspace.yaml")
    p.add_argument("--project", required=True)
    p.add_argument("--scene", required=True)
    p.add_argument("--shot", default=None)
    p.add_argument("--create_patch_template", action="store_true")
    p.add_argument("--apply_inline", default=None)
    p.add_argument("--log_level", default="INFO")
    return p.parse_args()


def _project_root(workspace_path: Path, project_name: str) -> Path:
    import yaml

    ws = yaml.safe_load(workspace_path.read_text(encoding="utf-8")) or {}
    for ref in ws.get("projects", []):
        if str(ref.get("name")) == project_name:
            path = Path(ref["path"])
            if not path.is_absolute():
                path = (workspace_path.parent / path).resolve()
            return path.parent
    raise ValueError(f"project not found in workspace: {project_name}")


def _next_patch_path(project_root: Path, scene_name: str) -> Path:
    patch_dir = project_root / "scripts" / "scenes" / "patches"
    patch_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(patch_dir.glob(f"{scene_name}.patch.*.yaml"))
    n = 1
    if existing:
        token = existing[-1].stem.split(".")[-1]
        if token.isdigit():
            n = int(token) + 1
    return patch_dir / f"{scene_name}.patch.{n:03d}.yaml"


def _template(project: str, scene: str, shot: str | None) -> dict[str, Any]:
    return {
        "target": {"project": project, "scene": scene, "shot": shot},
        "ops": [
            {"op": "replace_prompt", "find": "straight hair", "replace": "wavy hair"},
            {"op": "add_prompt_suffix", "text": ", cinematic look"},
            {"op": "set", "path": "generation.guidance_scale", "value": 6.8},
            {"op": "set_frame_range", "value": [120, 220]},
        ],
    }


def _inline_to_patch(project: str, scene: str, shot: str | None, inline: str) -> dict[str, Any]:
    ops: list[dict[str, Any]] = []

    rep = INLINE_REPLACE.search(inline)
    if rep:
        ops.append({"op": "replace_prompt", "find": rep.group(1), "replace": rep.group(2)})

    fr = INLINE_FRAME.search(inline)
    if fr:
        ops.append({"op": "set_frame_range", "value": [int(fr.group(1)), int(fr.group(2))]})

    cfg = INLINE_CFG.search(inline)
    if cfg:
        ops.append({"op": "set", "path": "generation.guidance_scale", "value": float(cfg.group(1))})

    steps = INLINE_STEPS.search(inline)
    if steps:
        ops.append({"op": "set", "path": "generation.num_inference_steps", "value": int(steps.group(1))})

    if not ops:
        ops.append({"op": "add_prompt_suffix", "text": inline.strip()})

    return {"target": {"project": project, "scene": scene, "shot": shot}, "ops": ops}


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    ws_path = Path(args.workspace).resolve()
    project_root = _project_root(ws_path, args.project)
    patch_path = _next_patch_path(project_root, args.scene)

    if args.create_patch_template:
        payload = _template(args.project, args.scene, args.shot)
        save_yaml(patch_path, payload)
        print(str(patch_path))
        return

    if args.apply_inline:
        payload = _inline_to_patch(args.project, args.scene, args.shot, args.apply_inline)
        save_yaml(patch_path, payload)
        print(str(patch_path))
        return

    raise SystemExit("Use --create_patch_template or --apply_inline")


if __name__ == "__main__":
    main()
