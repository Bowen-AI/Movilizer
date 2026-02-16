from __future__ import annotations

from pathlib import Path
from typing import Any

from ..utils import ensure_dir, get_logger
from .registry import pull_model

logger = get_logger("models.resolve")


def _resolve_ref(base_dir: Path, maybe_relative: str) -> str:
    p = Path(maybe_relative)
    if p.is_absolute():
        return str(p)
    if (base_dir / p).exists():
        return str((base_dir / p).resolve())
    return maybe_relative


def _get_model_entries(model_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    base_source = model_cfg.get("base_source")
    if base_source:
        entries.append({"name": "base", "source": base_source, "revision": model_cfg.get("base_revision")})

    refiner_source = model_cfg.get("refiner_source")
    if refiner_source:
        entries.append({"name": "refiner", "source": refiner_source, "revision": model_cfg.get("refiner_revision")})

    extra = model_cfg.get("model_sources", [])
    if isinstance(extra, list):
        for item in extra:
            if isinstance(item, dict) and item.get("source"):
                entries.append(item)

    return entries


def ensure_project_models(
    workspace: dict[str, Any],
    project_data: dict[str, Any],
    workspace_dir: str | Path,
    force_pull: bool = False,
) -> list[dict[str, Any]]:
    model_cfg = project_data.get("model", {})
    if not isinstance(model_cfg, dict):
        return []

    registry_cfg = workspace.get("model_registry", {})
    cache_root = ensure_dir(Path(workspace_dir) / str(registry_cfg.get("cache_root", "models/cache")))
    auto_pull = bool(registry_cfg.get("auto_pull", False) or force_pull)

    entries = _get_model_entries(model_cfg)
    if not entries:
        return []

    reports: list[dict[str, Any]] = []
    ws_dir = Path(workspace_dir)

    for entry in entries:
        source = _resolve_ref(ws_dir, str(entry.get("source")))
        revision = entry.get("revision")
        local_files_only = bool(entry.get("local_files_only", False))
        name = str(entry.get("name", "model"))

        if auto_pull:
            result = pull_model(
                source=source,
                cache_root=cache_root,
                revision=str(revision) if revision else None,
                local_files_only=local_files_only,
            )
            reports.append(result.__dict__)
            if result.pulled:
                if name == "base":
                    model_cfg["base_id"] = result.resolved_path
                elif name == "refiner":
                    model_cfg["refiner_id"] = result.resolved_path
                else:
                    model_cfg.setdefault("resolved_models", {})[name] = result.resolved_path
            continue

        # no auto-pull: resolve local paths only
        resolved = source
        reports.append(
            {
                "source": source,
                "resolved_path": resolved,
                "backend": "none",
                "pulled": False,
                "message": "auto_pull disabled",
            }
        )
        if name == "base":
            model_cfg["base_id"] = resolved
        elif name == "refiner":
            model_cfg["refiner_id"] = resolved
        else:
            model_cfg.setdefault("resolved_models", {})[name] = resolved

    project_data["model"] = model_cfg
    logger.info("Model resolution reports: %s", reports)
    return reports
