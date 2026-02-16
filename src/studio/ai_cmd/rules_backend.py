from __future__ import annotations

import re
from typing import Any

from .schemas import Action, ActionPlan

SCENE_RE = re.compile(r"\b(scene[_-]?\d+)\b", re.IGNORECASE)
SHOT_RE = re.compile(r"\b(shot[_-]?\d+)\b", re.IGNORECASE)
FRAME_RE = re.compile(r"frames?\s+(\d+)\s*(?:-|to)\s*(\d+)", re.IGNORECASE)
CFG_RE = re.compile(r"(?:cfg|guidance(?:_scale)?)\s*(?:to|=)?\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)
STEPS_RE = re.compile(r"(?:steps?)\s*(?:to|=)?\s*(\d+)", re.IGNORECASE)
HAIR_RE = re.compile(r"change hair to\s+([^,;]+)", re.IGNORECASE)
VIBE_RE = re.compile(r"add\s+([^,;]+?)\s+vibe", re.IGNORECASE)


def _normalize_id(text: str) -> str:
    return text.lower().replace("-", "_")


def plan_from_rules(request: str, context: dict[str, Any], dry_run: bool = False) -> ActionPlan:
    text = request.strip()
    low = text.lower()

    project = context.get("project")
    scene = context.get("scene")
    shot = context.get("shot")

    m_scene = SCENE_RE.search(text)
    m_shot = SHOT_RE.search(text)
    if m_scene:
        scene = _normalize_id(m_scene.group(1))
    if m_shot:
        shot = _normalize_id(m_shot.group(1))

    patch_ops: list[dict[str, Any]] = []
    frame_range: list[int] | None = None

    frame_match = FRAME_RE.search(low)
    if frame_match:
        frame_range = [int(frame_match.group(1)), int(frame_match.group(2))]
        patch_ops.append({"op": "set_frame_range", "value": frame_range})

    cfg_match = CFG_RE.search(low)
    if cfg_match:
        patch_ops.append(
            {
                "op": "set",
                "path": "generation.guidance_scale",
                "value": float(cfg_match.group(1)),
            }
        )

    steps_match = STEPS_RE.search(low)
    if steps_match:
        patch_ops.append(
            {
                "op": "set",
                "path": "generation.num_inference_steps",
                "value": int(steps_match.group(1)),
            }
        )

    if "more cinematic" in low:
        patch_ops.append({"op": "add_prompt_suffix", "text": ", cinematic lighting, dramatic composition"})

    if "reduce makeup" in low:
        patch_ops.append({"op": "add_negative_suffix", "text": ", heavy makeup, overdone cosmetics"})
        patch_ops.append({"op": "replace_prompt", "find": "makeup", "replace": "minimal makeup"})

    if "keep identity strong" in low or "identity strong" in low:
        patch_ops.append({"op": "add_prompt_suffix", "text": ", identity-preserving facial structure, true likeness"})

    hair_match = HAIR_RE.search(text)
    if hair_match:
        hair_desc = hair_match.group(1).strip()
        patch_ops.append({"op": "add_prompt_suffix", "text": f", hairstyle: {hair_desc}"})

    vibe_match = VIBE_RE.search(text)
    if vibe_match:
        vibe_text = vibe_match.group(1).strip()
        patch_ops.append({"op": "add_prompt_suffix", "text": f", {vibe_text} vibe"})

    actions: list[Action] = []

    if "compile only" in low:
        actions.append(Action(type="compile_only", payload={"project": project, "scene": scene, "shot": shot}))

    if patch_ops:
        actions.append(
            Action(
                type="apply_patch",
                payload={
                    "target": {"project": project, "scene": scene, "shot": shot},
                    "ops": patch_ops,
                },
            )
        )

    if any(word in low for word in ["regenerate", "rerun", "render"]) or patch_ops:
        actions.append(
            Action(
                type="rerun_subset",
                payload={
                    "project": project,
                    "scene": scene,
                    "shot": shot,
                    "frame_range": frame_range,
                },
            )
        )

    if any(word in low for word in ["evolve", "optimize", "search best"]):
        min_identity = 0.7
        id_match = re.search(r"identity\s*(?:>=|>|at least)?\s*([0-9]+(?:\.[0-9]+)?)", low)
        if id_match:
            min_identity = float(id_match.group(1))
        actions.append(
            Action(
                type="schedule_evolve",
                payload={
                    "project": project,
                    "budget": "small",
                    "constraints": {"min_identity_similarity": min_identity},
                },
            )
        )

    if not actions:
        actions.append(Action(type="compile_only", payload={"project": project, "scene": scene, "shot": shot}))

    return ActionPlan(
        request=request,
        backend="rules",
        context={"project": project, "scene": scene, "shot": shot},
        dry_run=dry_run,
        actions=actions,
    )
