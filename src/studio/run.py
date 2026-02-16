from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .config import load_workspace, resolve_projects, resolve_scene_files
from .judges.runner import evaluate_run
from .pipeline.executor import compile_scene, execute_compiled_scene, finalize_project_video
from .utils import ensure_dir, get_logger, setup_logging

logger = get_logger("run")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run studio generation pipeline")
    parser.add_argument("--workspace", required=True, help="Path to workspace.yaml")

    parser.add_argument("--projects", nargs="+", default=None, help="Project names or 'all'")
    parser.add_argument("--project", default=None, help="Single project name (shortcut)")

    parser.add_argument("--scenes", nargs="+", default=None, help="Scene names or 'all'")
    parser.add_argument("--scene", default=None, help="Single scene name (shortcut)")

    parser.add_argument("--shots", nargs="+", default=None, help="Optional shot IDs subset")
    parser.add_argument("--shot", default=None, help="Single shot ID (shortcut)")

    parser.add_argument("--patch", action="append", default=[], help="Patch YAML path (can repeat)")
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--compile_only", action="store_true")
    parser.add_argument("--skip_eval", action="store_true")
    parser.add_argument("--run_id", default=None)
    parser.add_argument("--log_level", default="INFO")
    return parser.parse_args()


def _merge_selector(many: list[str] | None, one: str | None) -> list[str]:
    if one:
        return [one]
    if many:
        return many
    return ["all"]


def main() -> None:
    args = _parse_args()
    setup_logging(args.log_level)

    workspace = load_workspace(args.workspace)
    ws_dir = Path(workspace["_workspace_dir"])

    projects_sel = _merge_selector(args.projects, args.project)
    scenes_sel = _merge_selector(args.scenes, args.scene)
    shots_sel = _merge_selector(args.shots, args.shot)
    if shots_sel == ["all"]:
        shots_sel = []

    output_root = ensure_dir((ws_dir / workspace.get("output_root", "outputs")).resolve())
    run_id = args.run_id or datetime.utcnow().strftime("run_%Y%m%d_%H%M%S")

    projects = resolve_projects(workspace, projects_sel)
    if not projects:
        raise SystemExit("No projects selected/resolved.")

    patch_paths = [Path(p).resolve() for p in args.patch]

    plan_lines: list[str] = []
    for project in projects:
        scene_files = resolve_scene_files(project, scenes_sel)
        for scene_file in scene_files:
            plan_lines.append(f"- {project.name}: {scene_file.stem}")

    logger.info("Run ID: %s", run_id)
    logger.info("Planned scenes:\n%s", "\n".join(plan_lines) if plan_lines else "(none)")

    if args.dry_run:
        logger.info("Dry run requested; no execution performed.")
        return

    project_to_scene_names: dict[str, list[str]] = {}

    for project in projects:
        scene_files = resolve_scene_files(project, scenes_sel)
        scene_names_for_project: list[str] = []

        for scene_file in scene_files:
            scene_name = scene_file.stem
            compiled_shots, scene_data, _dialog = compile_scene(
                workspace=workspace,
                project=project,
                scene_path=scene_file,
                run_id=run_id,
                output_root=output_root,
                selected_shot_ids=shots_sel,
                patch_paths=patch_paths,
            )
            if not compiled_shots:
                logger.warning("No compiled shots for %s/%s", project.name, scene_name)
                continue

            scene_name = compiled_shots[0].scene
            scene_names_for_project.append(scene_name)

            execute_compiled_scene(
                workspace=workspace,
                project=project,
                scene_name=scene_name,
                compiled_shots=compiled_shots,
                output_root=output_root,
                run_id=run_id,
                resume=bool(args.resume),
                compile_only=bool(args.compile_only),
            )

        if not args.compile_only and scene_names_for_project:
            final_path = finalize_project_video(
                output_root=output_root,
                run_id=run_id,
                project_name=project.name,
                scene_names=scene_names_for_project,
            )
            logger.info("Project final video: %s", final_path)

        project_to_scene_names[project.name] = scene_names_for_project

    if not args.compile_only and not args.skip_eval:
        eval_root = evaluate_run(output_root=output_root, run_id=run_id)
        logger.info("Evaluation written to %s", eval_root)

    logger.info("Studio run complete. run_id=%s", run_id)


if __name__ == "__main__":
    main()
