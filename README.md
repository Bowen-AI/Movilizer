# Personalized Generative Studio

A complete, local-first repository for:
- SDXL identity LoRA training
- batched multi-project image+video generation
- dialogue voice + music mixing + final MP4 mux
- modular judges (image/video/audio) + self-evolving loop
- non-destructive shot tweaks via patch YAMLs
- Slurm jobs for 2x80GB GPUs
- natural-language AI command prompt interface (`studio.ai`)

## Features

- Workspace / project / scene / shot object model in YAML and JSON Schemas.
- Deterministic compilation and caching using content hashes.
- Incremental reruns: skip unchanged tasks, rerender frame ranges only.
- Offline-capable baseline generation + optional heavy model integrations.
- Full artifact provenance: config snapshots, git hash, model IDs, LoRA checksums.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 1) Run full studio pipeline

```bash
python -m studio.run --workspace workspace.yaml --projects all --scenes all
```

### 2) Compile only

```bash
python -m studio.run --workspace workspace.yaml --project my_makeover --scene scene_01 --compile_only
```

### 3) Apply tweak patch and rerun a scene

```bash
python -m studio.run --workspace workspace.yaml --project my_makeover --scene scene_01 \
  --patch projects/my_makeover/scripts/scenes/patches/scene_01.patch.001.yaml
```

### 4) Natural-language command interface

```bash
python -m studio.ai "Make scene_01 shot_03 more cinematic, reduce makeup, keep identity strong; regenerate only frames 120-220"
python -m studio.ai --interactive
```

### 5) Train identity LoRA

```bash
python -m studio.train_identity --config configs/train/sdxl_lora.yaml
```

### 6) Evaluate outputs

```bash
python -m studio.eval --workspace workspace.yaml --run_id <run_id>
```

### 7) Evolve prompts/params

```bash
python -m studio.evolve --workspace workspace.yaml --projects my_makeover --budget small
```

## Add A New Project

1. Copy `projects/my_makeover/` to `projects/<new_name>/`.
2. Edit `projects/<new_name>/project.yaml`.
3. Add scene YAMLs in `projects/<new_name>/scripts/scenes/`.
4. Add dialog YAMLs in `projects/<new_name>/scripts/dialogs/`.
5. Register the project in `workspace.yaml`.

## Write A Scene + Dialogs

- Scene: `projects/<name>/scripts/scenes/<scene>.yaml`
- Dialog: `projects/<name>/scripts/dialogs/<dialog>.yaml`

See examples in `docs/AI/EXAMPLES/` and human docs in `docs/HUMAN/SCENES.md`.

## Produce final.mp4 With Voices + Music

```bash
python -m studio.run --workspace workspace.yaml --project my_makeover --scene scene_01 scene_02
```

Final outputs:
- `outputs/<run_id>/my_makeover/scene_01/scene.mp4`
- `outputs/<run_id>/my_makeover/scene_02/scene.mp4`
- `outputs/<run_id>/my_makeover/final.mp4`

## Slurm (2 GPUs)

- `slurm/train_identity_2gpu.sbatch`
- `slurm/run_studio_2gpu.sbatch`
- `slurm/eval.sbatch`
- `slurm/evolve.sbatch`

See `docs/HUMAN/SLURM.md`.

## Documentation

Human docs:
- `docs/HUMAN/PROJECTS.md`
- `docs/HUMAN/SCENES.md`
- `docs/HUMAN/TWEAKS.md`
- `docs/HUMAN/PIPELINE.md`
- `docs/HUMAN/SLURM.md`
- `docs/HUMAN/AUDIO.md`
- `docs/HUMAN/VIDEO.md`
- `docs/HUMAN/JUDGES.md`
- `docs/HUMAN/TROUBLESHOOTING.md`
- `docs/HUMAN/SAFETY.md`

AI docs:
- `docs/AI/*.schema.json`
- `docs/AI/PLAYBOOK.md`
- `docs/AI/COMMANDS.md`
- `docs/AI/EXAMPLES/`

## Graceful Fallback Strategy

If heavy dependencies (diffusers/torch/insightface/ffmpeg) are unavailable:
- generation falls back to lightweight synthetic frame renderer,
- training falls back to mock LoRA checkpoint generation,
- advanced judges fall back to heuristic metrics,
- clear warnings are logged with installation guidance.

This keeps the repo runnable end-to-end while allowing upgrade to full GPU workflows.
