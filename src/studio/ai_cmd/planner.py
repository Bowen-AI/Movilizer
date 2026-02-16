from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from ..utils import ensure_dir, get_logger, save_json, save_yaml, write_text
from .llm_backend import plan_with_llm
from .rules_backend import plan_from_rules
from .schemas import ActionPlan

logger = get_logger("ai_cmd.planner")


def build_plan(
    request: str,
    context: dict[str, Any],
    backend: str,
    backend_config: dict[str, Any],
    dry_run: bool,
) -> ActionPlan:
    if backend == "llm":
        llm_cfg = backend_config.get("llm", {})
        return plan_with_llm(
            request=request,
            context=context,
            endpoint=str(llm_cfg.get("endpoint", "")),
            model=str(llm_cfg.get("model", "")),
            api_key_env=str(llm_cfg.get("api_key_env", "OPENAI_API_KEY")),
            dry_run=dry_run,
        )
    return plan_from_rules(request=request, context=context, dry_run=dry_run)


def _next_patch_path(project_root: Path, scene_name: str) -> Path:
    patch_dir = project_root / "scripts" / "scenes" / "patches"
    ensure_dir(patch_dir)
    existing = sorted(patch_dir.glob(f"{scene_name}.patch.*.yaml"))
    n = 1
    if existing:
        last = existing[-1].stem.split(".")[-1]
        if last.isdigit():
            n = int(last) + 1
    return patch_dir / f"{scene_name}.patch.{n:03d}.yaml"


def _project_root_from_workspace(workspace_path: Path, project_name: str) -> Path:
    import yaml

    ws = yaml.safe_load(workspace_path.read_text(encoding="utf-8")) or {}
    for ref in ws.get("projects", []):
        if str(ref.get("name")) == project_name:
            project_yaml = ref.get("path")
            if project_yaml:
                p = Path(project_yaml)
                if not p.is_absolute():
                    p = (workspace_path.parent / p).resolve()
                return p.parent
    raise ValueError(f"Project not found in workspace: {project_name}")


def execute_plan(
    plan: ActionPlan,
    workspace_path: Path,
    yes: bool,
    dry_run: bool,
    run_id: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "run_id": run_id or datetime.utcnow().strftime("ai_%Y%m%d_%H%M%S"),
        "commands": [],
        "patch_path": None,
    }

    artifacts_dir = workspace_path.parent / "outputs" / result["run_id"] / "ai_cmd"
    ensure_dir(artifacts_dir)

    write_text(artifacts_dir / "request.txt", plan.request + "\n")
    save_json(artifacts_dir / "action_plan.json", plan.to_dict())

    if not yes and not dry_run:
        reply = input("Execute action plan? [y/N]: ").strip().lower()
        if reply not in {"y", "yes"}:
            write_text(artifacts_dir / "execution_log.txt", "Execution aborted by user confirmation.\n")
            return result

    log_lines: list[str] = []
    generated_patch: dict[str, Any] | None = None

    for action in plan.actions:
        kind = action.type
        payload = action.payload

        if kind == "apply_patch":
            target = payload.get("target", {})
            project = target.get("project")
            scene = target.get("scene")
            if not project or not scene:
                log_lines.append("apply_patch skipped: missing project/scene target")
                continue

            project_root = _project_root_from_workspace(workspace_path, str(project))
            patch_path = _next_patch_path(project_root, str(scene))
            generated_patch = {
                "target": {
                    "project": project,
                    "scene": scene,
                    "shot": target.get("shot"),
                },
                "ops": payload.get("ops", []),
            }
            save_yaml(patch_path, generated_patch)
            result["patch_path"] = str(patch_path)
            save_yaml(artifacts_dir / "generated_patch.yaml", generated_patch)
            log_lines.append(f"Generated patch: {patch_path}")

        elif kind in {"compile_only", "rerun_subset"}:
            project = payload.get("project") or plan.context.get("project")
            scene = payload.get("scene") or plan.context.get("scene")
            shot = payload.get("shot") or plan.context.get("shot")

            cmd = [
                "python",
                "-m",
                "studio.run",
                "--workspace",
                str(workspace_path),
                "--run_id",
                str(result["run_id"]),
            ]
            if project:
                cmd += ["--project", str(project)]
            else:
                cmd += ["--projects", "all"]

            if scene:
                cmd += ["--scene", str(scene)]
            else:
                cmd += ["--scenes", "all"]

            if shot:
                cmd += ["--shot", str(shot)]

            if kind == "compile_only":
                cmd.append("--compile_only")

            if result.get("patch_path"):
                cmd += ["--patch", str(result["patch_path"])]

            if dry_run:
                cmd.append("--dry_run")

            result["commands"].append(cmd)
            log_lines.append("RUN: " + " ".join(cmd))

            if not dry_run:
                proc = subprocess.run(cmd, capture_output=True, text=True)
                log_lines.append(proc.stdout)
                log_lines.append(proc.stderr)
                if proc.returncode != 0:
                    raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}")

        elif kind == "schedule_evolve":
            project = payload.get("project") or plan.context.get("project")
            budget = payload.get("budget", "small")
            cmd = [
                "python",
                "-m",
                "studio.evolve",
                "--workspace",
                str(workspace_path),
                "--budget",
                str(budget),
            ]
            if project:
                cmd += ["--projects", str(project)]
            result["commands"].append(cmd)
            log_lines.append("RUN: " + " ".join(cmd))
            if not dry_run:
                proc = subprocess.run(cmd, capture_output=True, text=True)
                log_lines.append(proc.stdout)
                log_lines.append(proc.stderr)
                if proc.returncode != 0:
                    raise RuntimeError(f"Evolve command failed ({proc.returncode})")

    write_text(artifacts_dir / "execution_log.txt", "\n".join(log_lines) + "\n")
    if generated_patch and not (artifacts_dir / "generated_patch.yaml").exists():
        save_yaml(artifacts_dir / "generated_patch.yaml", generated_patch)
    return result


def pretty_plan_json(plan: ActionPlan) -> str:
    return json.dumps(plan.to_dict(), indent=2, ensure_ascii=True)
