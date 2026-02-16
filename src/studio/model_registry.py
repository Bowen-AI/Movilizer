from __future__ import annotations

import argparse
import json
from pathlib import Path

from .models.registry import list_local_models, pull_model, push_model, write_model_registry_index
from .utils import load_yaml, setup_logging


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Model registry sync (Hugging Face + local)")
    p.add_argument("--config", default="configs/model_registry/default.yaml")
    p.add_argument("--cache_root", default=None)
    p.add_argument("--log_level", default="INFO")

    sub = p.add_subparsers(dest="command", required=True)

    pull = sub.add_parser("pull", help="Pull model from HF repo ID or local path")
    pull.add_argument("--source", required=True, help="HF repo id (org/model) or local path")
    pull.add_argument("--revision", default=None)
    pull.add_argument("--local_files_only", action="store_true")

    push = sub.add_parser("push", help="Push local model dir to HF or local target")
    push.add_argument("--source_dir", required=True)
    push.add_argument("--target", required=True, help="HF repo id or local target path")
    push.add_argument("--private", action="store_true")

    sub.add_parser("list", help="List local cached models")

    return p.parse_args()


def _resolve_cache_root(args: argparse.Namespace) -> Path:
    cfg = load_yaml(args.config) if Path(args.config).exists() else {}
    if args.cache_root:
        return Path(args.cache_root).resolve()
    return Path(cfg.get("cache_root", "models/cache")).resolve()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)
    cache_root = _resolve_cache_root(args)

    if args.command == "pull":
        result = pull_model(
            source=args.source,
            cache_root=cache_root,
            revision=args.revision,
            local_files_only=bool(args.local_files_only),
        )
        write_model_registry_index(cache_root)
        print(json.dumps(result.__dict__, indent=2, ensure_ascii=True))
        raise SystemExit(0 if result.pulled else 1)

    if args.command == "push":
        result = push_model(
            source_dir=args.source_dir,
            target=args.target,
            private=bool(args.private),
        )
        write_model_registry_index(cache_root)
        print(json.dumps(result.__dict__, indent=2, ensure_ascii=True))
        raise SystemExit(0 if result.pushed else 1)

    if args.command == "list":
        payload = {"cache_root": str(cache_root), "models": list_local_models(cache_root)}
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return


if __name__ == "__main__":
    main()
