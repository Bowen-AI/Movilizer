from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ai_cmd.planner import build_plan, execute_plan, pretty_plan_json
from .utils import get_logger, load_yaml, setup_logging

logger = get_logger("ai")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Natural-language command interface for studio")
    p.add_argument("request", nargs="?", default=None, help="Natural-language command")
    p.add_argument("--workspace", default="workspace.yaml")
    p.add_argument("--project", default=None)
    p.add_argument("--scene", default=None)
    p.add_argument("--shot", default=None)
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--backend", choices=["rules", "llm"], default=None)
    p.add_argument("--dry_run", action="store_true")
    p.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    p.add_argument("--run_id", default=None)
    p.add_argument("--config", default="configs/ai_cmd/default.yaml")
    p.add_argument("--log_level", default="INFO")
    return p.parse_args()


def _run_single_request(args: argparse.Namespace, request: str) -> None:
    cfg = load_yaml(args.config) if Path(args.config).exists() else {}
    backend = args.backend or str(cfg.get("backend", "rules"))

    context = {
        "project": args.project,
        "scene": args.scene,
        "shot": args.shot,
    }

    plan = build_plan(
        request=request,
        context=context,
        backend=backend,
        backend_config=cfg,
        dry_run=bool(args.dry_run),
    )

    print("Action Plan:")
    print(pretty_plan_json(plan))

    result = execute_plan(
        plan=plan,
        workspace_path=Path(args.workspace).resolve(),
        yes=bool(args.yes),
        dry_run=bool(args.dry_run),
        run_id=args.run_id,
    )

    print("Execution Result:")
    print(json.dumps(result, indent=2, ensure_ascii=True))


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    if args.interactive:
        print("Studio AI interactive mode. Type 'exit' to quit.")
        while True:
            request = input("studio.ai> ").strip()
            if not request or request.lower() in {"exit", "quit"}:
                break
            _run_single_request(args, request)
    else:
        if not args.request:
            raise SystemExit("Provide a request string or use --interactive")
        _run_single_request(args, args.request)


if __name__ == "__main__":
    main()
