from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

LOGGER_NAME = "studio"


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def save_yaml(path: str | Path, data: Any) -> None:
    ensure_dir(Path(path).parent)
    with Path(path).open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=False)


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str | Path, data: Any, indent: int = 2) -> None:
    ensure_dir(Path(path).parent)
    with Path(path).open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=True)


def stable_hash(payload: Any) -> str:
    normalized = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path: str | Path, default: str = "") -> str:
    p = Path(path)
    if not p.exists():
        return default
    return p.read_text(encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    ensure_dir(Path(path).parent)
    Path(path).write_text(text, encoding="utf-8")


def get_git_hash(default: str = "unknown") -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out or default
    except Exception:
        return default


def file_exists(path: str | Path) -> bool:
    return Path(path).exists()


def which(cmd: str) -> str | None:
    for segment in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(segment) / cmd
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def list_files(root: str | Path, patterns: tuple[str, ...] = ("*",)) -> list[Path]:
    r = Path(root)
    out: list[Path] = []
    for pattern in patterns:
        out.extend(r.rglob(pattern))
    return sorted({p for p in out if p.is_file()})
