from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Studio umbrella CLI")
    parser.add_argument(
        "command",
        choices=["run", "train_identity", "eval", "evolve", "tweak", "ai", "server", "model_registry", "daemon", "discover"],
        help="Subcommand to execute",
    )
    parser.add_argument("args", nargs=argparse.REMAINDER)
    ns = parser.parse_args()

    module = f"studio.{ns.command}"
    cmd = [sys.executable, "-m", module, *ns.args]
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
