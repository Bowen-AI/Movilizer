from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Template

from ..utils import read_text


def _layer(*parts: str) -> str:
    filtered = [p.strip().strip(".") for p in parts if p and str(p).strip()]
    return ". ".join(filtered)


def compose_prompt(
    global_guidelines: str,
    project_vibe: str,
    scene_vibe: str,
    shot_prompt: str,
    camera: str,
    lens: str,
    lighting: str,
    wardrobe: str,
    location: str,
    template_path: str | None = None,
) -> str:
    if template_path:
        tpath = Path(template_path)
        if tpath.exists():
            template = Template(read_text(tpath))
            return template.render(
                global_guidelines=global_guidelines,
                project_vibe=project_vibe,
                scene_vibe=scene_vibe,
                shot_prompt=shot_prompt,
                camera=camera,
                lens=lens,
                lighting=lighting,
                wardrobe=wardrobe,
                location=location,
            ).strip()
    return _layer(
        global_guidelines,
        project_vibe,
        scene_vibe,
        shot_prompt,
        f"Camera {camera}",
        f"Lens {lens}",
        f"Lighting {lighting}",
        f"Wardrobe {wardrobe}",
        f"Location {location}",
    )


def compose_negative_prompt(global_negative: str, scene_negative: str, shot_negative: str) -> str:
    return _layer(global_negative, scene_negative, shot_negative)


def apply_prompt_mutations(
    prompt: str,
    negative_prompt: str,
    operations: list[dict[str, Any]],
) -> tuple[str, str]:
    p = prompt
    n = negative_prompt
    for op in operations:
        name = op.get("op")
        if name == "replace_prompt":
            p = p.replace(str(op.get("find", "")), str(op.get("replace", "")))
        elif name == "add_prompt_prefix":
            p = f"{op.get('text', '')} {p}".strip()
        elif name == "add_prompt_suffix":
            p = f"{p} {op.get('text', '')}".strip()
        elif name == "add_negative_prefix":
            n = f"{op.get('text', '')} {n}".strip()
        elif name == "add_negative_suffix":
            n = f"{n} {op.get('text', '')}".strip()
    return p, n
