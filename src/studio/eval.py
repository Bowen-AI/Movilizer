from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_workspace
from .judges.runner import evaluate_run
from .utils import get_logger, setup_logging

logger = get_logger("eval")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate a completed studio run")
    p.add_argument("--workspace", required=True)
    p.add_argument("--run_id", required=True)
    p.add_argument("--log_level", default="INFO")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)
    ws = load_workspace(args.workspace)
    output_root = (Path(ws["_workspace_dir"]) / ws.get("output_root", "outputs")).resolve()
    eval_root = evaluate_run(output_root=output_root, run_id=args.run_id)
    logger.info("Done: %s", eval_root)


if __name__ == "__main__":
    main()
