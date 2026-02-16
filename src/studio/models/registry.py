from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..utils import ensure_dir, get_logger, now_utc_iso, save_json

logger = get_logger("models.registry")


@dataclass
class ModelRef:
    source: str
    revision: str | None = None


@dataclass
class ModelPullResult:
    source: str
    resolved_path: str
    backend: str
    pulled: bool
    message: str


@dataclass
class ModelPushResult:
    source_dir: str
    target: str
    backend: str
    pushed: bool
    message: str


def _safe_name(value: str) -> str:
    return value.replace("/", "__").replace(":", "_")


def _is_local_path(ref: str) -> bool:
    p = Path(ref)
    return p.exists() or ref.startswith(".") or ref.startswith("/")


def _copy_local_model(source: Path, cache_root: Path) -> Path:
    ensure_dir(cache_root)
    target = cache_root / _safe_name(source.name)
    if target.exists():
        shutil.rmtree(target)
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        ensure_dir(target)
        shutil.copy2(source, target / source.name)
    return target


def pull_model(
    source: str,
    cache_root: str | Path,
    revision: str | None = None,
    local_files_only: bool = False,
    token_env: str = "HF_TOKEN",
) -> ModelPullResult:
    cache_dir = ensure_dir(cache_root)

    if _is_local_path(source):
        src = Path(source).resolve()
        if not src.exists():
            return ModelPullResult(source=source, resolved_path="", backend="local", pulled=False, message="local source path not found")
        target = _copy_local_model(src, cache_dir)
        return ModelPullResult(source=source, resolved_path=str(target), backend="local", pulled=True, message="copied from local path")

    try:
        from huggingface_hub import snapshot_download

        local_dir = cache_dir / _safe_name(source if revision is None else f"{source}@{revision}")
        ensure_dir(local_dir)
        path = snapshot_download(
            repo_id=source,
            revision=revision,
            local_dir=str(local_dir),
            local_dir_use_symlinks=False,
            local_files_only=local_files_only,
            token=None,
        )
        return ModelPullResult(
            source=source,
            resolved_path=str(path),
            backend="huggingface",
            pulled=True,
            message="snapshot downloaded",
        )
    except Exception as exc:
        msg = (
            f"huggingface pull failed: {exc}. "
            "Install huggingface_hub and set network/token if needed, or use a local model path."
        )
        return ModelPullResult(source=source, resolved_path="", backend="huggingface", pulled=False, message=msg)


def push_model(
    source_dir: str | Path,
    target: str,
    private: bool = False,
    token_env: str = "HF_TOKEN",
) -> ModelPushResult:
    src = Path(source_dir).resolve()
    if not src.exists():
        return ModelPushResult(source_dir=str(src), target=target, backend="local", pushed=False, message="source_dir not found")

    if _is_local_path(target):
        dst = Path(target).resolve()
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        return ModelPushResult(source_dir=str(src), target=str(dst), backend="local", pushed=True, message="copied to local target")

    try:
        import os

        from huggingface_hub import HfApi

        token = os.environ.get(token_env)
        api = HfApi(token=token)
        api.create_repo(repo_id=target, repo_type="model", private=private, exist_ok=True)
        api.upload_folder(folder_path=str(src), repo_id=target, repo_type="model")
        return ModelPushResult(source_dir=str(src), target=target, backend="huggingface", pushed=True, message="uploaded to huggingface")
    except Exception as exc:
        msg = (
            f"huggingface push failed: {exc}. "
            "Set HF_TOKEN and install huggingface_hub, or push to a local target path."
        )
        return ModelPushResult(source_dir=str(src), target=target, backend="huggingface", pushed=False, message=msg)


def list_local_models(cache_root: str | Path) -> list[dict[str, Any]]:
    root = Path(cache_root)
    if not root.exists():
        return []
    out: list[dict[str, Any]] = []
    for child in sorted(p for p in root.iterdir() if p.is_dir()):
        size_bytes = 0
        for f in child.rglob("*"):
            if f.is_file():
                size_bytes += f.stat().st_size
        out.append(
            {
                "name": child.name,
                "path": str(child),
                "size_bytes": size_bytes,
                "updated_utc": now_utc_iso(),
            }
        )
    return out


def write_model_registry_index(cache_root: str | Path) -> Path:
    root = ensure_dir(cache_root)
    index = {"models": list_local_models(root), "generated_utc": now_utc_iso()}
    out = root / "index.json"
    save_json(out, index)
    return out
