from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .utils import get_logger, load_yaml

logger = get_logger("config")


@dataclass
class WorkspaceProjectRef:
    name: str
    path: str


@dataclass
class LoadedProject:
    name: str
    path: Path
    data: dict[str, Any]


def _resolve(base: Path, maybe_relative: str) -> Path:
    p = Path(maybe_relative)
    return p if p.is_absolute() else (base / p).resolve()


def load_workspace(workspace_path: str) -> dict[str, Any]:
    ws_path = Path(workspace_path).resolve()
    ws = load_yaml(ws_path)
    ws["_workspace_path"] = str(ws_path)
    ws["_workspace_dir"] = str(ws_path.parent)
    return ws


def validate_with_schema(config_data: dict[str, Any], schema_path: str | Path) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except Exception:
        return ["jsonschema not installed; schema validation skipped"]

    schema = load_yaml(schema_path)
    validator = Draft202012Validator(schema)
    errors = [e.message for e in sorted(validator.iter_errors(config_data), key=str)]
    return errors


def resolve_projects(workspace: dict[str, Any], selected: list[str] | None = None) -> list[LoadedProject]:
    ws_dir = Path(workspace["_workspace_dir"])
    refs: list[dict[str, Any]] = workspace.get("projects", [])
    all_projects: dict[str, Path] = {
        r["name"]: _resolve(ws_dir, r["path"]) for r in refs if "name" in r and "path" in r
    }

    if not selected or selected == ["all"]:
        chosen_names = list(all_projects.keys())
    else:
        chosen_names = selected

    loaded: list[LoadedProject] = []
    for name in chosen_names:
        if name not in all_projects:
            logger.warning("Project %s not found in workspace", name)
            continue
        proj_path = all_projects[name]
        proj_data = load_yaml(proj_path)
        loaded.append(LoadedProject(name=name, path=proj_path, data=proj_data))
    return loaded


def resolve_scene_files(project: LoadedProject, selected_scenes: list[str] | None = None) -> list[Path]:
    project_data = project.data
    scene_files = project_data.get("scene_files")
    proj_root = project.path.parent

    if scene_files:
        candidates = [
            (Path(p) if Path(p).is_absolute() else (proj_root.parents[1] / p).resolve()) for p in scene_files
        ]
    else:
        scenes_dir = proj_root / "scripts" / "scenes"
        candidates = [p for p in scenes_dir.glob("*.yaml") if "patch" not in p.name]

    if not selected_scenes or selected_scenes == ["all"]:
        return sorted(candidates)

    selected_set = set(selected_scenes)
    out: list[Path] = []
    for p in candidates:
        stem = p.stem
        if stem in selected_set:
            out.append(p)
    return sorted(out)


def merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge_dict(out[k], v)
        else:
            out[k] = v
    return out
