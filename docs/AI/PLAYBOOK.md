# AI Playbook

This playbook defines strict conventions for operating this repository as an autonomous or semi-autonomous agent.

## 1) Order of operations

1. Validate `workspace.yaml` against `workspace.schema.json`.
2. Resolve selected projects and load each `project.yaml`.
3. Optionally resolve model sources (`local` or `huggingface`) into model cache.
4. Resolve selected scene YAML files.
5. Compile scene + shot prompts (template + layered overrides).
6. Merge prompt media references from workspace/project/scene/shot.
7. Apply patch YAML files in deterministic order.
8. Write compiled artifacts to `outputs/<run_id>/<project>/<scene>/<shot>/compiled/`.
9. Compute deterministic signatures for frame/audio tasks.
10. Execute generation/audio assembly only for invalidated tasks.
11. Assemble clips -> scenes -> project final.
12. Evaluate via judges and write leaderboard/scores.

## 2) Prompt layering contract

Prompt = `global_guidelines.prompt` + `project.style_bible.vibe_guidelines` + `scene.vibe_overrides.prompt` + `shot.prompt` + patch prompt ops.

Negative prompt = `global_guidelines.negative_prompt` + `scene.vibe_overrides.negative_prompt` + `shot.negative_prompt` + patch negative ops.

Prompt-media references are merged in this precedence order:
- workspace
- project
- scene
- shot
- `shot.references.prompt_images/prompt_videos`

## 3) Patch application contract

- Patches are applied after base scene load and after template composition.
- Apply all matching patches sorted by filename.
- Match scope by `target.project`, `target.scene`, and optional `target.shot`.
- Supported ops are exactly those in `patch.schema.json`.

## 4) Deterministic cache contract

Task signatures include:
- compiled hash,
- prompt/negative prompt,
- refs and prompt media,
- seed and inference params,
- model IDs + LoRA checksums,
- git hash.

Skip task only if signature unchanged and required outputs exist.

## 5) Scene/shot outputs contract

Each shot must produce:
- `frames/`
- `compiled/compiled_scene.yaml`
- `compiled/compiled_shot.yaml`
- `compiled/compiled_prompt.txt`
- `compiled/compiled_negative_prompt.txt`
- `compiled/compiled_metadata.json`
- `compiled/compiled_prompt.diff.txt`
- `metadata.json`
- `clip.mp4` (or fallback note when ffmpeg unavailable)

Each scene must produce:
- `scene.mp4`
- scene-level `audio/` tracks

Each project run must produce:
- `final.mp4`

## 6) AI command interface contract

1. Convert NL request into Action Plan JSON.
2. Print plan before execution unless `--yes`.
3. Save AI command artifacts:
   - `request.txt`
   - `action_plan.json`
   - `generated_patch.yaml` (if created)
   - `execution_log.txt`
4. Execute deterministically from the plan.

## 7) Server contract

`studio.server` must expose:
- health endpoint,
- run endpoint,
- AI plan/execute endpoints,
- model list/pull/push endpoints.

## 8) Evolution loop contract

- Search over prompt/inference parameters.
- Record per-trial artifacts and summary.
- Respect constraints (`min_identity_similarity`, `max_flicker`).
- Resume from trial snapshots when requested.
