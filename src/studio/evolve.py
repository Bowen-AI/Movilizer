from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import load_workspace
from .utils import ensure_dir, get_logger, load_yaml, save_json, save_yaml, setup_logging, stable_hash

logger = get_logger("evolve")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Self-evolving optimization loop")
    p.add_argument("--workspace", required=True)
    p.add_argument("--projects", nargs="+", default=["all"])
    p.add_argument("--budget", default="small", choices=["small", "medium", "large"])
    p.add_argument("--config", default="configs/evolve/default.yaml")
    p.add_argument("--mode", default=None, choices=["weighted_sum", "pareto"])
    p.add_argument("--resume", action="store_true")
    p.add_argument("--run_id", default=None)
    p.add_argument("--log_level", default="INFO")
    return p.parse_args()


def _mutate(search_space: dict[str, Any], trial_idx: int, seed: int = 42) -> dict[str, Any]:
    rng = random.Random(seed + trial_idx)
    cfg_min, cfg_max = search_space.get("cfg_scale", [4.5, 9.0])
    steps_min, steps_max = search_space.get("steps", [20, 45])
    prompt_mut = rng.choice(search_space.get("prompt_mutations", ["cinematic lighting"]))
    neg_mut = rng.choice(search_space.get("negative_mutations", ["plastic skin"]))
    return {
        "guidance_scale": round(rng.uniform(float(cfg_min), float(cfg_max)), 3),
        "num_inference_steps": int(rng.randint(int(steps_min), int(steps_max))),
        "prompt_mutation": prompt_mut,
        "negative_mutation": neg_mut,
    }


def _proxy_objective(mutation: dict[str, Any], mode: str) -> dict[str, float]:
    # Fast proxy score for baseline evolution loop; replace with full rerun+judge objective if desired.
    ident = max(0.0, 1.0 - abs(mutation["guidance_scale"] - 6.8) / 6.0)
    flicker = min(1.0, abs(mutation["num_inference_steps"] - 32) / 32.0)
    adherence = 0.65 + (0.2 if "cinematic" in mutation["prompt_mutation"] else 0.0)
    quality = min(1.0, mutation["num_inference_steps"] / 50.0)

    if mode == "pareto":
        return {
            "identity_similarity": ident,
            "negative_flicker": 1.0 - flicker,
            "aggregate": 0.0,
        }

    aggregate = 0.45 * ident + 0.25 * adherence + 0.2 * quality + 0.1 * (1.0 - flicker)
    return {
        "identity_similarity": ident,
        "adherence": adherence,
        "quality": quality,
        "flicker": flicker,
        "aggregate": aggregate,
    }


def _constraints_ok(score: dict[str, float], constraints: dict[str, Any]) -> bool:
    min_identity = float(constraints.get("min_identity_similarity", 0.0))
    max_flicker = float(constraints.get("max_flicker", 1.0))

    identity = float(score.get("identity_similarity", 0.0))
    flicker = float(score.get("flicker", 0.0))
    return identity >= min_identity and flicker <= max_flicker


def main() -> None:
    args = _parse_args()
    setup_logging(args.log_level)

    ws = load_workspace(args.workspace)
    evo_cfg = load_yaml(args.config)
    mode = args.mode or str(evo_cfg.get("mode", "weighted_sum"))

    run_id = args.run_id or datetime.utcnow().strftime("evolve_%Y%m%d_%H%M%S")
    out_root = ensure_dir((Path(ws["_workspace_dir"]) / evo_cfg.get("snapshot_dir", "outputs/evolve")).resolve())
    run_dir = ensure_dir(out_root / run_id)

    budget_map = evo_cfg.get("trials", {"small": 8, "medium": 24, "large": 64})
    n_trials = int(budget_map.get(args.budget, 8))

    search_space = evo_cfg.get("search_space", {})
    constraints = evo_cfg.get("constraints", {})

    seed = int(stable_hash({"run_id": run_id, "workspace": args.workspace})[:8], 16)
    rows: list[dict[str, Any]] = []

    start_idx = 0
    resume_file = run_dir / "trials.json"
    if args.resume and resume_file.exists():
        existing = json_load(resume_file)
        rows.extend(existing.get("rows", []))
        start_idx = len(rows)
        logger.info("Resuming evolve run at trial %s", start_idx)

    for trial_idx in range(start_idx, n_trials):
        mutation = _mutate(search_space, trial_idx, seed=seed)
        score = _proxy_objective(mutation, mode=mode)
        feasible = _constraints_ok(score, constraints)

        row = {
            "trial": trial_idx,
            "feasible": feasible,
            **mutation,
            **score,
        }
        rows.append(row)

        save_json(run_dir / f"trial_{trial_idx:04d}.json", row)
        save_json(
            resume_file,
            {
                "run_id": run_id,
                "mode": mode,
                "rows": rows,
            },
        )

    feasible_rows = [r for r in rows if bool(r.get("feasible", False))]
    ranked = sorted(
        feasible_rows if feasible_rows else rows,
        key=lambda r: float(r.get("aggregate", r.get("identity_similarity", 0.0))),
        reverse=True,
    )

    best = ranked[0] if ranked else {}
    best_config = {
        "project_selection": args.projects,
        "mode": mode,
        "budget": args.budget,
        "best_trial": best,
    }

    save_yaml(run_dir / "best_config.yaml", best_config)
    save_json(run_dir / "summary.json", {"run_id": run_id, "trials": len(rows), "best": best})

    csv_path = run_dir / "leaderboard.csv"
    fields = sorted({k for row in rows for k in row.keys()}) if rows else ["trial"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    logger.info("Evolve complete: %s", run_dir)


def json_load(path: Path) -> dict[str, Any]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
