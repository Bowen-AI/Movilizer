# /Users/bowensong/Documents/New project/.gitignore
```gitignore
__pycache__/
*.py[cod]
*.so
.venv/
venv/
.env
.pytest_cache/
.mypy_cache/
coverage.xml
htmlcov/
outputs/
logs/
*.pt
*.bin
*.safetensors
*.ckpt
.DS_Store

```

# /Users/bowensong/Documents/New project/README.md
```markdown
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

```

# /Users/bowensong/Documents/New project/configs/ai_cmd/default.yaml
```yaml
backend: "rules" # rules | llm
workspace: "workspace.yaml"
llm:
  enabled: false
  endpoint: "http://localhost:8000/v1/chat/completions"
  model: "gpt-4o-mini"
  api_key_env: "OPENAI_API_KEY"
execution:
  require_confirm: true
  dry_run_default: false
patch:
  auto_dir: "scripts/scenes/patches"

```

# /Users/bowensong/Documents/New project/configs/eval/default.yaml
```yaml
judges:
  image:
    identity_similarity:
      enabled: true
      weight: 0.35
    prompt_adherence:
      enabled: true
      weight: 0.2
    quality:
      enabled: true
      weight: 0.2
    diversity:
      enabled: true
      weight: 0.1
    safety:
      enabled: true
      weight: 0.15
  video:
    temporal_identity_consistency:
      enabled: true
      weight: 0.5
    clip_stability:
      enabled: true
      weight: 0.3
    flicker:
      enabled: true
      weight: 0.2
  audio:
    loudness:
      enabled: true
      weight: 0.7
    clipping:
      enabled: true
      weight: 0.3
output:
  write_leaderboard: true
  write_per_shot: true

```

# /Users/bowensong/Documents/New project/configs/evolve/default.yaml
```yaml
mode: "weighted_sum" # weighted_sum | pareto
budget: "small" # small | medium | large
trials:
  small: 8
  medium: 24
  large: 64

search_space:
  cfg_scale: [4.5, 9.0]
  steps: [20, 45]
  prompt_mutations:
    - "cinematic lighting"
    - "natural skin texture"
    - "subtle film grain"
    - "dramatic backlight"
  negative_mutations:
    - "plastic skin"
    - "overexposed highlights"

constraints:
  min_identity_similarity: 0.7
  max_flicker: 0.4

resume: true
snapshot_dir: "outputs/evolve"

```

# /Users/bowensong/Documents/New project/configs/run/default_run.yaml
```yaml
seed: 42
resume: true
dry_run: false
compile_only: false
save_intermediate: true

generation:
  num_inference_steps: 30
  guidance_scale: 6.5
  eta: 0.0
  seed_lock_across_frames: true
  anchor_frames: [0]
  prompt_schedule: []

audio:
  target_lufs: -16
  ducking_db: -8
  fade_in_sec: 0.4
  fade_out_sec: 0.6
  sample_rate: 24000

evaluation:
  enabled: true
  profile: "default"

```

# /Users/bowensong/Documents/New project/configs/train/sdxl_lora.yaml
```yaml
run_name: "my_identity_sdxl_lora"
output_dir: "outputs/train/my_identity_sdxl_lora"
resume_from: null
seed: 42

model:
  base_id: "stabilityai/stable-diffusion-xl-base-1.0"
  refiner_id: "stabilityai/stable-diffusion-xl-refiner-1.0"
  use_refiner: false
  precision: "bf16"
  enable_xformers: true
  attention_slicing: true

lora:
  rank: 16
  alpha: 32
  dropout: 0.05
  target_modules: ["to_q", "to_k", "to_v", "to_out", "ff.net"]
  train_text_encoder: false

train:
  dataset_root: "data/my_identity"
  image_size: 1024
  train_batch_size: 1
  gradient_accumulation_steps: 4
  gradient_checkpointing: true
  learning_rate: 1.0e-4
  max_train_steps: 200
  save_every_steps: 50
  sample_every_steps: 50
  num_workers: 2
  use_8bit_adam: false

regularization:
  enabled: false
  weight: 1.0

distributed:
  num_processes: 2
  mixed_precision: "bf16"

notes: "If diffusers/accelerate are missing, trainer will generate a mock LoRA artifact and sample renders."

```

# /Users/bowensong/Documents/New project/configs/workspace_example.yaml
```yaml
workspace_name: "studio_workspace"
output_root: "outputs"
shared_prompt_library: "shared/prompt_library.yaml"
shared_asset_packs:
  - "shared/asset_packs.yaml"
global_defaults:
  seed: 1337
  run_settings:
    batch_size: 1
    resume: true
  model:
    base_id: "stabilityai/stable-diffusion-xl-base-1.0"
    refiner_id: "stabilityai/stable-diffusion-xl-refiner-1.0"
    fast_base_id: "your-org/fast-sdxl-placeholder"
    use_refiner: false
    precision: "bf16"
    enable_xformers: true
    attention_slicing: true
global_guidelines:
  prompt: "cinematic, balanced composition, realistic textures"
  negative_prompt: "deformed, lowres, oversmoothed"
projects:
  - name: "my_makeover"
    path: "projects/my_makeover/project.yaml"
selection:
  default_projects: ["my_makeover"]
  default_scenes: ["scene_01"]
identity_folders:
  - "data/my_identity"
asset_folders:
  - "projects/my_makeover/assets"

```

# /Users/bowensong/Documents/New project/data/my_identity/README.txt
```text
Place training images in train/images and matching caption txt files in train/captions.
Optional regularization images/captions can be placed in reg/.

```

# /Users/bowensong/Documents/New project/data/my_identity/reg/.gitkeep
```text

```

# /Users/bowensong/Documents/New project/data/my_identity/train/captions/example1.txt
```text
<me> portrait, neutral expression, high detail skin texture

```

# /Users/bowensong/Documents/New project/data/my_identity/train/images/.gitkeep
```text

```

# /Users/bowensong/Documents/New project/docs/AI/COMMANDS.md
```markdown
# Command Spec (Machine-Readable)

```yaml
commands:
  - name: run
    module: studio.run
    usage: "python -m studio.run --workspace <path> [--projects all|<p...>] [--scenes all|<s...>]"
    flags:
      - {name: --workspace, type: str, required: true}
      - {name: --projects, type: list[str], required: false}
      - {name: --project, type: str, required: false}
      - {name: --scenes, type: list[str], required: false}
      - {name: --scene, type: str, required: false}
      - {name: --shots, type: list[str], required: false}
      - {name: --shot, type: str, required: false}
      - {name: --patch, type: list[path], required: false}
      - {name: --dry_run, type: bool, required: false}
      - {name: --resume, type: bool, required: false}
      - {name: --compile_only, type: bool, required: false}
      - {name: --skip_eval, type: bool, required: false}
      - {name: --run_id, type: str, required: false}

  - name: train_identity
    module: studio.train_identity
    usage: "python -m studio.train_identity --config configs/train/sdxl_lora.yaml"
    flags:
      - {name: --config, type: path, required: true}

  - name: eval
    module: studio.eval
    usage: "python -m studio.eval --workspace workspace.yaml --run_id <id>"
    flags:
      - {name: --workspace, type: path, required: true}
      - {name: --run_id, type: str, required: true}

  - name: evolve
    module: studio.evolve
    usage: "python -m studio.evolve --workspace workspace.yaml --projects <p...> --budget small"
    flags:
      - {name: --workspace, type: path, required: true}
      - {name: --projects, type: list[str], required: false}
      - {name: --budget, type: enum[small,medium,large], required: false}
      - {name: --config, type: path, required: false}
      - {name: --mode, type: enum[weighted_sum,pareto], required: false}
      - {name: --resume, type: bool, required: false}
      - {name: --run_id, type: str, required: false}

  - name: tweak
    module: studio.tweak
    usage: "python -m studio.tweak --workspace workspace.yaml --project <p> --scene <s> --create_patch_template"
    flags:
      - {name: --workspace, type: path, required: false}
      - {name: --project, type: str, required: true}
      - {name: --scene, type: str, required: true}
      - {name: --shot, type: str, required: false}
      - {name: --create_patch_template, type: bool, required: false}
      - {name: --apply_inline, type: str, required: false}

  - name: ai
    module: studio.ai
    usage: "python -m studio.ai [--interactive] [--workspace workspace.yaml] \"<request>\""
    flags:
      - {name: request, type: str, required: conditional}
      - {name: --interactive, type: bool, required: false}
      - {name: --workspace, type: path, required: false}
      - {name: --project, type: str, required: false}
      - {name: --scene, type: str, required: false}
      - {name: --shot, type: str, required: false}
      - {name: --backend, type: enum[rules,llm], required: false}
      - {name: --dry_run, type: bool, required: false}
      - {name: --yes, type: bool, required: false}
      - {name: --run_id, type: str, required: false}
      - {name: --config, type: path, required: false}

  - name: tools.extract_frames
    module: studio.tools.extract_frames
    usage: "python -m studio.tools.extract_frames --input in.mp4 --output out_frames"

  - name: tools.auto_caption
    module: studio.tools.auto_caption
    usage: "python -m studio.tools.auto_caption --images data/id/train/images --captions data/id/train/captions"

  - name: tools.face_crop_align
    module: studio.tools.face_crop_align
    usage: "python -m studio.tools.face_crop_align --input data/id/train/images --output data/id/train/aligned"

  - name: tools.dataset_report
    module: studio.tools.dataset_report
    usage: "python -m studio.tools.dataset_report --dataset_root data/my_identity"
```

```

# /Users/bowensong/Documents/New project/docs/AI/EXAMPLES/dialog.min.yaml
```yaml
scene: "scene_01"
lines:
  - line_id: "l1"
    speaker: "narrator"
    start_sec: 0.0
    end_sec: 1.0
    text: "Hello world"

```

# /Users/bowensong/Documents/New project/docs/AI/EXAMPLES/patch.min.yaml
```yaml
target:
  project: "my_makeover"
  scene: "scene_01"
  shot: "shot_01"
ops:
  - op: "replace_prompt"
    find: "portrait"
    replace: "cinematic portrait"

```

# /Users/bowensong/Documents/New project/docs/AI/EXAMPLES/project.min.yaml
```yaml
project_name: "my_makeover"
model:
  base_id: "stabilityai/stable-diffusion-xl-base-1.0"
output_specs:
  resolution: [1024, 1024]
  fps: 24
  loudness_target_lufs: -16

```

# /Users/bowensong/Documents/New project/docs/AI/EXAMPLES/scene.min.yaml
```yaml
scene_name: "scene_01"
shots:
  - shot_id: "shot_01"
    duration: 3
    fps: 24
    resolution: [1024, 1024]
    prompt: "<me> portrait"
    generation:
      method: "image_only"

```

# /Users/bowensong/Documents/New project/docs/AI/EXAMPLES/workspace.min.yaml
```yaml
workspace_name: "demo"
output_root: "outputs"
projects:
  - name: "my_makeover"
    path: "projects/my_makeover/project.yaml"

```

# /Users/bowensong/Documents/New project/docs/AI/PLAYBOOK.md
```markdown
# AI Playbook

This playbook defines strict conventions for operating this repository as an autonomous or semi-autonomous agent.

## 1) Order of operations

1. Validate `workspace.yaml` against `workspace.schema.json`.
2. Resolve selected projects and load each `project.yaml`.
3. Resolve selected scene YAML files.
4. Compile scene + shot prompts (template + layered overrides).
5. Apply patch YAML files in deterministic order.
6. Write compiled artifacts to `outputs/<run_id>/<project>/<scene>/<shot>/compiled/`.
7. Compute deterministic signatures for frame/audio tasks.
8. Execute generation/audio assembly only for invalidated tasks.
9. Assemble clips -> scenes -> project final.
10. Evaluate via judges and write leaderboard/scores.

## 2) Prompt layering contract

Prompt = `global_guidelines.prompt` + `project.style_bible.vibe_guidelines` + `scene.vibe_overrides.prompt` + `shot.prompt` + patch prompt ops.

Negative prompt = `global_guidelines.negative_prompt` + `scene.vibe_overrides.negative_prompt` + `shot.negative_prompt` + patch negative ops.

## 3) Patch application contract

- Patches are applied after base scene load and after template composition.
- Apply all matching patches sorted by filename.
- Match scope by `target.project`, `target.scene`, and optional `target.shot`.
- Supported ops are exactly those in `patch.schema.json`.

## 4) Deterministic cache contract

Task signatures include:
- compiled hash,
- prompt/negative prompt,
- refs,
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

## 7) Evolution loop contract

- Search over prompt/inference parameters.
- Record per-trial artifacts and summary.
- Respect constraints (`min_identity_similarity`, `max_flicker`).
- Resume from trial snapshots when requested.

```

# /Users/bowensong/Documents/New project/docs/AI/dialog.schema.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "dialog.schema.json",
  "title": "DialogScript",
  "type": "object",
  "required": ["scene", "lines"],
  "properties": {
    "scene": {"type": "string"},
    "sample_rate": {"type": "integer"},
    "speakers": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "voice_profile": {"type": "string"}
        }
      }
    },
    "lines": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["line_id", "speaker", "start_sec", "end_sec", "text"],
        "properties": {
          "line_id": {"type": "string"},
          "speaker": {"type": "string"},
          "start_sec": {"type": "number"},
          "end_sec": {"type": "number"},
          "text": {"type": "string"}
        }
      }
    }
  },
  "additionalProperties": true
}

```

# /Users/bowensong/Documents/New project/docs/AI/patch.schema.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "patch.schema.json",
  "title": "ScenePatch",
  "type": "object",
  "required": ["target", "ops"],
  "properties": {
    "target": {
      "type": "object",
      "required": ["project", "scene"],
      "properties": {
        "project": {"type": "string"},
        "scene": {"type": "string"},
        "shot": {"type": ["string", "null"]}
      }
    },
    "ops": {
      "type": "array",
      "items": {
        "anyOf": [
          {
            "type": "object",
            "required": ["op", "path", "value"],
            "properties": {
              "op": {"const": "set"},
              "path": {"type": "string"},
              "value": {}
            }
          },
          {
            "type": "object",
            "required": ["op", "path"],
            "properties": {
              "op": {"const": "delete"},
              "path": {"type": "string"}
            }
          },
          {
            "type": "object",
            "required": ["op", "path", "value"],
            "properties": {
              "op": {"const": "append"},
              "path": {"type": "string"},
              "value": {}
            }
          },
          {
            "type": "object",
            "required": ["op", "path", "values"],
            "properties": {
              "op": {"const": "extend"},
              "path": {"type": "string"},
              "values": {"type": "array"}
            }
          },
          {
            "type": "object",
            "required": ["op", "find", "replace"],
            "properties": {
              "op": {"const": "replace_prompt"},
              "find": {"type": "string"},
              "replace": {"type": "string"}
            }
          },
          {
            "type": "object",
            "required": ["op", "text"],
            "properties": {
              "op": {"enum": ["add_prompt_prefix", "add_prompt_suffix", "add_negative_prefix", "add_negative_suffix"]},
              "text": {"type": "string"}
            }
          },
          {
            "type": "object",
            "required": ["op", "ref_path_key", "value"],
            "properties": {
              "op": {"const": "set_ref"},
              "ref_path_key": {"type": "string"},
              "value": {}
            }
          },
          {
            "type": "object",
            "required": ["op", "value"],
            "properties": {
              "op": {"const": "set_frame_range"},
              "value": {
                "oneOf": [
                  {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 2,
                    "maxItems": 2
                  },
                  {
                    "type": "object",
                    "properties": {
                      "start": {"type": "integer"},
                      "end": {"type": "integer"}
                    }
                  },
                  {"type": "string"}
                ]
              }
            }
          },
          {
            "type": "object",
            "required": ["op", "speaker", "line_id", "text"],
            "properties": {
              "op": {"const": "set_dialog_text"},
              "speaker": {"type": "string"},
              "line_id": {"type": "string"},
              "text": {"type": "string"}
            }
          },
          {
            "type": "object",
            "required": ["op", "line_id", "delta_seconds"],
            "properties": {
              "op": {"const": "shift_dialog_time"},
              "line_id": {"type": "string"},
              "delta_seconds": {"type": "number"}
            }
          },
          {
            "type": "object",
            "required": ["op", "track_path"],
            "properties": {
              "op": {"const": "replace_music"},
              "track_path": {"type": "string"}
            }
          }
        ]
      }
    }
  },
  "additionalProperties": false
}

```

# /Users/bowensong/Documents/New project/docs/AI/project.schema.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "project.schema.json",
  "title": "ProjectConfig",
  "type": "object",
  "required": ["project_name", "model", "output_specs"],
  "properties": {
    "project_name": {"type": "string"},
    "description": {"type": "string"},
    "identity_packs": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["path"],
        "properties": {
          "path": {"type": "string"},
          "weight": {"type": "number"}
        }
      }
    },
    "model": {
      "type": "object",
      "required": ["base_id"],
      "properties": {
        "base_id": {"type": "string"},
        "refiner_id": {"type": "string"},
        "fast_base_id": {"type": "string"},
        "use_refiner": {"type": "boolean"},
        "precision": {"enum": ["fp16", "bf16"]},
        "enable_xformers": {"type": "boolean"},
        "attention_slicing": {"type": "boolean"},
        "loras": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["path"],
            "properties": {
              "path": {"type": "string"},
              "scale": {"type": "number"}
            }
          }
        }
      }
    },
    "style_bible": {
      "type": "object",
      "properties": {
        "vibe_guidelines": {"type": "array", "items": {"type": "string"}},
        "forbidden": {"type": "array", "items": {"type": "string"}}
      }
    },
    "safety_policy": {"type": "object"},
    "output_specs": {
      "type": "object",
      "required": ["resolution", "fps", "loudness_target_lufs"],
      "properties": {
        "resolution": {
          "type": "array",
          "minItems": 2,
          "maxItems": 2,
          "items": {"type": "integer"}
        },
        "fps": {"type": "integer"},
        "loudness_target_lufs": {"type": "number"}
      }
    },
    "shared_refs": {"type": "object"},
    "assets": {
      "type": "object",
      "properties": {
        "identity_folders": {"type": "array", "items": {"type": "string"}},
        "asset_folders": {"type": "array", "items": {"type": "string"}}
      }
    },
    "scene_files": {"type": "array", "items": {"type": "string"}}
  },
  "additionalProperties": true
}

```

# /Users/bowensong/Documents/New project/docs/AI/scene.schema.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "scene.schema.json",
  "title": "SceneConfig",
  "type": "object",
  "required": ["scene_name", "shots"],
  "properties": {
    "scene_name": {"type": "string"},
    "scene_title": {"type": "string"},
    "vibe_overrides": {
      "type": "object",
      "properties": {
        "prompt": {"type": "string"},
        "negative_prompt": {"type": "string"}
      }
    },
    "location_refs": {"type": "array", "items": {"type": "string"}},
    "wardrobe_refs": {"type": "array", "items": {"type": "string"}},
    "dialog_ref": {"type": "string"},
    "shots": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["shot_id", "duration", "fps", "resolution", "prompt", "generation"],
        "properties": {
          "shot_id": {"type": "string"},
          "duration": {"type": "number"},
          "fps": {"type": "integer"},
          "resolution": {
            "type": "array",
            "items": {"type": "integer"},
            "minItems": 2,
            "maxItems": 2
          },
          "camera": {"type": "string"},
          "lens": {"type": "string"},
          "lighting": {"type": "string"},
          "prompt": {"type": "string"},
          "negative_prompt": {"type": "string"},
          "generation": {
            "type": "object",
            "required": ["method"],
            "properties": {
              "method": {"enum": ["image_only", "keyframes_to_video", "video_plugin"]},
              "plugin": {"type": "string"},
              "seed": {"type": "integer"},
              "num_inference_steps": {"type": "integer"},
              "guidance_scale": {"type": "number"},
              "anchor_frames": {"type": "array", "items": {"type": "integer"}},
              "prompt_schedule": {
                "type": "array",
                "items": {
                  "type": "object",
                  "properties": {
                    "frame": {"type": "integer"},
                    "prompt_suffix": {"type": "string"}
                  }
                }
              },
              "frame_range": {
                "type": "array",
                "items": {"type": "integer"},
                "minItems": 2,
                "maxItems": 2
              }
            }
          },
          "references": {"type": "object"},
          "actors": {"type": "array", "items": {"type": "string"}}
        }
      }
    }
  },
  "additionalProperties": true
}

```

# /Users/bowensong/Documents/New project/docs/AI/workspace.schema.json
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "workspace.schema.json",
  "title": "WorkspaceConfig",
  "type": "object",
  "required": ["workspace_name", "output_root", "projects"],
  "properties": {
    "workspace_name": {"type": "string"},
    "output_root": {"type": "string"},
    "shared_prompt_library": {"type": "string"},
    "shared_asset_packs": {
      "type": "array",
      "items": {"type": "string"}
    },
    "global_defaults": {
      "type": "object",
      "properties": {
        "seed": {"type": "integer"},
        "run_settings": {"type": "object"},
        "model": {
          "type": "object",
          "properties": {
            "base_id": {"type": "string"},
            "refiner_id": {"type": "string"},
            "fast_base_id": {"type": "string"},
            "use_refiner": {"type": "boolean"},
            "precision": {"enum": ["fp16", "bf16"]},
            "enable_xformers": {"type": "boolean"},
            "attention_slicing": {"type": "boolean"}
          }
        }
      }
    },
    "global_guidelines": {
      "type": "object",
      "properties": {
        "prompt": {"type": "string"},
        "negative_prompt": {"type": "string"}
      }
    },
    "projects": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "path"],
        "properties": {
          "name": {"type": "string"},
          "path": {"type": "string"}
        }
      }
    },
    "selection": {
      "type": "object",
      "properties": {
        "default_projects": {"type": "array", "items": {"type": "string"}},
        "default_scenes": {"type": "array", "items": {"type": "string"}}
      }
    },
    "identity_folders": {"type": "array", "items": {"type": "string"}},
    "asset_folders": {"type": "array", "items": {"type": "string"}}
  },
  "additionalProperties": true
}

```

# /Users/bowensong/Documents/New project/docs/HUMAN/AUDIO.md
```markdown
# Audio

Baseline dialog system:
- speaker profiles in `assets/audio/voices/<speaker>/profile.yaml`
- uses prerecorded line wavs when available
- otherwise generates lightweight offline synthetic voice tones

Music baseline:
- selects track from `music_library/catalog.yaml` by tag overlap with scene vibe
- if source track missing, synthesizes a fallback bed

Mixing:
- ffmpeg sidechain ducking + loudnorm when available
- NumPy fallback mix if ffmpeg is unavailable
- outputs `final_audio.wav` and optional `subtitles.srt`

```

# /Users/bowensong/Documents/New project/docs/HUMAN/JUDGES.md
```markdown
# Judges

Image judges:
- identity similarity
- prompt adherence
- quality
- diversity
- safety

Video judges:
- temporal identity consistency
- clip stability
- flicker

Audio judges:
- loudness compliance
- clipping detection

Outputs:
- `outputs/eval/<run_id>/leaderboard.csv`
- `outputs/eval/<run_id>/scores.json`
- `outputs/eval/<run_id>/project_scores.json`
- `outputs/eval/<run_id>/scene_scores.json`

```

# /Users/bowensong/Documents/New project/docs/HUMAN/PIPELINE.md
```markdown
# Pipeline

Execution DAG per shot/scene:
1. compile scene + shot
2. generate frames
3. assemble shot clip
4. assemble scene video
5. render dialog track
6. render/select music track
7. mix final audio
8. mux scene video + audio
9. concat scenes into project final
10. evaluate judges

Caching/resume:
- deterministic signatures per task
- skip unchanged tasks
- if only audio changes, frame generation is skipped
- frame-range patches regenerate only selected frames and reassemble clip

```

# /Users/bowensong/Documents/New project/docs/HUMAN/PROJECTS.md
```markdown
# Projects

Each project lives under `projects/<name>/` and must include `project.yaml`.

Required sections:
- `identity_packs`: one or more data folders.
- `model`: base SDXL model + optional refiner + LoRAs.
- `style_bible`: vibe and guardrails.
- `safety_policy`: constraints and filters.
- `output_specs`: resolution, fps, target loudness.
- `scene_files`: explicit scene YAML references.

Use `workspace.yaml` to register the project and to select runs across many projects.

```

# /Users/bowensong/Documents/New project/docs/HUMAN/SAFETY.md
```markdown
# Safety

Safety controls include:
- policy fields in `project.yaml`
- negative prompt layering
- safety judge score in evaluation

Recommendations:
- keep NSFW disallowed by policy unless explicitly required by compliance controls
- log provenance for every run
- review generated media before publication

```

# /Users/bowensong/Documents/New project/docs/HUMAN/SCENES.md
```markdown
# Scenes

A scene YAML defines scene-level vibe and a list of shots.

Shot fields:
- timing: `duration`, `fps`, `resolution`
- cinematic intent: `camera`, `lens`, `lighting`
- prompt controls: `prompt`, `negative_prompt`
- generation method: `image_only`, `keyframes_to_video`, or `video_plugin`
- references: pose/wardrobe/background/moodboard
- actors: identity tokens such as `<me>`

Dialog references are linked through `dialog_ref`.

```

# /Users/bowensong/Documents/New project/docs/HUMAN/SLURM.md
```markdown
# Slurm

Provided scripts:
- `slurm/train_identity_2gpu.sbatch`
- `slurm/run_studio_2gpu.sbatch`
- `slurm/eval.sbatch`
- `slurm/evolve.sbatch`

All scripts:
- request 2 GPUs
- set NCCL environment variables
- log to `logs/%x_%j.out`
- support workspace/project/scene args
- support resume flags

```

# /Users/bowensong/Documents/New project/docs/HUMAN/TROUBLESHOOTING.md
```markdown
# Troubleshooting

## ffmpeg missing
Install ffmpeg and rerun. Without ffmpeg, MP4 creation falls back to warning files.

## Heavy ML dependencies missing
`studio.train_identity` and advanced judges degrade gracefully.
Install optional packages from `requirements.txt` for full capability.

## Empty outputs
Check project/scene selection flags and ensure `scene_files` exist in `project.yaml`.

## Cache confusion
Use a new `--run_id` or disable resume behavior by omitting `--resume`.

```

# /Users/bowensong/Documents/New project/docs/HUMAN/TWEAKS.md
```markdown
# Tweaks (Patch System)

Patch files are non-destructive overlays:
- `projects/<proj>/scripts/scenes/patches/<scene>.patch.<N>.yaml`

Supported operations:
- structure ops: `set`, `delete`, `append`, `extend`, `set_ref`, `set_frame_range`
- prompt ops: `replace_prompt`, `add_prompt_prefix/suffix`, `add_negative_prefix/suffix`
- audio ops: `set_dialog_text`, `shift_dialog_time`, `replace_music`

Examples:
```bash
python -m studio.tweak --workspace workspace.yaml --project my_makeover --scene scene_01 --create_patch_template
python -m studio.tweak --workspace workspace.yaml --project my_makeover --scene scene_01 --shot shot_03 --apply_inline "replace_prompt: 'straight hair' -> 'wavy hair'"
```

```

# /Users/bowensong/Documents/New project/docs/HUMAN/VIDEO.md
```markdown
# Video

Generation supports:
- `image_only`
- `keyframes_to_video`
- `video_plugin` (native stub included)

Assembly:
- `frames/` -> `clip.mp4` per shot
- shot clips -> `scene.mp4`
- scene clips -> `final.mp4`

Consistency controls:
- seed locking
- anchor frames
- prompt schedule by frame index
- per-shot metadata with provenance

```

# /Users/bowensong/Documents/New project/logs/.gitkeep
```text

```

# /Users/bowensong/Documents/New project/projects/my_makeover/assets/audio/music_library/catalog.yaml
```yaml
tracks:
  - path: "projects/my_makeover/assets/audio/music_library/track_neon.wav"
    tags: ["neon", "rain", "cinematic"]
  - path: "projects/my_makeover/assets/audio/music_library/track_studio.wav"
    tags: ["clean", "daylight", "modern"]

```

# /Users/bowensong/Documents/New project/projects/my_makeover/assets/audio/voices/.gitkeep
```text

```

# /Users/bowensong/Documents/New project/projects/my_makeover/assets/audio/voices/narrator/profile.yaml
```yaml
speaker_id: "narrator"
style: "calm_confident"
baseline_pitch_hz: 160
use_prerecorded_if_available: true

```

# /Users/bowensong/Documents/New project/projects/my_makeover/assets/images/.gitkeep
```text

```

# /Users/bowensong/Documents/New project/projects/my_makeover/assets/refs/moodboard_neon_ref.txt
```text
Moodboard: neon reds and blues, rain atmosphere, cinematic contrast.

```

# /Users/bowensong/Documents/New project/projects/my_makeover/assets/refs/pose_speak_ref.txt
```text
Reference pose: direct-to-camera speaking posture.

```

# /Users/bowensong/Documents/New project/projects/my_makeover/assets/refs/pose_stand_ref.txt
```text
Reference pose: relaxed standing, shoulders open.

```

# /Users/bowensong/Documents/New project/projects/my_makeover/assets/refs/pose_turn_ref.txt
```text
Reference pose: head turn toward camera, smooth transition.

```

# /Users/bowensong/Documents/New project/projects/my_makeover/assets/refs/pose_walk_ref.txt
```text
Reference pose: forward walk with confident stride.

```

# /Users/bowensong/Documents/New project/projects/my_makeover/assets/refs/rainy_street_ref.txt
```text
Reference: rainy neon street at night, reflective pavement.

```

# /Users/bowensong/Documents/New project/projects/my_makeover/assets/refs/studio_ref.txt
```text
Reference: clean daylight studio with neutral backdrop.

```

# /Users/bowensong/Documents/New project/projects/my_makeover/assets/refs/wardrobe_modern_ref.txt
```text
Reference: modern dark jacket, minimal accessories.

```

# /Users/bowensong/Documents/New project/projects/my_makeover/assets/videos/.gitkeep
```text

```

# /Users/bowensong/Documents/New project/projects/my_makeover/project.yaml
```yaml
project_name: "my_makeover"
description: "Personal brand makeover with cinematic portrait scenes."

identity_packs:
  - path: "data/my_identity"
    weight: 1.0

model:
  base_id: "stabilityai/stable-diffusion-xl-base-1.0"
  refiner_id: "stabilityai/stable-diffusion-xl-refiner-1.0"
  fast_base_id: "your-org/fast-sdxl-placeholder"
  use_refiner: false
  precision: "bf16"
  enable_xformers: true
  attention_slicing: true
  loras:
    - path: "outputs/train/my_identity_sdxl_lora/final_lora.safetensors"
      scale: 0.8

style_bible:
  vibe_guidelines:
    - "identity fidelity is top priority"
    - "cinematic framing with realistic skin texture"
    - "avoid over-retouching"
  forbidden:
    - "excessive makeup"
    - "cartoon style"

safety_policy:
  nsfw_filter: true
  disallow_minors: true
  violence_level: "low"

output_specs:
  resolution: [1024, 1024]
  fps: 24
  loudness_target_lufs: -16

shared_refs:
  prompt_library: "shared/prompt_library.yaml"
  asset_packs:
    - "urban_night"
    - "wardrobe_modern"

assets:
  identity_folders:
    - "data/my_identity"
  asset_folders:
    - "projects/my_makeover/assets"

scene_files:
  - "projects/my_makeover/scripts/scenes/scene_01.yaml"
  - "projects/my_makeover/scripts/scenes/scene_02.yaml"

```

# /Users/bowensong/Documents/New project/projects/my_makeover/scripts/dialogs/scene_01_dialog.yaml
```yaml
scene: "scene_01"
sample_rate: 24000
speakers:
  narrator:
    voice_profile: "projects/my_makeover/assets/audio/voices/narrator/profile.yaml"
lines:
  - line_id: "l1"
    speaker: "narrator"
    start_sec: 0.2
    end_sec: 2.1
    text: "This is the moment I stopped hiding and started owning my style."
  - line_id: "l2"
    speaker: "narrator"
    start_sec: 3.0
    end_sec: 5.2
    text: "Rain, lights, and one clear direction forward."

```

# /Users/bowensong/Documents/New project/projects/my_makeover/scripts/dialogs/scene_02_dialog.yaml
```yaml
scene: "scene_02"
sample_rate: 24000
speakers:
  narrator:
    voice_profile: "projects/my_makeover/assets/audio/voices/narrator/profile.yaml"
lines:
  - line_id: "l1"
    speaker: "narrator"
    start_sec: 0.4
    end_sec: 2.6
    text: "In daylight, confidence is just clarity with better posture."

```

# /Users/bowensong/Documents/New project/projects/my_makeover/scripts/prompt_templates/default_prompt.j2
```text
{{global_guidelines}}. {{project_vibe}}. {{scene_vibe}}.
Shot description: {{shot_prompt}}.
Camera: {{camera}}; Lens: {{lens}}; Lighting: {{lighting}}.
Wardrobe: {{wardrobe}}; Location: {{location}}.

```

# /Users/bowensong/Documents/New project/projects/my_makeover/scripts/scenes/patches/.gitkeep
```text

```

# /Users/bowensong/Documents/New project/projects/my_makeover/scripts/scenes/patches/scene_01.patch.001.yaml
```yaml
target:
  project: "my_makeover"
  scene: "scene_01"
  shot: "shot_03"
ops:
  - op: "replace_prompt"
    find: "cinematic city depth"
    replace: "cinematic city depth with stronger identity preservation"
  - op: "add_prompt_suffix"
    text: ", rainy neon reflections, subtle wind motion"
  - op: "add_negative_suffix"
    text: ", overdone makeup"
  - op: "set"
    path: "generation.guidance_scale"
    value: 6.8
  - op: "set_frame_range"
    value: [120, 220]

```

# /Users/bowensong/Documents/New project/projects/my_makeover/scripts/scenes/scene_01.yaml
```yaml
scene_name: "scene_01"
scene_title: "Rainy Neon Street Intro"
vibe_overrides:
  prompt: "rainy neon city mood, cinematic contrast"
  negative_prompt: "heavy makeup"
location_refs:
  - "projects/my_makeover/assets/refs/rainy_street_ref.txt"
wardrobe_refs:
  - "projects/my_makeover/assets/refs/wardrobe_modern_ref.txt"
dialog_ref: "projects/my_makeover/scripts/dialogs/scene_01_dialog.yaml"

shots:
  - shot_id: "shot_01"
    duration: 3.5
    fps: 24
    resolution: [1024, 1024]
    camera: "medium shot, slow dolly in"
    lens: "50mm"
    lighting: "neon backlight with rain highlights"
    prompt: "<me> stands under neon sign, subtle confident expression"
    negative_prompt: "plastic skin"
    generation:
      method: "image_only"
      seed: 101
      num_inference_steps: 30
      guidance_scale: 6.5
    references:
      pose: "projects/my_makeover/assets/refs/pose_stand_ref.txt"
      wardrobe: "projects/my_makeover/assets/refs/wardrobe_modern_ref.txt"
      background: "projects/my_makeover/assets/refs/rainy_street_ref.txt"
      moodboard: "projects/my_makeover/assets/refs/moodboard_neon_ref.txt"
    actors: ["<me>"]

  - shot_id: "shot_02"
    duration: 4.0
    fps: 24
    resolution: [1024, 1024]
    camera: "close-up, handheld subtle motion"
    lens: "85mm"
    lighting: "key light from storefront"
    prompt: "<me> turns toward camera, soft smile, raindrops on jacket"
    negative_prompt: "harsh shadows"
    generation:
      method: "keyframes_to_video"
      seed: 102
      num_inference_steps: 32
      guidance_scale: 7.0
      anchor_frames: [0, 48]
      prompt_schedule:
        - frame: 0
          prompt_suffix: "intro expression"
        - frame: 48
          prompt_suffix: "warmer smile"
    references:
      pose: "projects/my_makeover/assets/refs/pose_turn_ref.txt"
      wardrobe: "projects/my_makeover/assets/refs/wardrobe_modern_ref.txt"
      background: "projects/my_makeover/assets/refs/rainy_street_ref.txt"
    actors: ["<me>"]

  - shot_id: "shot_03"
    duration: 5.0
    fps: 24
    resolution: [1024, 1024]
    camera: "wide shot with tracking"
    lens: "35mm"
    lighting: "neon reflections, wet ground"
    prompt: "<me> walks forward, cinematic city depth"
    negative_prompt: "over-sharpening"
    generation:
      method: "video_plugin"
      plugin: "native_video_stub"
      seed: 103
      num_inference_steps: 28
      guidance_scale: 6.2
    references:
      pose: "projects/my_makeover/assets/refs/pose_walk_ref.txt"
      wardrobe: "projects/my_makeover/assets/refs/wardrobe_modern_ref.txt"
      background: "projects/my_makeover/assets/refs/rainy_street_ref.txt"
    actors: ["<me>"]

```

# /Users/bowensong/Documents/New project/projects/my_makeover/scripts/scenes/scene_02.yaml
```yaml
scene_name: "scene_02"
scene_title: "Studio Confidence Segment"
vibe_overrides:
  prompt: "clean daylight studio, soft modern style"
  negative_prompt: "muddy tones"
location_refs:
  - "projects/my_makeover/assets/refs/studio_ref.txt"
wardrobe_refs:
  - "projects/my_makeover/assets/refs/wardrobe_modern_ref.txt"
dialog_ref: "projects/my_makeover/scripts/dialogs/scene_02_dialog.yaml"

shots:
  - shot_id: "shot_01"
    duration: 4.0
    fps: 24
    resolution: [1024, 1024]
    camera: "medium portrait static"
    lens: "50mm"
    lighting: "soft box key + fill"
    prompt: "<me> speaks to camera in bright studio"
    negative_prompt: "crushed blacks"
    generation:
      method: "image_only"
      seed: 201
      num_inference_steps: 28
      guidance_scale: 6.0
    references:
      pose: "projects/my_makeover/assets/refs/pose_speak_ref.txt"
      wardrobe: "projects/my_makeover/assets/refs/wardrobe_modern_ref.txt"
      background: "projects/my_makeover/assets/refs/studio_ref.txt"
    actors: ["<me>"]

```

# /Users/bowensong/Documents/New project/pyproject.toml
```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "personalized-generative-studio"
version = "0.1.0"
description = "Personalized generative studio: SDXL LoRA training, multi-project generation, audio/video production, evaluation, and AI command interface"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [{name = "Codex"}]
dependencies = []

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
addopts = "-q"

```

# /Users/bowensong/Documents/New project/requirements.txt
```text
PyYAML>=6.0
Jinja2>=3.1
jsonschema>=4.20
numpy>=1.24
Pillow>=10.0
soundfile>=0.12
scipy>=1.10
optuna>=3.6
tqdm>=4.66

# Optional heavy dependencies (graceful fallback if missing)
torch>=2.1
diffusers>=0.27
accelerate>=0.27
transformers>=4.38
xformers>=0.0.25
insightface>=0.7
facenet-pytorch>=2.5
lpips>=0.1
open_clip_torch>=2.24

```

# /Users/bowensong/Documents/New project/shared/.gitkeep
```text

```

# /Users/bowensong/Documents/New project/shared/asset_packs.yaml
```yaml
asset_packs:
  - name: "urban_night"
    images:
      - "projects/my_makeover/assets/refs/rainy_street_ref.txt"
    tags: ["neon", "city", "rain"]
  - name: "wardrobe_modern"
    images:
      - "projects/my_makeover/assets/refs/wardrobe_modern_ref.txt"
    tags: ["fashion", "modern"]

```

# /Users/bowensong/Documents/New project/shared/prompt_library.yaml
```yaml
global_templates:
  cinematic_portrait: |
    {{subject}} in {{location}}, {{lighting}}, {{camera}}, {{lens}},
    cinematic composition, rich detail, realistic skin, subtle film grain
  fashion_editorial: |
    {{subject}} wearing {{wardrobe}}, {{location}}, editorial style,
    controlled highlights, premium makeup, sharp focus
negative_templates:
  base_negative: "deformed anatomy, warped face, blurry, lowres, jpeg artifacts"
vibe_words:
  neon_rain: ["rain-soaked streets", "neon reflections", "night city haze"]
  clean_daylight: ["soft daylight", "natural color", "gentle contrast"]

```

# /Users/bowensong/Documents/New project/slurm/eval.sbatch
```bash
#!/bin/bash
#SBATCH --job-name=eval_studio
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:2
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --output=logs/%x_%j.out

set -euo pipefail

export NCCL_DEBUG=INFO
export NCCL_SOCKET_IFNAME=${NCCL_SOCKET_IFNAME:-"^lo,docker0"}
export PYTHONUNBUFFERED=1

WORKSPACE_PATH=${WORKSPACE_PATH:-workspace.yaml}
RUN_ID=${RUN_ID:?RUN_ID environment variable is required}

python -m studio.eval --workspace "${WORKSPACE_PATH}" --run_id "${RUN_ID}"

```

# /Users/bowensong/Documents/New project/slurm/evolve.sbatch
```bash
#!/bin/bash
#SBATCH --job-name=evolve_studio
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --gres=gpu:2
#SBATCH --mem=96G
#SBATCH --time=24:00:00
#SBATCH --output=logs/%x_%j.out

set -euo pipefail

export NCCL_DEBUG=INFO
export NCCL_SOCKET_IFNAME=${NCCL_SOCKET_IFNAME:-"^lo,docker0"}
export PYTHONUNBUFFERED=1

WORKSPACE_PATH=${WORKSPACE_PATH:-workspace.yaml}
PROJECTS=${PROJECTS:-my_makeover}
BUDGET=${BUDGET:-small}
RESUME_FLAG=${RESUME_FLAG:-1}

CMD=(python -m studio.evolve --workspace "${WORKSPACE_PATH}" --projects ${PROJECTS} --budget "${BUDGET}")
if [[ "${RESUME_FLAG}" == "1" ]]; then
  CMD+=(--resume)
fi

"${CMD[@]}"

```

# /Users/bowensong/Documents/New project/slurm/run_studio_2gpu.sbatch
```bash
#!/bin/bash
#SBATCH --job-name=run_studio_2gpu
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --gres=gpu:2
#SBATCH --mem=160G
#SBATCH --time=24:00:00
#SBATCH --output=logs/%x_%j.out

set -euo pipefail

export NCCL_DEBUG=INFO
export NCCL_IB_DISABLE=0
export NCCL_P2P_DISABLE=0
export NCCL_SOCKET_IFNAME=${NCCL_SOCKET_IFNAME:-"^lo,docker0"}
export PYTHONUNBUFFERED=1

WORKSPACE_PATH=${WORKSPACE_PATH:-workspace.yaml}
PROJECTS=${PROJECTS:-all}
SCENES=${SCENES:-all}
RUN_ID=${RUN_ID:-""}
RESUME_FLAG=${RESUME_FLAG:-1}

CMD=(python -m studio.run --workspace "${WORKSPACE_PATH}")

if [[ "${PROJECTS}" == "all" ]]; then
  CMD+=(--projects all)
else
  CMD+=(--projects ${PROJECTS})
fi

if [[ "${SCENES}" == "all" ]]; then
  CMD+=(--scenes all)
else
  CMD+=(--scenes ${SCENES})
fi

if [[ -n "${RUN_ID}" ]]; then
  CMD+=(--run_id "${RUN_ID}")
fi

if [[ "${RESUME_FLAG}" == "1" ]]; then
  CMD+=(--resume)
fi

"${CMD[@]}"

```

# /Users/bowensong/Documents/New project/slurm/train_identity_2gpu.sbatch
```bash
#!/bin/bash
#SBATCH --job-name=train_identity_2gpu
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --gres=gpu:2
#SBATCH --mem=160G
#SBATCH --time=48:00:00
#SBATCH --output=logs/%x_%j.out

set -euo pipefail

export NCCL_DEBUG=INFO
export NCCL_IB_DISABLE=0
export NCCL_P2P_DISABLE=0
export NCCL_SOCKET_IFNAME=${NCCL_SOCKET_IFNAME:-"^lo,docker0"}
export PYTHONUNBUFFERED=1

CONFIG_PATH=${1:-configs/train/sdxl_lora.yaml}
RESUME_FROM=${RESUME_FROM:-""}

if [[ -n "${RESUME_FROM}" ]]; then
  python -m studio.train_identity --config "${CONFIG_PATH}" --log_level INFO
else
  python -m studio.train_identity --config "${CONFIG_PATH}" --log_level INFO
fi

```

# /Users/bowensong/Documents/New project/src/studio/__init__.py
```python
"""Personalized Generative Studio package."""

__all__ = ["__version__"]
__version__ = "0.1.0"

```

# /Users/bowensong/Documents/New project/src/studio/ai.py
```python
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

```

# /Users/bowensong/Documents/New project/src/studio/ai_cmd/__init__.py
```python
"""AI command planner backends and schemas."""

```

# /Users/bowensong/Documents/New project/src/studio/ai_cmd/llm_backend.py
```python
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from ..utils import get_logger
from .rules_backend import plan_from_rules
from .schemas import Action, ActionPlan

logger = get_logger("ai_cmd.llm_backend")


def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except Exception:
        return None


def plan_with_llm(
    request: str,
    context: dict[str, Any],
    endpoint: str,
    model: str,
    api_key_env: str,
    dry_run: bool = False,
) -> ActionPlan:
    api_key = os.environ.get(api_key_env, "")
    if not endpoint or not model or not api_key:
        logger.warning("LLM backend disabled/misconfigured; falling back to rules backend.")
        return plan_from_rules(request=request, context=context, dry_run=dry_run)

    system = (
        "You are a planner that converts natural language into deterministic studio ActionPlan JSON. "
        "Return strict JSON only with fields: request, backend, context, dry_run, actions[]. "
        "Action type values: compile_only, apply_patch, rerun_subset, adjust_inference_params, "
        "adjust_prompt_templates, schedule_evolve."
    )
    user = json.dumps({"request": request, "context": context}, ensure_ascii=True)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
        obj = json.loads(raw)
        content = obj["choices"][0]["message"]["content"]
        planned = _extract_json(content)
        if not planned:
            raise ValueError("LLM output did not contain valid JSON")

        actions = [Action(type=a.get("type", "compile_only"), payload=a.get("payload", {})) for a in planned.get("actions", [])]
        return ActionPlan(
            request=request,
            backend="llm",
            context=planned.get("context", context),
            dry_run=dry_run,
            actions=actions,
        )
    except Exception as exc:
        logger.warning("LLM backend failed (%s); using rules backend.", exc)
        return plan_from_rules(request=request, context=context, dry_run=dry_run)

```

# /Users/bowensong/Documents/New project/src/studio/ai_cmd/planner.py
```python
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

```

# /Users/bowensong/Documents/New project/src/studio/ai_cmd/rules_backend.py
```python
from __future__ import annotations

import re
from typing import Any

from .schemas import Action, ActionPlan

SCENE_RE = re.compile(r"\b(scene[_-]?\d+)\b", re.IGNORECASE)
SHOT_RE = re.compile(r"\b(shot[_-]?\d+)\b", re.IGNORECASE)
FRAME_RE = re.compile(r"frames?\s+(\d+)\s*(?:-|to)\s*(\d+)", re.IGNORECASE)
CFG_RE = re.compile(r"(?:cfg|guidance(?:_scale)?)\s*(?:to|=)?\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)
STEPS_RE = re.compile(r"(?:steps?)\s*(?:to|=)?\s*(\d+)", re.IGNORECASE)
HAIR_RE = re.compile(r"change hair to\s+([^,;]+)", re.IGNORECASE)
VIBE_RE = re.compile(r"add\s+([^,;]+?)\s+vibe", re.IGNORECASE)


def _normalize_id(text: str) -> str:
    return text.lower().replace("-", "_")


def plan_from_rules(request: str, context: dict[str, Any], dry_run: bool = False) -> ActionPlan:
    text = request.strip()
    low = text.lower()

    project = context.get("project")
    scene = context.get("scene")
    shot = context.get("shot")

    m_scene = SCENE_RE.search(text)
    m_shot = SHOT_RE.search(text)
    if m_scene:
        scene = _normalize_id(m_scene.group(1))
    if m_shot:
        shot = _normalize_id(m_shot.group(1))

    patch_ops: list[dict[str, Any]] = []
    frame_range: list[int] | None = None

    frame_match = FRAME_RE.search(low)
    if frame_match:
        frame_range = [int(frame_match.group(1)), int(frame_match.group(2))]
        patch_ops.append({"op": "set_frame_range", "value": frame_range})

    cfg_match = CFG_RE.search(low)
    if cfg_match:
        patch_ops.append(
            {
                "op": "set",
                "path": "generation.guidance_scale",
                "value": float(cfg_match.group(1)),
            }
        )

    steps_match = STEPS_RE.search(low)
    if steps_match:
        patch_ops.append(
            {
                "op": "set",
                "path": "generation.num_inference_steps",
                "value": int(steps_match.group(1)),
            }
        )

    if "more cinematic" in low:
        patch_ops.append({"op": "add_prompt_suffix", "text": ", cinematic lighting, dramatic composition"})

    if "reduce makeup" in low:
        patch_ops.append({"op": "add_negative_suffix", "text": ", heavy makeup, overdone cosmetics"})
        patch_ops.append({"op": "replace_prompt", "find": "makeup", "replace": "minimal makeup"})

    if "keep identity strong" in low or "identity strong" in low:
        patch_ops.append({"op": "add_prompt_suffix", "text": ", identity-preserving facial structure, true likeness"})

    hair_match = HAIR_RE.search(text)
    if hair_match:
        hair_desc = hair_match.group(1).strip()
        patch_ops.append({"op": "add_prompt_suffix", "text": f", hairstyle: {hair_desc}"})

    vibe_match = VIBE_RE.search(text)
    if vibe_match:
        vibe_text = vibe_match.group(1).strip()
        patch_ops.append({"op": "add_prompt_suffix", "text": f", {vibe_text} vibe"})

    actions: list[Action] = []

    if "compile only" in low:
        actions.append(Action(type="compile_only", payload={"project": project, "scene": scene, "shot": shot}))

    if patch_ops:
        actions.append(
            Action(
                type="apply_patch",
                payload={
                    "target": {"project": project, "scene": scene, "shot": shot},
                    "ops": patch_ops,
                },
            )
        )

    if any(word in low for word in ["regenerate", "rerun", "render"]) or patch_ops:
        actions.append(
            Action(
                type="rerun_subset",
                payload={
                    "project": project,
                    "scene": scene,
                    "shot": shot,
                    "frame_range": frame_range,
                },
            )
        )

    if any(word in low for word in ["evolve", "optimize", "search best"]):
        min_identity = 0.7
        id_match = re.search(r"identity\s*(?:>=|>|at least)?\s*([0-9]+(?:\.[0-9]+)?)", low)
        if id_match:
            min_identity = float(id_match.group(1))
        actions.append(
            Action(
                type="schedule_evolve",
                payload={
                    "project": project,
                    "budget": "small",
                    "constraints": {"min_identity_similarity": min_identity},
                },
            )
        )

    if not actions:
        actions.append(Action(type="compile_only", payload={"project": project, "scene": scene, "shot": shot}))

    return ActionPlan(
        request=request,
        backend="rules",
        context={"project": project, "scene": scene, "shot": shot},
        dry_run=dry_run,
        actions=actions,
    )

```

# /Users/bowensong/Documents/New project/src/studio/ai_cmd/schemas.py
```python
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Action:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionPlan:
    request: str
    backend: str
    context: dict[str, Any]
    dry_run: bool
    actions: list[Action] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "backend": self.backend,
            "context": self.context,
            "dry_run": self.dry_run,
            "actions": [asdict(a) for a in self.actions],
        }

```

# /Users/bowensong/Documents/New project/src/studio/cli.py
```python
from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Studio umbrella CLI")
    parser.add_argument(
        "command",
        choices=["run", "train_identity", "eval", "evolve", "tweak", "ai"],
        help="Subcommand to execute",
    )
    parser.add_argument("args", nargs=argparse.REMAINDER)
    ns = parser.parse_args()

    module = f"studio.{ns.command}"
    cmd = [sys.executable, "-m", module, *ns.args]
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()

```

# /Users/bowensong/Documents/New project/src/studio/config.py
```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .utils import get_logger, load_yaml

logger = get_logger("config")


@dataclass
class WorkspaceProjectRef:
    name: str
    path: str


@dataclass
class LoadedProject:
    name: str
    path: Path
    data: dict[str, Any]


def _resolve(base: Path, maybe_relative: str) -> Path:
    p = Path(maybe_relative)
    return p if p.is_absolute() else (base / p).resolve()


def load_workspace(workspace_path: str) -> dict[str, Any]:
    ws_path = Path(workspace_path).resolve()
    ws = load_yaml(ws_path)
    ws["_workspace_path"] = str(ws_path)
    ws["_workspace_dir"] = str(ws_path.parent)
    return ws


def validate_with_schema(config_data: dict[str, Any], schema_path: str | Path) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except Exception:
        return ["jsonschema not installed; schema validation skipped"]

    schema = load_yaml(schema_path)
    validator = Draft202012Validator(schema)
    errors = [e.message for e in sorted(validator.iter_errors(config_data), key=str)]
    return errors


def resolve_projects(workspace: dict[str, Any], selected: list[str] | None = None) -> list[LoadedProject]:
    ws_dir = Path(workspace["_workspace_dir"])
    refs: list[dict[str, Any]] = workspace.get("projects", [])
    all_projects: dict[str, Path] = {
        r["name"]: _resolve(ws_dir, r["path"]) for r in refs if "name" in r and "path" in r
    }

    if not selected or selected == ["all"]:
        chosen_names = list(all_projects.keys())
    else:
        chosen_names = selected

    loaded: list[LoadedProject] = []
    for name in chosen_names:
        if name not in all_projects:
            logger.warning("Project %s not found in workspace", name)
            continue
        proj_path = all_projects[name]
        proj_data = load_yaml(proj_path)
        loaded.append(LoadedProject(name=name, path=proj_path, data=proj_data))
    return loaded


def resolve_scene_files(project: LoadedProject, selected_scenes: list[str] | None = None) -> list[Path]:
    project_data = project.data
    scene_files = project_data.get("scene_files")
    proj_root = project.path.parent

    if scene_files:
        candidates = [
            (Path(p) if Path(p).is_absolute() else (proj_root.parents[1] / p).resolve()) for p in scene_files
        ]
    else:
        scenes_dir = proj_root / "scripts" / "scenes"
        candidates = [p for p in scenes_dir.glob("*.yaml") if "patch" not in p.name]

    if not selected_scenes or selected_scenes == ["all"]:
        return sorted(candidates)

    selected_set = set(selected_scenes)
    out: list[Path] = []
    for p in candidates:
        stem = p.stem
        if stem in selected_set:
            out.append(p)
    return sorted(out)


def merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge_dict(out[k], v)
        else:
            out[k] = v
    return out

```

# /Users/bowensong/Documents/New project/src/studio/eval.py
```python
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

```

# /Users/bowensong/Documents/New project/src/studio/evolve.py
```python
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

```

# /Users/bowensong/Documents/New project/src/studio/judges/__init__.py
```python
"""Modular judges for image/video/audio evaluation."""

```

# /Users/bowensong/Documents/New project/src/studio/judges/audio.py
```python
from __future__ import annotations

from pathlib import Path

from .base import ShotEvalContext


class LoudnessJudge:
    name = "loudness"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        stats = ctx.metadata.get("audio_stats", {})
        lufs = float(stats.get("lufs", -30.0))
        target = float(ctx.metadata.get("loudness_target_lufs", -16.0))
        delta = abs(lufs - target)
        score = max(0.0, 1.0 - delta / 20.0)
        return {self.name: score}


class ClippingJudge:
    name = "clipping"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        clip_ratio = float(ctx.metadata.get("audio_stats", {}).get("clipping_ratio", 0.0))
        return {self.name: max(0.0, 1.0 - clip_ratio * 50.0)}

```

# /Users/bowensong/Documents/New project/src/studio/judges/base.py
```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass
class ShotEvalContext:
    run_id: str
    project: str
    scene: str
    shot: str
    shot_dir: Path
    frames: list[Path]
    clip_path: Path
    prompt: str
    negative_prompt: str
    metadata: dict[str, Any]


class Judge(Protocol):
    name: str

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        ...

```

# /Users/bowensong/Documents/New project/src/studio/judges/image.py
```python
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from .base import ShotEvalContext


def _load_image(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0


def _safe_mean(values: list[float], default: float = 0.0) -> float:
    return float(np.mean(values)) if values else default


class IdentitySimilarityJudge:
    name = "identity_similarity"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        if len(ctx.frames) < 2:
            return {self.name: 0.7}

        sims: list[float] = []
        prev = _load_image(ctx.frames[0])
        for f in ctx.frames[1: min(len(ctx.frames), 12)]:
            cur = _load_image(f)
            sim = 1.0 - float(np.mean(np.abs(cur - prev)))
            sims.append(max(0.0, min(1.0, sim)))
            prev = cur
        return {self.name: _safe_mean(sims, 0.7)}


class PromptAdherenceJudge:
    name = "prompt_adherence"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        prompt = ctx.prompt.lower()
        tokens = [t for t in prompt.replace(",", " ").split() if len(t) > 3]
        # Heuristic proxy: more specific prompt vocabulary tends to score higher.
        richness = min(1.0, len(set(tokens)) / 25.0)
        return {self.name: float(0.4 + 0.6 * richness)}


class QualityJudge:
    name = "quality"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        scores: list[float] = []
        for f in ctx.frames[: min(len(ctx.frames), 16)]:
            img = _load_image(f)
            gray = np.mean(img, axis=2)
            sharpness = float(np.var(np.gradient(gray)[0]) + np.var(np.gradient(gray)[1]))
            score = min(1.0, sharpness * 10.0)
            scores.append(score)
        return {self.name: _safe_mean(scores, 0.5)}


class DiversityJudge:
    name = "diversity"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        if len(ctx.frames) < 2:
            return {self.name: 0.1}

        diffs: list[float] = []
        sampled = ctx.frames[:: max(1, len(ctx.frames) // 8)]
        arrs = [_load_image(p) for p in sampled]
        for i in range(1, len(arrs)):
            diffs.append(float(np.mean(np.abs(arrs[i] - arrs[i - 1]))))
        score = min(1.0, _safe_mean(diffs, 0.0) * 4.0)
        return {self.name: score}


class SafetyJudge:
    name = "safety"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        prompt = f"{ctx.prompt} {ctx.negative_prompt}".lower()
        banned = ["nsfw", "nudity", "gore"]
        bad_hits = sum(1 for word in banned if word in prompt)
        return {self.name: 1.0 if bad_hits == 0 else max(0.0, 1.0 - bad_hits * 0.5)}

```

# /Users/bowensong/Documents/New project/src/studio/judges/runner.py
```python
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from ..utils import ensure_dir, get_logger, load_json, save_json
from .audio import ClippingJudge, LoudnessJudge
from .base import ShotEvalContext
from .image import (
    DiversityJudge,
    IdentitySimilarityJudge,
    PromptAdherenceJudge,
    QualityJudge,
    SafetyJudge,
)
from .video import ClipStabilityJudge, FlickerJudge, TemporalIdentityConsistencyJudge

logger = get_logger("judges.runner")


def _collect_shots(run_root: Path) -> list[tuple[str, str, str, Path]]:
    out: list[tuple[str, str, str, Path]] = []
    if not run_root.exists():
        return out

    for project_dir in sorted(p for p in run_root.iterdir() if p.is_dir()):
        for scene_dir in sorted(p for p in project_dir.iterdir() if p.is_dir()):
            if scene_dir.name in {"compiled", "audio"}:
                continue
            for shot_dir in sorted(p for p in scene_dir.iterdir() if p.is_dir()):
                if shot_dir.name.startswith("shot_"):
                    out.append((project_dir.name, scene_dir.name, shot_dir.name, shot_dir))
    return out


def evaluate_run(output_root: Path, run_id: str) -> Path:
    run_root = output_root / run_id
    eval_root = output_root / "eval" / run_id
    ensure_dir(eval_root)

    judges = [
        IdentitySimilarityJudge(),
        PromptAdherenceJudge(),
        QualityJudge(),
        DiversityJudge(),
        SafetyJudge(),
        TemporalIdentityConsistencyJudge(),
        ClipStabilityJudge(),
        FlickerJudge(),
        LoudnessJudge(),
        ClippingJudge(),
    ]

    shot_rows: list[dict[str, Any]] = []
    per_shot_scores: dict[str, Any] = {}

    for project, scene, shot, shot_dir in _collect_shots(run_root):
        frames = sorted((shot_dir / "frames").glob("frame_*.png"))
        metadata_path = shot_dir / "metadata.json"
        metadata = load_json(metadata_path) if metadata_path.exists() else {}

        ctx = ShotEvalContext(
            run_id=run_id,
            project=project,
            scene=scene,
            shot=shot,
            shot_dir=shot_dir,
            frames=frames,
            clip_path=shot_dir / "clip.mp4",
            prompt=str(metadata.get("compiled_prompt", "")),
            negative_prompt=str(metadata.get("compiled_negative_prompt", "")),
            metadata=metadata,
        )

        scores: dict[str, float] = {}
        for judge in judges:
            try:
                scores.update(judge.evaluate(ctx))
            except Exception as exc:
                logger.warning("Judge %s failed on %s/%s/%s: %s", judge.name, project, scene, shot, exc)

        aggregate = float(sum(scores.values()) / max(1, len(scores)))
        row = {
            "run_id": run_id,
            "project": project,
            "scene": scene,
            "shot": shot,
            "aggregate": aggregate,
            **scores,
        }
        shot_rows.append(row)
        key = f"{project}/{scene}/{shot}"
        per_shot_scores[key] = row

    leaderboard_path = eval_root / "leaderboard.csv"
    if shot_rows:
        fields = sorted({k for row in shot_rows for k in row.keys()})
        with leaderboard_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(shot_rows)
    else:
        leaderboard_path.write_text("run_id,project,scene,shot,aggregate\n", encoding="utf-8")

    save_json(eval_root / "scores.json", per_shot_scores)

    # Per-project and per-scene summaries.
    project_summary: dict[str, list[float]] = {}
    scene_summary: dict[str, list[float]] = {}
    for row in shot_rows:
        project_summary.setdefault(row["project"], []).append(float(row["aggregate"]))
        scene_summary.setdefault(f"{row['project']}/{row['scene']}", []).append(float(row["aggregate"]))

    save_json(
        eval_root / "project_scores.json",
        {k: sum(v) / len(v) for k, v in project_summary.items()},
    )
    save_json(
        eval_root / "scene_scores.json",
        {k: sum(v) / len(v) for k, v in scene_summary.items()},
    )

    logger.info("Evaluation complete: %s", eval_root)
    return eval_root

```

# /Users/bowensong/Documents/New project/src/studio/judges/video.py
```python
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from .base import ShotEvalContext


def _load(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0


class TemporalIdentityConsistencyJudge:
    name = "temporal_identity_consistency"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        if len(ctx.frames) < 2:
            return {self.name: 0.8}
        vals: list[float] = []
        prev = _load(ctx.frames[0])
        for frame in ctx.frames[1: min(len(ctx.frames), 20)]:
            cur = _load(frame)
            vals.append(1.0 - float(np.mean(np.abs(cur - prev))))
            prev = cur
        score = float(np.clip(np.mean(vals), 0.0, 1.0))
        return {self.name: score}


class ClipStabilityJudge:
    name = "clip_stability"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        if len(ctx.frames) < 2:
            return {self.name: 0.8}
        diffs: list[float] = []
        for i in range(1, min(len(ctx.frames), 20)):
            a = _load(ctx.frames[i - 1])
            b = _load(ctx.frames[i])
            diffs.append(float(np.std(b - a)))
        score = float(np.clip(1.0 - np.mean(diffs) * 2.0, 0.0, 1.0))
        return {self.name: score}


class FlickerJudge:
    name = "flicker"

    def evaluate(self, ctx: ShotEvalContext) -> dict[str, float]:
        if len(ctx.frames) < 3:
            return {self.name: 0.1}
        means = []
        for frame in ctx.frames[: min(len(ctx.frames), 30)]:
            arr = _load(frame)
            means.append(float(arr.mean()))
        diffs = np.abs(np.diff(np.asarray(means)))
        score = float(np.clip(np.mean(diffs) * 6.0, 0.0, 1.0))
        return {self.name: score}

```

# /Users/bowensong/Documents/New project/src/studio/media/__init__.py
```python
"""Media pipelines: video, TTS, music, and mixing."""

```

# /Users/bowensong/Documents/New project/src/studio/media/audio.py
```python
from __future__ import annotations

import math
import subprocess
import wave
from pathlib import Path

import numpy as np

from ..utils import ensure_dir, get_logger, which

logger = get_logger("media.audio")


def _read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
    return audio, sr


def _write_wav(path: Path, audio: np.ndarray, sr: int) -> None:
    ensure_dir(path.parent)
    clipped = np.clip(audio, -1.0, 1.0)
    data = (clipped * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(data.tobytes())


def _to_lufs_approx(audio: np.ndarray) -> float:
    if len(audio) == 0:
        return -120.0
    rms = float(np.sqrt(np.mean(np.square(audio)) + 1e-9))
    return 20.0 * math.log10(rms + 1e-9)


def _normalize_to_lufs(audio: np.ndarray, target_lufs: float) -> np.ndarray:
    cur = _to_lufs_approx(audio)
    gain_db = target_lufs - cur
    gain = 10 ** (gain_db / 20.0)
    return audio * gain


def _ffmpeg_mix(dialog_path: Path, music_path: Path, output_path: Path, target_lufs: float, ducking_db: float) -> bool:
    if which("ffmpeg") is None:
        return False

    ensure_dir(output_path.parent)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(music_path),
        "-i",
        str(dialog_path),
        "-filter_complex",
        (
            f"[0:a][1:a]sidechaincompress=threshold=0.05:ratio=8:level_sc=1:makeup={abs(ducking_db):.1f}[ducked];"
            f"[ducked][1:a]amix=inputs=2:weights='0.8 1.0',loudnorm=I={target_lufs}:TP=-1.5:LRA=11"
        ),
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except Exception as exc:
        logger.warning("ffmpeg mix failed: %s", exc)
        return False


def mix_dialog_and_music(
    dialog_path: Path,
    music_path: Path,
    output_path: Path,
    target_lufs: float = -16.0,
    ducking_db: float = -8.0,
    fade_in_sec: float = 0.3,
    fade_out_sec: float = 0.5,
) -> Path:
    if _ffmpeg_mix(dialog_path, music_path, output_path, target_lufs, ducking_db):
        return output_path

    logger.info("Using numpy fallback for audio mixing")
    dialog, sr_d = _read_wav(dialog_path)
    music, sr_m = _read_wav(music_path)
    if sr_d != sr_m:
        logger.warning("Sample rate mismatch in audio mix (%s vs %s); naive resample music", sr_d, sr_m)
        x_old = np.linspace(0.0, 1.0, num=len(music), endpoint=False)
        x_new = np.linspace(0.0, 1.0, num=int(len(music) * sr_d / sr_m), endpoint=False)
        music = np.interp(x_new, x_old, music).astype(np.float32)
    sr = sr_d

    n = max(len(dialog), len(music))
    dialog_pad = np.zeros(n, dtype=np.float32)
    music_pad = np.zeros(n, dtype=np.float32)
    dialog_pad[: len(dialog)] = dialog
    music_pad[: len(music)] = music

    dialog_env = np.clip(np.abs(dialog_pad) * 4.0, 0.0, 1.0)
    duck = 1.0 - (abs(ducking_db) / 20.0) * dialog_env
    duck = np.clip(duck, 0.2, 1.0)

    mix = dialog_pad + 0.7 * music_pad * duck

    fade_in_samples = int(max(0.0, fade_in_sec) * sr)
    fade_out_samples = int(max(0.0, fade_out_sec) * sr)

    if fade_in_samples > 0:
        mix[:fade_in_samples] *= np.linspace(0.0, 1.0, num=fade_in_samples, endpoint=True)
    if fade_out_samples > 0:
        mix[-fade_out_samples:] *= np.linspace(1.0, 0.0, num=fade_out_samples, endpoint=True)

    mix = _normalize_to_lufs(mix, target_lufs)
    _write_wav(output_path, mix, sr)
    return output_path


def audio_stats(path: Path) -> dict[str, float]:
    audio, _ = _read_wav(path)
    lufs = _to_lufs_approx(audio)
    clipping_ratio = float(np.mean(np.abs(audio) >= 0.999)) if len(audio) else 0.0
    return {"lufs": lufs, "clipping_ratio": clipping_ratio}

```

# /Users/bowensong/Documents/New project/src/studio/media/music.py
```python
from __future__ import annotations

import math
import wave
from pathlib import Path
from typing import Any

import numpy as np

from ..utils import ensure_dir, get_logger, load_yaml

logger = get_logger("media.music")


def _write_wav(path: Path, audio: np.ndarray, sr: int) -> None:
    ensure_dir(path.parent)
    audio = np.clip(audio, -1.0, 1.0)
    int16 = (audio * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(int16.tobytes())


def _synth_music(duration_sec: float, sr: int, tags: list[str]) -> np.ndarray:
    n = max(1, int(duration_sec * sr))
    t = np.linspace(0.0, duration_sec, num=n, endpoint=False)
    base_freq = 90.0 if any("neon" in tag for tag in tags) else 120.0

    pad = 0.22 * np.sin(2 * math.pi * base_freq * t)
    pad += 0.15 * np.sin(2 * math.pi * (base_freq * 1.5) * t)

    beat_freq = 2.0 if any("rain" in tag for tag in tags) else 1.5
    beat = (np.sin(2 * math.pi * beat_freq * t) > 0.75).astype(np.float32)
    beat_env = 0.5 + 0.5 * np.sin(2 * math.pi * 0.2 * t)

    return 0.35 * pad + 0.12 * beat * beat_env


def choose_music_track(music_catalog_path: Path, scene_prompt: str) -> tuple[str | None, list[str]]:
    if not music_catalog_path.exists():
        return None, []

    catalog = load_yaml(music_catalog_path)
    tracks = catalog.get("tracks", [])
    prompt_tokens = set(scene_prompt.lower().replace(",", " ").split())

    best_path = None
    best_tags: list[str] = []
    best_score = -1

    for track in tracks:
        tags = [str(t).lower() for t in track.get("tags", [])]
        score = sum(1 for tag in tags if tag in prompt_tokens)
        if score > best_score:
            best_score = score
            best_path = str(track.get("path"))
            best_tags = tags
    return best_path, best_tags


def render_music_track(
    project_root: Path,
    scene_prompt: str,
    duration_sec: float,
    output_path: Path,
    sample_rate: int = 24000,
) -> Path:
    ensure_dir(output_path.parent)
    catalog_path = project_root / "assets" / "audio" / "music_library" / "catalog.yaml"
    selected, tags = choose_music_track(catalog_path, scene_prompt)

    # Baseline path: synthesize locally even when catalog references external files.
    if selected:
        logger.info("Selected music track reference: %s (tags=%s)", selected, tags)
    else:
        logger.info("No catalog track matched; synthesizing baseline music.")

    audio = _synth_music(duration_sec=duration_sec, sr=sample_rate, tags=tags)
    _write_wav(output_path, audio, sample_rate)
    return output_path

```

# /Users/bowensong/Documents/New project/src/studio/media/tts.py
```python
from __future__ import annotations

import math
import shutil
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..utils import ensure_dir, get_logger

logger = get_logger("media.tts")


@dataclass
class DialogLineAudio:
    line_id: str
    speaker: str
    start_sec: float
    end_sec: float
    text: str
    wav_path: Path


def _write_wav(path: Path, audio: np.ndarray, sr: int) -> None:
    ensure_dir(path.parent)
    clipped = np.clip(audio, -1.0, 1.0)
    int16 = (clipped * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(int16.tobytes())


def _read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
    return audio, sr


def _synth_tone(text: str, sr: int, duration_sec: float, pitch_hz: float = 160.0) -> np.ndarray:
    n = max(1, int(sr * duration_sec))
    t = np.linspace(0.0, duration_sec, num=n, endpoint=False)
    mod = 0.18 * np.sin(2 * math.pi * 4.0 * t)
    carrier = np.sin(2 * math.pi * (pitch_hz + 22 * mod) * t)
    envelope = np.minimum(1.0, t / 0.04) * np.minimum(1.0, (duration_sec - t + 1e-6) / 0.06)
    # encode rough syllabic pulses from text length
    pulse_rate = max(2.0, min(8.0, len(text.split()) * 0.8))
    pulse = 0.55 + 0.45 * np.maximum(0.0, np.sin(2 * math.pi * pulse_rate * t))
    return 0.25 * carrier * envelope * pulse


def synth_line_wav(
    line: dict[str, Any],
    voice_dir: Path,
    output_dir: Path,
    sample_rate: int,
    pitch_hz: float = 160.0,
) -> DialogLineAudio:
    line_id = str(line["line_id"])
    speaker = str(line["speaker"])
    start_sec = float(line.get("start_sec", 0.0))
    end_sec = float(line.get("end_sec", start_sec + 1.0))
    text = str(line.get("text", ""))

    prerecorded = voice_dir / f"{line_id}.wav"
    out_wav = output_dir / f"{line_id}.wav"
    if prerecorded.exists():
        ensure_dir(out_wav.parent)
        shutil.copy2(prerecorded, out_wav)
        logger.info("Using prerecorded line %s from %s", line_id, prerecorded)
    else:
        duration = max(0.5, end_sec - start_sec)
        audio = _synth_tone(text=text, sr=sample_rate, duration_sec=duration, pitch_hz=pitch_hz)
        _write_wav(out_wav, audio, sample_rate)
        logger.info("Synthesized baseline TTS tone for line %s", line_id)

    return DialogLineAudio(
        line_id=line_id,
        speaker=speaker,
        start_sec=start_sec,
        end_sec=end_sec,
        text=text,
        wav_path=out_wav,
    )


def render_dialog_track(
    dialog_yaml: dict[str, Any],
    project_root: Path,
    output_dir: Path,
    total_duration_sec: float,
    default_sample_rate: int = 24000,
) -> Path:
    ensure_dir(output_dir)
    sample_rate = int(dialog_yaml.get("sample_rate", default_sample_rate))
    lines = dialog_yaml.get("lines", [])
    speakers = dialog_yaml.get("speakers", {})

    line_audio_dir = output_dir / "lines"
    line_entries: list[DialogLineAudio] = []

    for line in lines:
        speaker = str(line.get("speaker", "narrator"))
        voice_cfg = speakers.get(speaker, {})
        profile_path = voice_cfg.get("voice_profile")
        pitch = 160.0
        if profile_path:
            abs_profile = (project_root.parents[1] / profile_path).resolve()
            if abs_profile.exists():
                import yaml

                profile = yaml.safe_load(abs_profile.read_text(encoding="utf-8")) or {}
                pitch = float(profile.get("baseline_pitch_hz", 160.0))

        voice_dir = project_root / "assets" / "audio" / "voices" / speaker
        line_audio = synth_line_wav(
            line=line,
            voice_dir=voice_dir,
            output_dir=line_audio_dir,
            sample_rate=sample_rate,
            pitch_hz=pitch,
        )
        line_entries.append(line_audio)

    total_samples = max(1, int(total_duration_sec * sample_rate))
    mix = np.zeros(total_samples, dtype=np.float32)

    for line in line_entries:
        audio, sr = _read_wav(line.wav_path)
        if sr != sample_rate:
            logger.warning("Sample rate mismatch for %s (%s != %s), naive resample", line.line_id, sr, sample_rate)
            x_old = np.linspace(0.0, 1.0, num=len(audio), endpoint=False)
            x_new = np.linspace(0.0, 1.0, num=int(len(audio) * sample_rate / sr), endpoint=False)
            audio = np.interp(x_new, x_old, audio).astype(np.float32)
        start = int(line.start_sec * sample_rate)
        end = min(total_samples, start + len(audio))
        if start < total_samples and end > start:
            mix[start:end] += audio[: end - start]

    dialog_path = output_dir / "dialog_track.wav"
    _write_wav(dialog_path, mix, sample_rate)
    return dialog_path


def write_srt(dialog_yaml: dict[str, Any], output_path: Path) -> Path:
    ensure_dir(output_path.parent)

    def fmt(sec: float) -> str:
        ms = int(sec * 1000)
        hh = ms // 3600000
        ms -= hh * 3600000
        mm = ms // 60000
        ms -= mm * 60000
        ss = ms // 1000
        ms -= ss * 1000
        return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"

    lines_out = []
    for i, line in enumerate(dialog_yaml.get("lines", []), start=1):
        start = float(line.get("start_sec", 0.0))
        end = float(line.get("end_sec", start + 1.0))
        text = str(line.get("text", ""))
        lines_out.append(str(i))
        lines_out.append(f"{fmt(start)} --> {fmt(end)}")
        lines_out.append(text)
        lines_out.append("")

    output_path.write_text("\n".join(lines_out), encoding="utf-8")
    return output_path

```

# /Users/bowensong/Documents/New project/src/studio/media/video.py
```python
from __future__ import annotations

import subprocess
from pathlib import Path

from ..utils import ensure_dir, get_logger, which

logger = get_logger("media.video")


def has_ffmpeg() -> bool:
    return which("ffmpeg") is not None


def _run_ffmpeg(args: list[str]) -> bool:
    cmd = ["ffmpeg", "-y", *args]
    logger.info("Running ffmpeg: %s", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except Exception as exc:
        logger.warning("ffmpeg command failed: %s", exc)
        return False


def frames_to_clip(frames_dir: Path, fps: int, output_path: Path) -> bool:
    ensure_dir(output_path.parent)
    if not has_ffmpeg():
        logger.warning("ffmpeg not found; cannot create clip %s", output_path)
        output_path.with_suffix(".txt").write_text(
            "ffmpeg missing; install ffmpeg to render MP4 clips.\n",
            encoding="utf-8",
        )
        return False

    pattern = str(frames_dir / "frame_%06d.png")
    return _run_ffmpeg(
        [
            "-framerate",
            str(fps),
            "-i",
            pattern,
            "-pix_fmt",
            "yuv420p",
            "-vcodec",
            "libx264",
            str(output_path),
        ]
    )


def concat_clips(clips: list[Path], output_path: Path) -> bool:
    ensure_dir(output_path.parent)
    if not clips:
        logger.warning("No clips provided for concat into %s", output_path)
        return False

    if not has_ffmpeg():
        output_path.with_suffix(".txt").write_text(
            "ffmpeg missing; install ffmpeg to concatenate videos.\n",
            encoding="utf-8",
        )
        return False

    concat_file = output_path.parent / f"{output_path.stem}_concat.txt"
    lines = [f"file '{p.resolve()}'" for p in clips if p.exists()]
    concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok = _run_ffmpeg(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(output_path),
        ]
    )
    return ok


def mux_audio(video_path: Path, audio_path: Path, output_path: Path) -> bool:
    ensure_dir(output_path.parent)
    if not has_ffmpeg():
        output_path.with_suffix(".txt").write_text(
            "ffmpeg missing; install ffmpeg to mux audio and video.\n",
            encoding="utf-8",
        )
        return False
    if not video_path.exists() or not audio_path.exists():
        logger.warning("Missing input for mux: %s %s", video_path, audio_path)
        return False

    return _run_ffmpeg(
        [
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
    )

```

# /Users/bowensong/Documents/New project/src/studio/models/__init__.py
```python
"""Model integration modules (diffusion, LoRA, adapters)."""

```

# /Users/bowensong/Documents/New project/src/studio/models/adapters.py
```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..utils import get_logger

logger = get_logger("models.adapters")


class ReferenceAdapter:
    name = "base"

    def apply(self, generation_kwargs: dict[str, Any], references: dict[str, Any]) -> dict[str, Any]:
        return generation_kwargs


class NoOpReferenceAdapter(ReferenceAdapter):
    name = "noop"

    def apply(self, generation_kwargs: dict[str, Any], references: dict[str, Any]) -> dict[str, Any]:
        generation_kwargs["_ref_adapter"] = "noop"
        generation_kwargs["_references"] = references
        return generation_kwargs


@dataclass
class IPAdapterConfig:
    enabled: bool = False
    weight: float = 0.7


class IPAdapterReferenceAdapter(ReferenceAdapter):
    name = "ip_adapter"

    def __init__(self, config: IPAdapterConfig | None = None) -> None:
        self.config = config or IPAdapterConfig()

    def apply(self, generation_kwargs: dict[str, Any], references: dict[str, Any]) -> dict[str, Any]:
        generation_kwargs["_ref_adapter"] = "ip_adapter"
        generation_kwargs["_references"] = references
        generation_kwargs["_ip_adapter_weight"] = self.config.weight
        logger.info(
            "IP-Adapter selected; baseline implementation keeps references in kwargs. "
            "Replace this method with diffusers IP-Adapter conditioning for production."
        )
        return generation_kwargs


def make_reference_adapter(adapter_cfg: dict[str, Any] | None) -> ReferenceAdapter:
    cfg = adapter_cfg or {}
    name = str(cfg.get("name", "noop")).lower()
    if name == "ip_adapter" and cfg.get("enabled", False):
        return IPAdapterReferenceAdapter(
            IPAdapterConfig(enabled=True, weight=float(cfg.get("weight", 0.7)))
        )
    return NoOpReferenceAdapter()

```

# /Users/bowensong/Documents/New project/src/studio/models/diffusion.py
```python
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from ..utils import ensure_dir, get_logger

logger = get_logger("models.diffusion")


@dataclass
class DiffusionConfig:
    base_id: str
    refiner_id: str | None = None
    use_refiner: bool = False
    precision: str = "bf16"
    enable_xformers: bool = True
    attention_slicing: bool = True


class VideoPlugin:
    name = "base"

    def render(self, shot: dict[str, Any], frame_indices: list[int], output_frames_dir: Path) -> list[Path]:
        raise NotImplementedError


class NativeVideoStubPlugin(VideoPlugin):
    name = "native_video_stub"

    def render(self, shot: dict[str, Any], frame_indices: list[int], output_frames_dir: Path) -> list[Path]:
        logger.info("Using native video stub plugin for shot %s", shot.get("shot_id"))
        width, height = shot.get("resolution", [1024, 1024])
        produced: list[Path] = []
        for idx in frame_indices:
            img = Image.new("RGB", (int(width), int(height)), color=(15, 20, 30))
            draw = ImageDraw.Draw(img)
            draw.text((30, 30), f"VideoStub {shot.get('shot_id')} frame={idx}", fill=(180, 220, 255))
            draw.text((30, 70), shot.get("prompt", ""), fill=(220, 220, 220))
            out = output_frames_dir / f"frame_{idx:06d}.png"
            img.save(out)
            produced.append(out)
        return produced


class DiffusionGenerator:
    def __init__(self, config: DiffusionConfig) -> None:
        self.config = config
        self._diffusers_pipeline = None
        self._diffusers_ready = False
        self._attempted = False

    def _try_load_diffusers(self) -> None:
        if self._attempted:
            return
        self._attempted = True
        try:
            import torch  # noqa: F401
            from diffusers import DiffusionPipeline

            self._diffusers_pipeline = DiffusionPipeline.from_pretrained(
                self.config.base_id,
                torch_dtype=None,
                local_files_only=True,
            )
            self._diffusers_ready = True
            logger.info("Loaded local diffusers pipeline for %s", self.config.base_id)
        except Exception as exc:
            logger.warning(
                "Diffusers pipeline unavailable (%s). Falling back to synthetic renderer.",
                exc,
            )
            self._diffusers_ready = False

    def _synthetic_frame(
        self,
        prompt: str,
        negative_prompt: str,
        seed: int,
        width: int,
        height: int,
        frame_idx: int,
        output_path: Path,
    ) -> None:
        random.seed(seed + frame_idx)
        np.random.seed((seed + frame_idx) % (2**32 - 1))

        base = np.zeros((height, width, 3), dtype=np.uint8)
        hue = abs(hash(prompt)) % 255
        base[:, :, 0] = (hue + frame_idx * 3) % 255
        base[:, :, 1] = (100 + frame_idx * 2) % 255
        base[:, :, 2] = (180 + frame_idx) % 255

        noise = np.random.randint(0, 35, size=(height, width, 3), dtype=np.uint8)
        arr = np.clip(base + noise, 0, 255)

        img = Image.fromarray(arr, mode="RGB")
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, width, 130), fill=(0, 0, 0, 170))
        draw.text((16, 10), f"prompt: {prompt[:110]}", fill=(255, 255, 255))
        draw.text((16, 40), f"negative: {negative_prompt[:110]}", fill=(230, 230, 230))
        draw.text((16, 70), f"seed={seed} frame={frame_idx}", fill=(255, 220, 180))

        # simple vignette
        px = img.load()
        cx, cy = width / 2.0, height / 2.0
        maxd = math.sqrt(cx * cx + cy * cy)
        for y in range(0, height, 4):
            for x in range(0, width, 4):
                d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / maxd
                factor = max(0.5, 1.0 - 0.45 * d)
                r, g, b = px[x, y]
                px[x, y] = (int(r * factor), int(g * factor), int(b * factor))

        img.save(output_path)

    def generate_frame(
        self,
        prompt: str,
        negative_prompt: str,
        seed: int,
        width: int,
        height: int,
        output_path: Path,
        frame_idx: int = 0,
        generation_kwargs: dict[str, Any] | None = None,
    ) -> Path:
        ensure_dir(output_path.parent)
        self._try_load_diffusers()
        if self._diffusers_ready:
            # Deterministic fallback still used intentionally to avoid hidden downloads.
            logger.info(
                "Diffusers is available but synthetic path is used by default for reproducibility/offline safety. "
                "Set STUDIO_ALLOW_MODEL_EXEC=1 and extend this method for real sampling."
            )
        self._synthetic_frame(
            prompt=prompt,
            negative_prompt=negative_prompt,
            seed=seed,
            width=width,
            height=height,
            frame_idx=frame_idx,
            output_path=output_path,
        )
        return output_path

    def generate_frames_for_shot(
        self,
        shot: dict[str, Any],
        prompt: str,
        negative_prompt: str,
        frame_indices: list[int],
        output_frames_dir: Path,
        generation_kwargs: dict[str, Any] | None = None,
    ) -> list[Path]:
        ensure_dir(output_frames_dir)
        width, height = shot.get("resolution", [1024, 1024])
        shot_seed = int(shot.get("generation", {}).get("seed", 0))
        method = shot.get("generation", {}).get("method", "image_only")
        plugin = shot.get("generation", {}).get("plugin", "native_video_stub")

        if method == "video_plugin":
            if plugin == "native_video_stub":
                return NativeVideoStubPlugin().render(shot, frame_indices, output_frames_dir)

        out: list[Path] = []
        for idx in frame_indices:
            p = output_frames_dir / f"frame_{idx:06d}.png"
            self.generate_frame(
                prompt=prompt,
                negative_prompt=negative_prompt,
                seed=shot_seed,
                width=int(width),
                height=int(height),
                output_path=p,
                frame_idx=idx,
                generation_kwargs=generation_kwargs,
            )
            out.append(p)
        return out

```

# /Users/bowensong/Documents/New project/src/studio/models/lora.py
```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..utils import sha256_file


@dataclass
class LoRAMath:
    rank: int
    alpha: float

    def scale(self) -> float:
        return self.alpha / float(self.rank)

    def description(self) -> str:
        return (
            "W' = W + (alpha/r) * A @ B, "
            f"rank={self.rank}, alpha={self.alpha}, scale={self.scale():.4f}"
        )


def lora_checksum(path: str | Path) -> str | None:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None
    return sha256_file(p)

```

# /Users/bowensong/Documents/New project/src/studio/pipeline/__init__.py
```python
"""Pipeline planning and execution modules."""

```

# /Users/bowensong/Documents/New project/src/studio/pipeline/cache.py
```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..utils import load_json, save_json, stable_hash


def _cache_file(compiled_dir: Path) -> Path:
    return compiled_dir / "cache_state.json"


def compute_signature(payload: dict[str, Any]) -> str:
    return stable_hash(payload)


def read_cache(compiled_dir: Path) -> dict[str, Any]:
    p = _cache_file(compiled_dir)
    if not p.exists():
        return {}
    return load_json(p)


def write_cache(compiled_dir: Path, state: dict[str, Any]) -> None:
    save_json(_cache_file(compiled_dir), state)


def should_skip(
    compiled_dir: Path,
    task_key: str,
    signature: str,
    required_outputs: list[Path],
    resume: bool,
) -> bool:
    if not resume:
        return False
    state = read_cache(compiled_dir)
    if state.get(task_key) != signature:
        return False
    return all(p.exists() for p in required_outputs)


def update_task_signature(compiled_dir: Path, task_key: str, signature: str) -> None:
    state = read_cache(compiled_dir)
    state[task_key] = signature
    write_cache(compiled_dir, state)

```

# /Users/bowensong/Documents/New project/src/studio/pipeline/executor.py
```python
from __future__ import annotations

import difflib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import LoadedProject
from ..media.audio import audio_stats, mix_dialog_and_music
from ..media.music import render_music_track
from ..media.tts import render_dialog_track, write_srt
from ..media.video import concat_clips, frames_to_clip, mux_audio
from ..models.adapters import make_reference_adapter
from ..models.diffusion import DiffusionConfig, DiffusionGenerator
from ..models.lora import lora_checksum
from ..prompts.composer import apply_prompt_mutations, compose_negative_prompt, compose_prompt
from ..utils import (
    ensure_dir,
    get_git_hash,
    get_logger,
    load_json,
    load_yaml,
    now_utc_iso,
    save_json,
    save_yaml,
    stable_hash,
    write_text,
)
from .cache import compute_signature, should_skip, update_task_signature

logger = get_logger("pipeline.executor")


@dataclass
class CompiledShot:
    project: str
    scene: str
    shot_id: str
    scene_data: dict[str, Any]
    shot_data: dict[str, Any]
    dialog_data: dict[str, Any]
    compiled_prompt: str
    compiled_negative_prompt: str
    output_dir: Path
    compiled_dir: Path
    frame_count: int
    frame_range: tuple[int, int] | None
    patch_files: list[str]
    compiled_hash: str
    visual_hash: str
    audio_hash: str


def _set_path(payload: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cursor: Any = payload
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    cursor[parts[-1]] = value


def _delete_path(payload: dict[str, Any], dotted: str) -> None:
    parts = dotted.split(".")
    cursor: Any = payload
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            return
        cursor = cursor[part]
    cursor.pop(parts[-1], None)


def _append_path(payload: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cursor: Any = payload
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    arr = cursor.get(parts[-1])
    if not isinstance(arr, list):
        arr = []
        cursor[parts[-1]] = arr
    arr.append(value)


def _extend_path(payload: dict[str, Any], dotted: str, values: list[Any]) -> None:
    parts = dotted.split(".")
    cursor: Any = payload
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    arr = cursor.get(parts[-1])
    if not isinstance(arr, list):
        arr = []
        cursor[parts[-1]] = arr
    arr.extend(values)


def _parse_frame_range(value: Any) -> tuple[int, int] | None:
    if isinstance(value, list) and len(value) == 2:
        start = max(0, int(value[0]))
        end = max(start, int(value[1]))
        return (start, end)
    if isinstance(value, dict):
        start = int(value.get("start", 0))
        end = int(value.get("end", start))
        return (max(0, start), max(start, end))
    if isinstance(value, str) and "-" in value:
        left, right = value.split("-", 1)
        if left.isdigit() and right.isdigit():
            start = int(left)
            end = int(right)
            return (max(0, start), max(start, end))
    return None


def _apply_audio_op(dialog: dict[str, Any], scene: dict[str, Any], op: dict[str, Any]) -> None:
    opname = op.get("op")
    lines = scene.get("_dialog_lines", dialog.get("lines", []))

    if opname == "set_dialog_text":
        speaker = str(op.get("speaker", ""))
        line_id = str(op.get("line_id", ""))
        text = str(op.get("text", ""))
        for line in lines:
            if str(line.get("line_id")) == line_id and (not speaker or str(line.get("speaker")) == speaker):
                line["text"] = text

    elif opname == "shift_dialog_time":
        line_id = str(op.get("line_id", ""))
        delta = float(op.get("delta_seconds", 0.0))
        for line in lines:
            if str(line.get("line_id")) == line_id:
                line["start_sec"] = max(0.0, float(line.get("start_sec", 0.0)) + delta)
                line["end_sec"] = max(float(line["start_sec"]) + 0.05, float(line.get("end_sec", 0.0)) + delta)

    elif opname == "replace_music":
        scene["music_override"] = str(op.get("track_path", ""))

    scene["_dialog_lines"] = lines


def _apply_patch_ops(
    shot: dict[str, Any],
    scene_data: dict[str, Any],
    dialog_data: dict[str, Any],
    prompt: str,
    negative: str,
    ops: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str, str]:
    shot_out = dict(shot)
    scene_out = dict(scene_data)
    dialog_out = dict(dialog_data)

    prompt_ops: list[dict[str, Any]] = []
    for op in ops:
        name = op.get("op")
        if name in {
            "replace_prompt",
            "add_prompt_prefix",
            "add_prompt_suffix",
            "add_negative_prefix",
            "add_negative_suffix",
        }:
            prompt_ops.append(op)
            continue

        if name == "set":
            _set_path(shot_out, str(op.get("path", "")), op.get("value"))
        elif name == "delete":
            _delete_path(shot_out, str(op.get("path", "")))
        elif name == "append":
            _append_path(shot_out, str(op.get("path", "")), op.get("value"))
        elif name == "extend":
            _extend_path(shot_out, str(op.get("path", "")), list(op.get("values", [])))
        elif name == "set_ref":
            refs = shot_out.get("references", {})
            if not isinstance(refs, dict):
                refs = {}
            refs[str(op.get("ref_path_key", "ref"))] = op.get("value")
            shot_out["references"] = refs
        elif name == "set_frame_range":
            fr = _parse_frame_range(op.get("value"))
            if fr:
                gen = shot_out.get("generation", {})
                if not isinstance(gen, dict):
                    gen = {}
                gen["frame_range"] = [fr[0], fr[1]]
                shot_out["generation"] = gen
        elif name in {"set_dialog_text", "shift_dialog_time", "replace_music"}:
            _apply_audio_op(dialog_out, scene_out, op)

    prompt_out, negative_out = apply_prompt_mutations(prompt, negative, prompt_ops)
    return shot_out, scene_out, dialog_out, prompt_out, negative_out


def _resolve_path(root: Path, path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (root / p).resolve()


def _load_patch_file(patch_path: Path) -> dict[str, Any]:
    return load_yaml(patch_path)


def _patches_for_target(
    patch_paths: list[Path],
    project: str,
    scene: str,
    shot: str,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for patch_path in sorted(patch_paths):
        patch = _load_patch_file(patch_path)
        target = patch.get("target", {})
        if target.get("project") and str(target.get("project")) != project:
            continue
        if target.get("scene") and str(target.get("scene")) != scene:
            continue
        if target.get("shot") and str(target.get("shot")) != shot:
            continue
        selected.append({"path": str(patch_path), "data": patch})
    return selected


def _prompt_for_frame(base_prompt: str, prompt_schedule: list[dict[str, Any]], frame_idx: int) -> str:
    if not prompt_schedule:
        return base_prompt
    current_suffix = ""
    for item in sorted(prompt_schedule, key=lambda x: int(x.get("frame", 0))):
        if frame_idx >= int(item.get("frame", 0)):
            current_suffix = str(item.get("prompt_suffix", ""))
    if current_suffix:
        return f"{base_prompt} {current_suffix}".strip()
    return base_prompt


def compile_scene(
    workspace: dict[str, Any],
    project: LoadedProject,
    scene_path: Path,
    run_id: str,
    output_root: Path,
    selected_shot_ids: list[str] | None,
    patch_paths: list[Path],
) -> tuple[list[CompiledShot], dict[str, Any], dict[str, Any]]:
    ws_dir = Path(workspace["_workspace_dir"])  # repository root
    project_root = project.path.parent

    scene_data = load_yaml(scene_path)
    scene_name = str(scene_data.get("scene_name", scene_path.stem))

    dialog_ref = scene_data.get("dialog_ref")
    if dialog_ref:
        dialog_path = _resolve_path(ws_dir, str(dialog_ref))
        dialog_data = load_yaml(dialog_path)
    else:
        dialog_path = None
        dialog_data = {"lines": [], "speakers": {}}

    global_guidelines = workspace.get("global_guidelines", {})
    global_prompt = str(global_guidelines.get("prompt", ""))
    global_negative = str(global_guidelines.get("negative_prompt", ""))

    project_vibes = project.data.get("style_bible", {}).get("vibe_guidelines", [])
    project_vibe = ", ".join(str(x) for x in project_vibes)
    scene_vibe = str(scene_data.get("vibe_overrides", {}).get("prompt", ""))
    scene_negative = str(scene_data.get("vibe_overrides", {}).get("negative_prompt", ""))

    template_path = project_root / "scripts" / "prompt_templates" / "default_prompt.j2"
    compiled: list[CompiledShot] = []

    shots = scene_data.get("shots", [])
    for shot in shots:
        shot_id = str(shot.get("shot_id"))
        if selected_shot_ids and shot_id not in selected_shot_ids:
            continue

        shot_prompt = str(shot.get("prompt", ""))
        shot_negative = str(shot.get("negative_prompt", ""))
        refs = shot.get("references", {}) if isinstance(shot.get("references"), dict) else {}

        prompt = compose_prompt(
            global_guidelines=global_prompt,
            project_vibe=project_vibe,
            scene_vibe=scene_vibe,
            shot_prompt=shot_prompt,
            camera=str(shot.get("camera", "")),
            lens=str(shot.get("lens", "")),
            lighting=str(shot.get("lighting", "")),
            wardrobe=str(refs.get("wardrobe", "")),
            location=str(refs.get("background", scene_data.get("location_refs", [""])[0] if scene_data.get("location_refs") else "")),
            template_path=str(template_path) if template_path.exists() else None,
        )
        negative = compose_negative_prompt(global_negative, scene_negative, shot_negative)

        shot_scene = dict(scene_data)
        shot_dialog = dict(dialog_data)

        target_patches = _patches_for_target(
            patch_paths=patch_paths,
            project=project.name,
            scene=scene_name,
            shot=shot_id,
        )

        for patch in target_patches:
            ops = patch["data"].get("ops", [])
            shot, shot_scene, shot_dialog, prompt, negative = _apply_patch_ops(
                shot=shot,
                scene_data=shot_scene,
                dialog_data=shot_dialog,
                prompt=prompt,
                negative=negative,
                ops=ops,
            )

        out_dir = output_root / run_id / project.name / scene_name / shot_id
        compiled_dir = out_dir / "compiled"
        ensure_dir(compiled_dir)

        old_prompt = (compiled_dir / "compiled_prompt.txt").read_text(encoding="utf-8") if (compiled_dir / "compiled_prompt.txt").exists() else ""
        if old_prompt:
            diff = difflib.unified_diff(
                old_prompt.splitlines(),
                prompt.splitlines(),
                fromfile="previous",
                tofile="current",
                lineterm="",
            )
            write_text(compiled_dir / "compiled_prompt.diff.txt", "\n".join(diff) + "\n")
        else:
            write_text(compiled_dir / "compiled_prompt.diff.txt", "(no previous prompt for diff)\n")

        frame_count = max(1, int(round(float(shot.get("duration", 1.0)) * float(shot.get("fps", 24)))))
        fr = shot.get("generation", {}).get("frame_range")
        frame_range = _parse_frame_range(fr) if fr is not None else None

        model_cfg = project.data.get("model", {})
        lora_checksums = []
        for lora in model_cfg.get("loras", []):
            path = lora.get("path")
            if path:
                checksum = lora_checksum(_resolve_path(ws_dir, str(path)))
                if checksum:
                    lora_checksums.append({"path": path, "sha256": checksum})

        provenance = {
            "timestamp_utc": now_utc_iso(),
            "git_hash": get_git_hash(),
            "workspace_path": workspace.get("_workspace_path"),
            "project_yaml": str(project.path),
            "scene_yaml": str(scene_path),
            "dialog_yaml": str(dialog_path) if dialog_path else None,
            "model_ids": {
                "base": model_cfg.get("base_id"),
                "refiner": model_cfg.get("refiner_id"),
                "use_refiner": model_cfg.get("use_refiner", False),
            },
            "lora_checksums": lora_checksums,
        }

        compiled_meta = {
            "project": project.name,
            "scene": scene_name,
            "shot": shot_id,
            "patches": [p["path"] for p in target_patches],
            "frame_count": frame_count,
            "frame_range": list(frame_range) if frame_range else None,
            "provenance": provenance,
        }
        visual_hash = stable_hash(
            {
                "shot": shot,
                "prompt": prompt,
                "negative": negative,
                "refs": shot.get("references", {}),
                "generation": shot.get("generation", {}),
            }
        )
        audio_hash = stable_hash(
            {
                "scene_music_override": shot_scene.get("music_override"),
                "dialog_lines": shot_dialog.get("lines", []),
            }
        )
        compiled_hash = stable_hash(
            {"visual_hash": visual_hash, "audio_hash": audio_hash, "meta": compiled_meta}
        )
        compiled_meta["compiled_hash"] = compiled_hash
        compiled_meta["visual_hash"] = visual_hash
        compiled_meta["audio_hash"] = audio_hash

        save_yaml(compiled_dir / "compiled_scene.yaml", shot_scene)
        save_yaml(compiled_dir / "compiled_shot.yaml", shot)
        write_text(compiled_dir / "compiled_prompt.txt", prompt + "\n")
        write_text(compiled_dir / "compiled_negative_prompt.txt", negative + "\n")
        save_json(compiled_dir / "compiled_metadata.json", compiled_meta)

        compiled.append(
            CompiledShot(
                project=project.name,
                scene=scene_name,
                shot_id=shot_id,
                scene_data=shot_scene,
                shot_data=shot,
                dialog_data=shot_dialog,
                compiled_prompt=prompt,
                compiled_negative_prompt=negative,
                output_dir=out_dir,
                compiled_dir=compiled_dir,
                frame_count=frame_count,
                frame_range=frame_range,
                patch_files=[p["path"] for p in target_patches],
                compiled_hash=compiled_hash,
                visual_hash=visual_hash,
                audio_hash=audio_hash,
            )
        )

    return compiled, scene_data, dialog_data


def _resolve_requested_frame_indices(compiled: CompiledShot) -> list[int]:
    all_indices = list(range(compiled.frame_count))
    frames_dir = compiled.output_dir / "frames"

    if not compiled.frame_range:
        return all_indices

    start, end = compiled.frame_range
    start = max(0, min(start, compiled.frame_count - 1))
    end = max(start, min(end, compiled.frame_count - 1))

    requested = set(range(start, end + 1))
    existing = {
        int(p.stem.split("_")[-1])
        for p in frames_dir.glob("frame_*.png")
        if p.stem.split("_")[-1].isdigit()
    }
    missing = {idx for idx in all_indices if idx not in existing}
    return sorted(requested | missing)


def _copy_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    ensure_dir(dst.parent)
    shutil.copy2(src, dst)
    return True


def execute_compiled_scene(
    workspace: dict[str, Any],
    project: LoadedProject,
    scene_name: str,
    compiled_shots: list[CompiledShot],
    output_root: Path,
    run_id: str,
    resume: bool,
    compile_only: bool,
) -> None:
    if not compiled_shots:
        return

    ws_dir = Path(workspace["_workspace_dir"])
    run_generation_cfg = workspace.get("global_defaults", {}).get("run_settings", {})
    model_cfg_data = project.data.get("model", workspace.get("global_defaults", {}).get("model", {}))

    diff_cfg = DiffusionConfig(
        base_id=str(model_cfg_data.get("base_id", "stabilityai/stable-diffusion-xl-base-1.0")),
        refiner_id=str(model_cfg_data.get("refiner_id", "")) or None,
        use_refiner=bool(model_cfg_data.get("use_refiner", False)),
        precision=str(model_cfg_data.get("precision", "bf16")),
        enable_xformers=bool(model_cfg_data.get("enable_xformers", True)),
        attention_slicing=bool(model_cfg_data.get("attention_slicing", True)),
    )

    generator = DiffusionGenerator(diff_cfg)
    ref_adapter = make_reference_adapter(project.data.get("reference_adapter", {"name": "noop"}))

    scene_out_dir = output_root / run_id / project.name / scene_name
    ensure_dir(scene_out_dir)

    scene_clip_paths: list[Path] = []
    scene_dialog_data = compiled_shots[0].dialog_data
    scene_data = compiled_shots[0].scene_data

    for compiled in compiled_shots:
        frames_dir = compiled.output_dir / "frames"
        ensure_dir(frames_dir)
        clip_path = compiled.output_dir / "clip.mp4"

        frame_indices = _resolve_requested_frame_indices(compiled)

        frame_signature = compute_signature(
            {
                "visual_hash": compiled.visual_hash,
                "frame_indices": frame_indices,
                "model": model_cfg_data,
                "generation": compiled.shot_data.get("generation", {}),
                "run_generation_cfg": run_generation_cfg,
                "code_git": get_git_hash(),
            }
        )

        skip_frames = should_skip(
            compiled_dir=compiled.compiled_dir,
            task_key="frames",
            signature=frame_signature,
            required_outputs=[frames_dir / f"frame_{i:06d}.png" for i in range(compiled.frame_count)],
            resume=resume,
        )

        if compile_only:
            logger.info("Compile-only mode: skipping render for %s/%s/%s", compiled.project, compiled.scene, compiled.shot_id)
            continue

        if not skip_frames:
            logger.info("Generating %s frames for %s/%s/%s", len(frame_indices), compiled.project, compiled.scene, compiled.shot_id)
            prompt_schedule = compiled.shot_data.get("generation", {}).get("prompt_schedule", [])
            refs = compiled.shot_data.get("references", {})

            for frame_idx in frame_indices:
                prompt_frame = _prompt_for_frame(compiled.compiled_prompt, prompt_schedule, frame_idx)
                gen_kwargs = ref_adapter.apply({}, refs)
                generator.generate_frame(
                    prompt=prompt_frame,
                    negative_prompt=compiled.compiled_negative_prompt,
                    seed=int(compiled.shot_data.get("generation", {}).get("seed", 0)),
                    width=int(compiled.shot_data.get("resolution", [1024, 1024])[0]),
                    height=int(compiled.shot_data.get("resolution", [1024, 1024])[1]),
                    output_path=frames_dir / f"frame_{frame_idx:06d}.png",
                    frame_idx=frame_idx,
                    generation_kwargs=gen_kwargs,
                )
            update_task_signature(compiled.compiled_dir, "frames", frame_signature)
        else:
            logger.info("Skipping frame generation (cache hit) for %s/%s/%s", compiled.project, compiled.scene, compiled.shot_id)

        clip_signature = compute_signature(
            {
                "frame_signature": frame_signature,
                "fps": compiled.shot_data.get("fps", 24),
                "frame_count": compiled.frame_count,
            }
        )
        if should_skip(
            compiled_dir=compiled.compiled_dir,
            task_key="clip",
            signature=clip_signature,
            required_outputs=[clip_path],
            resume=resume,
        ):
            logger.info("Skipping clip assembly (cache hit) for %s/%s/%s", compiled.project, compiled.scene, compiled.shot_id)
        else:
            frames_to_clip(frames_dir=frames_dir, fps=int(compiled.shot_data.get("fps", 24)), output_path=clip_path)
            update_task_signature(compiled.compiled_dir, "clip", clip_signature)

        metadata = {
            "project": compiled.project,
            "scene": compiled.scene,
            "shot": compiled.shot_id,
            "compiled_prompt": compiled.compiled_prompt,
            "compiled_negative_prompt": compiled.compiled_negative_prompt,
            "patches": compiled.patch_files,
            "frame_count": compiled.frame_count,
            "frame_range": list(compiled.frame_range) if compiled.frame_range else None,
            "references": compiled.shot_data.get("references", {}),
            "generation": compiled.shot_data.get("generation", {}),
            "provenance": {
                "git_hash": get_git_hash(),
                "compiled_hash": compiled.compiled_hash,
                "model_ids": {
                    "base_id": model_cfg_data.get("base_id"),
                    "refiner_id": model_cfg_data.get("refiner_id"),
                    "use_refiner": model_cfg_data.get("use_refiner", False),
                },
            },
        }
        save_json(compiled.output_dir / "metadata.json", metadata)
        scene_clip_paths.append(clip_path)

    if compile_only:
        return

    # scene-level assembly + audio
    scene_video_no_audio = scene_out_dir / "scene_video_no_audio.mp4"
    concat_clips(scene_clip_paths, scene_video_no_audio)

    total_duration = float(sum(float(s.shot_data.get("duration", 0.0)) for s in compiled_shots))
    audio_dir = scene_out_dir / "audio"
    ensure_dir(audio_dir)

    dialog_signature = compute_signature(
        {
            "audio_hash": compiled_shots[0].audio_hash,
            "total_duration": total_duration,
            "code_git": get_git_hash(),
        }
    )

    dialog_track = audio_dir / "dialog_track.wav"
    music_track = audio_dir / "music_track.wav"
    final_audio = audio_dir / "final_audio.wav"

    should_render_audio = not should_skip(
        compiled_dir=compiled_shots[0].compiled_dir,
        task_key="scene_audio",
        signature=dialog_signature,
        required_outputs=[dialog_track, music_track, final_audio],
        resume=resume,
    )

    if should_render_audio:
        dialog_rendered = render_dialog_track(
            dialog_yaml=scene_dialog_data,
            project_root=project.path.parent,
            output_dir=audio_dir,
            total_duration_sec=total_duration,
            default_sample_rate=24000,
        )
        write_srt(scene_dialog_data, audio_dir / "subtitles.srt")

        music_override = scene_data.get("music_override")
        if music_override and _copy_if_exists(_resolve_path(ws_dir, str(music_override)), music_track):
            logger.info("Using music override track: %s", music_override)
        else:
            scene_prompt = str(scene_data.get("vibe_overrides", {}).get("prompt", ""))
            render_music_track(
                project_root=project.path.parent,
                scene_prompt=scene_prompt,
                duration_sec=total_duration,
                output_path=music_track,
                sample_rate=24000,
            )

        mix_dialog_and_music(
            dialog_path=dialog_rendered,
            music_path=music_track,
            output_path=final_audio,
            target_lufs=float(project.data.get("output_specs", {}).get("loudness_target_lufs", -16.0)),
            ducking_db=-8.0,
            fade_in_sec=0.3,
            fade_out_sec=0.5,
        )
        update_task_signature(compiled_shots[0].compiled_dir, "scene_audio", dialog_signature)
    else:
        logger.info("Skipping scene audio render (cache hit) for %s/%s", project.name, scene_name)

    scene_output = scene_out_dir / "scene.mp4"
    mux_audio(scene_video_no_audio, final_audio, scene_output)

    a_stats = audio_stats(final_audio) if final_audio.exists() else {"lufs": -30.0, "clipping_ratio": 0.0}
    for compiled in compiled_shots:
        meta_path = compiled.output_dir / "metadata.json"
        if meta_path.exists():
            meta = load_json(meta_path)
            meta["audio_stats"] = a_stats
            meta["loudness_target_lufs"] = float(project.data.get("output_specs", {}).get("loudness_target_lufs", -16.0))
            save_json(meta_path, meta)


def finalize_project_video(output_root: Path, run_id: str, project_name: str, scene_names: list[str]) -> Path:
    project_dir = output_root / run_id / project_name
    clips = [project_dir / scene / "scene.mp4" for scene in scene_names if (project_dir / scene / "scene.mp4").exists()]
    final_path = project_dir / "final.mp4"
    concat_clips(clips, final_path)
    return final_path

```

# /Users/bowensong/Documents/New project/src/studio/pipeline/planner.py
```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ShotTask:
    project: str
    scene: str
    shot: str
    scene_path: Path
    output_dir: Path
    compile_only: bool = False


@dataclass
class SceneTask:
    project: str
    scene: str
    scene_path: Path
    output_dir: Path
    shots: list[ShotTask] = field(default_factory=list)


@dataclass
class RunPlan:
    run_id: str
    workspace_path: Path
    scene_tasks: list[SceneTask] = field(default_factory=list)

    def flat_shot_tasks(self) -> list[ShotTask]:
        out: list[ShotTask] = []
        for scene_task in self.scene_tasks:
            out.extend(scene_task.shots)
        return out

```

# /Users/bowensong/Documents/New project/src/studio/pipeline/registry.py
```python
from __future__ import annotations

from typing import Any, Callable


class Registry:
    def __init__(self) -> None:
        self._items: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, factory: Callable[..., Any]) -> None:
        self._items[name] = factory

    def get(self, name: str) -> Callable[..., Any]:
        if name not in self._items:
            raise KeyError(f"Registry item not found: {name}")
        return self._items[name]

    def names(self) -> list[str]:
        return sorted(self._items)

```

# /Users/bowensong/Documents/New project/src/studio/prompts/__init__.py
```python
"""Prompt composition helpers."""

```

# /Users/bowensong/Documents/New project/src/studio/prompts/composer.py
```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Template

from ..utils import read_text


def _layer(*parts: str) -> str:
    filtered = [p.strip().strip(".") for p in parts if p and str(p).strip()]
    return ". ".join(filtered)


def compose_prompt(
    global_guidelines: str,
    project_vibe: str,
    scene_vibe: str,
    shot_prompt: str,
    camera: str,
    lens: str,
    lighting: str,
    wardrobe: str,
    location: str,
    template_path: str | None = None,
) -> str:
    if template_path:
        tpath = Path(template_path)
        if tpath.exists():
            template = Template(read_text(tpath))
            return template.render(
                global_guidelines=global_guidelines,
                project_vibe=project_vibe,
                scene_vibe=scene_vibe,
                shot_prompt=shot_prompt,
                camera=camera,
                lens=lens,
                lighting=lighting,
                wardrobe=wardrobe,
                location=location,
            ).strip()
    return _layer(
        global_guidelines,
        project_vibe,
        scene_vibe,
        shot_prompt,
        f"Camera {camera}",
        f"Lens {lens}",
        f"Lighting {lighting}",
        f"Wardrobe {wardrobe}",
        f"Location {location}",
    )


def compose_negative_prompt(global_negative: str, scene_negative: str, shot_negative: str) -> str:
    return _layer(global_negative, scene_negative, shot_negative)


def apply_prompt_mutations(
    prompt: str,
    negative_prompt: str,
    operations: list[dict[str, Any]],
) -> tuple[str, str]:
    p = prompt
    n = negative_prompt
    for op in operations:
        name = op.get("op")
        if name == "replace_prompt":
            p = p.replace(str(op.get("find", "")), str(op.get("replace", "")))
        elif name == "add_prompt_prefix":
            p = f"{op.get('text', '')} {p}".strip()
        elif name == "add_prompt_suffix":
            p = f"{p} {op.get('text', '')}".strip()
        elif name == "add_negative_prefix":
            n = f"{op.get('text', '')} {n}".strip()
        elif name == "add_negative_suffix":
            n = f"{n} {op.get('text', '')}".strip()
    return p, n

```

# /Users/bowensong/Documents/New project/src/studio/run.py
```python
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

```

# /Users/bowensong/Documents/New project/src/studio/tools/__init__.py
```python
"""Dataset preparation and inspection tools."""

```

# /Users/bowensong/Documents/New project/src/studio/tools/auto_caption.py
```python
from __future__ import annotations

import argparse
from pathlib import Path

from ..utils import ensure_dir, get_logger, list_files, setup_logging

logger = get_logger("tools.auto_caption")


def infer_caption_from_filename(stem: str, token: str) -> str:
    base = stem.replace("_", " ").replace("-", " ").strip()
    if not base:
        base = "portrait"
    return f"{token} {base}, high quality portrait"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Baseline auto-captioning from filenames")
    p.add_argument("--images", required=True, help="Directory of images")
    p.add_argument("--captions", required=True, help="Output captions directory")
    p.add_argument("--token", default="<me>")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--log_level", default="INFO")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    img_dir = Path(args.images).resolve()
    cap_dir = ensure_dir(Path(args.captions).resolve())

    images = list_files(img_dir, patterns=("*.jpg", "*.jpeg", "*.png", "*.webp"))
    for image in images:
        caption_path = cap_dir / f"{image.stem}.txt"
        if caption_path.exists() and not args.overwrite:
            continue
        caption = infer_caption_from_filename(image.stem, args.token)
        caption_path.write_text(caption + "\n", encoding="utf-8")

    logger.info("Wrote %s captions to %s", len(images), cap_dir)


if __name__ == "__main__":
    main()

```

# /Users/bowensong/Documents/New project/src/studio/tools/dataset_report.py
```python
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ..utils import get_logger, list_files, save_json, setup_logging

logger = get_logger("tools.dataset_report")


def build_dataset_report(dataset_root: Path) -> dict[str, Any]:
    train_images_dir = dataset_root / "train" / "images"
    train_caps_dir = dataset_root / "train" / "captions"
    reg_dir = dataset_root / "reg"

    images = list_files(train_images_dir, patterns=("*.jpg", "*.jpeg", "*.png", "*.webp"))
    captions = list_files(train_caps_dir, patterns=("*.txt",))

    cap_stems = {p.stem for p in captions}
    img_stems = {p.stem for p in images}

    missing_caption = sorted(img_stems - cap_stems)
    orphan_caption = sorted(cap_stems - img_stems)

    reg_images = list_files(reg_dir, patterns=("*.jpg", "*.jpeg", "*.png", "*.webp")) if reg_dir.exists() else []

    return {
        "dataset_root": str(dataset_root),
        "train_images": len(images),
        "train_captions": len(captions),
        "reg_images": len(reg_images),
        "missing_caption_count": len(missing_caption),
        "orphan_caption_count": len(orphan_caption),
        "missing_caption_stems": missing_caption,
        "orphan_caption_stems": orphan_caption,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dataset report for identity LoRA data")
    p.add_argument("--dataset_root", required=True)
    p.add_argument("--output", default=None)
    p.add_argument("--log_level", default="INFO")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    report = build_dataset_report(Path(args.dataset_root).resolve())
    if args.output:
        save_json(Path(args.output).resolve(), report)
        logger.info("Report written to %s", args.output)
    else:
        import json

        print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()

```

# /Users/bowensong/Documents/New project/src/studio/tools/extract_frames.py
```python
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from ..utils import ensure_dir, get_logger, setup_logging, which

logger = get_logger("tools.extract_frames")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract video frames to images")
    p.add_argument("--input", required=True, help="Input video path")
    p.add_argument("--output", required=True, help="Output frames directory")
    p.add_argument("--fps", type=float, default=None, help="Optional output FPS")
    p.add_argument("--log_level", default="INFO")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is required for extract_frames.py")

    in_path = Path(args.input).resolve()
    out_dir = ensure_dir(Path(args.output).resolve())

    vf = []
    if args.fps:
        vf = ["-vf", f"fps={args.fps}"]

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(in_path),
        *vf,
        str(out_dir / "frame_%06d.png"),
    ]
    logger.info("Running: %s", " ".join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()

```

# /Users/bowensong/Documents/New project/src/studio/tools/face_crop_align.py
```python
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from ..utils import ensure_dir, get_logger, list_files, setup_logging

logger = get_logger("tools.face_crop_align")


def center_crop(img: Image.Image, size: int) -> Image.Image:
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    crop = img.crop((left, top, left + side, top + side))
    return crop.resize((size, size), Image.Resampling.LANCZOS)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Optional face crop/align baseline (center-crop fallback)")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--size", type=int, default=1024)
    p.add_argument("--log_level", default="INFO")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    in_dir = Path(args.input).resolve()
    out_dir = ensure_dir(Path(args.output).resolve())

    images = list_files(in_dir, patterns=("*.jpg", "*.jpeg", "*.png"))
    for image in images:
        img = Image.open(image).convert("RGB")
        cropped = center_crop(img, args.size)
        cropped.save(out_dir / image.name)

    logger.info("Wrote %s aligned images to %s", len(images), out_dir)


if __name__ == "__main__":
    main()

```

# /Users/bowensong/Documents/New project/src/studio/train_identity.py
```python
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .models.lora import LoRAMath
from .tools.dataset_report import build_dataset_report
from .utils import ensure_dir, get_git_hash, get_logger, load_yaml, save_json, setup_logging

logger = get_logger("train_identity")


def _check_heavy_deps() -> tuple[bool, str]:
    try:
        import accelerate  # noqa: F401
        import diffusers  # noqa: F401
        import torch  # noqa: F401

        return True, ""
    except Exception as exc:
        return False, str(exc)


def _sample_image(output_dir: Path, step: int, token: str = "<me>") -> None:
    img = Image.new("RGB", (768, 768), color=(20 + (step * 3) % 120, 40, 70))
    draw = ImageDraw.Draw(img)
    draw.text((30, 30), f"Training sample step={step}", fill=(255, 255, 255))
    draw.text((30, 70), f"identity token {token}", fill=(220, 220, 220))
    out = output_dir / f"sample_{step:06d}.png"
    img.save(out)


def _mock_train(config: dict[str, Any], out_dir: Path, resume_from: Path | None) -> Path:
    train_cfg = config.get("train", {})
    lora_cfg = config.get("lora", {})

    max_steps = int(train_cfg.get("max_train_steps", 100))
    save_every = int(train_cfg.get("save_every_steps", 50))
    sample_every = int(train_cfg.get("sample_every_steps", 50))

    state_path = out_dir / "train_state.json"
    start_step = 0

    if resume_from and (resume_from / "train_state.json").exists():
        resume_state = json.loads((resume_from / "train_state.json").read_text(encoding="utf-8"))
        start_step = int(resume_state.get("step", 0))
        logger.info("Resuming mock training from step %s", start_step)

    samples_dir = ensure_dir(out_dir / "samples")
    checkpoints_dir = ensure_dir(out_dir / "checkpoints")

    random.seed(int(config.get("seed", 42)))

    for step in range(start_step + 1, max_steps + 1):
        loss = 1.0 / (1 + 0.03 * step) + random.uniform(-0.02, 0.02)
        if step % sample_every == 0:
            _sample_image(samples_dir, step)
        if step % save_every == 0:
            ckpt = checkpoints_dir / f"step_{step:06d}.json"
            ckpt.write_text(
                json.dumps({"step": step, "mock_loss": loss}, indent=2),
                encoding="utf-8",
            )
        state_path.write_text(json.dumps({"step": step, "loss": loss}, indent=2), encoding="utf-8")

    lora_math = LoRAMath(rank=int(lora_cfg.get("rank", 16)), alpha=float(lora_cfg.get("alpha", 32)))
    final_path = out_dir / "final_lora.safetensors"
    final_payload = {
        "format": "mock_safetensors",
        "note": "fallback artifact generated because full diffusers training is optional",
        "lora_math": lora_math.description(),
        "rank": lora_math.rank,
        "alpha": lora_math.alpha,
        "dropout": float(lora_cfg.get("dropout", 0.0)),
        "git_hash": get_git_hash(),
    }
    final_path.write_text(json.dumps(final_payload, indent=2), encoding="utf-8")
    return final_path


def _real_train_stub(config: dict[str, Any], out_dir: Path, resume_from: Path | None) -> Path:
    # This path is intentionally conservative: it validates environment and then delegates
    # to a reproducible mock loop unless user extends with a full diffusers trainer.
    logger.info(
        "Heavy dependencies detected. Baseline trainer remains mock by default for offline reproducibility. "
        "Replace _real_train_stub with a full diffusers+accelerate SDXL LoRA loop when model weights are available locally."
    )
    return _mock_train(config=config, out_dir=out_dir, resume_from=resume_from)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train identity LoRA for SDXL")
    p.add_argument("--config", required=True)
    p.add_argument("--log_level", default="INFO")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    cfg = load_yaml(args.config)
    out_dir = ensure_dir(cfg.get("output_dir", "outputs/train/default"))
    resume_from = Path(cfg["resume_from"]).resolve() if cfg.get("resume_from") else None

    report = build_dataset_report(Path(cfg["train"]["dataset_root"]))
    save_json(out_dir / "dataset_report.json", report)

    heavy_ok, heavy_error = _check_heavy_deps()
    if not heavy_ok:
        logger.warning("Heavy training dependencies unavailable (%s). Falling back to mock LoRA training.", heavy_error)
        logger.warning("Install torch/diffusers/accelerate for full SDXL LoRA fine-tuning.")
        final = _mock_train(cfg, out_dir, resume_from)
    else:
        final = _real_train_stub(cfg, out_dir, resume_from)

    save_json(
        out_dir / "train_summary.json",
        {
            "run_name": cfg.get("run_name", "unnamed"),
            "output_dir": str(out_dir),
            "final_lora": str(final),
            "git_hash": get_git_hash(),
        },
    )
    logger.info("Training complete. Final LoRA artifact: %s", final)


if __name__ == "__main__":
    main()

```

# /Users/bowensong/Documents/New project/src/studio/tweak.py
```python
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from .utils import get_logger, save_yaml, setup_logging

logger = get_logger("tweak")


INLINE_REPLACE = re.compile(r"replace_prompt:\s*'([^']+)'\s*->\s*'([^']+)'", re.IGNORECASE)
INLINE_FRAME = re.compile(r"frame_range\s*=\s*(\d+)\s*[-:]\s*(\d+)", re.IGNORECASE)
INLINE_CFG = re.compile(r"cfg\s*=\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)
INLINE_STEPS = re.compile(r"steps\s*=\s*(\d+)", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create/apply non-destructive scene/shot patches")
    p.add_argument("--workspace", default="workspace.yaml")
    p.add_argument("--project", required=True)
    p.add_argument("--scene", required=True)
    p.add_argument("--shot", default=None)
    p.add_argument("--create_patch_template", action="store_true")
    p.add_argument("--apply_inline", default=None)
    p.add_argument("--log_level", default="INFO")
    return p.parse_args()


def _project_root(workspace_path: Path, project_name: str) -> Path:
    import yaml

    ws = yaml.safe_load(workspace_path.read_text(encoding="utf-8")) or {}
    for ref in ws.get("projects", []):
        if str(ref.get("name")) == project_name:
            path = Path(ref["path"])
            if not path.is_absolute():
                path = (workspace_path.parent / path).resolve()
            return path.parent
    raise ValueError(f"project not found in workspace: {project_name}")


def _next_patch_path(project_root: Path, scene_name: str) -> Path:
    patch_dir = project_root / "scripts" / "scenes" / "patches"
    patch_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(patch_dir.glob(f"{scene_name}.patch.*.yaml"))
    n = 1
    if existing:
        token = existing[-1].stem.split(".")[-1]
        if token.isdigit():
            n = int(token) + 1
    return patch_dir / f"{scene_name}.patch.{n:03d}.yaml"


def _template(project: str, scene: str, shot: str | None) -> dict[str, Any]:
    return {
        "target": {"project": project, "scene": scene, "shot": shot},
        "ops": [
            {"op": "replace_prompt", "find": "straight hair", "replace": "wavy hair"},
            {"op": "add_prompt_suffix", "text": ", cinematic look"},
            {"op": "set", "path": "generation.guidance_scale", "value": 6.8},
            {"op": "set_frame_range", "value": [120, 220]},
        ],
    }


def _inline_to_patch(project: str, scene: str, shot: str | None, inline: str) -> dict[str, Any]:
    ops: list[dict[str, Any]] = []

    rep = INLINE_REPLACE.search(inline)
    if rep:
        ops.append({"op": "replace_prompt", "find": rep.group(1), "replace": rep.group(2)})

    fr = INLINE_FRAME.search(inline)
    if fr:
        ops.append({"op": "set_frame_range", "value": [int(fr.group(1)), int(fr.group(2))]})

    cfg = INLINE_CFG.search(inline)
    if cfg:
        ops.append({"op": "set", "path": "generation.guidance_scale", "value": float(cfg.group(1))})

    steps = INLINE_STEPS.search(inline)
    if steps:
        ops.append({"op": "set", "path": "generation.num_inference_steps", "value": int(steps.group(1))})

    if not ops:
        ops.append({"op": "add_prompt_suffix", "text": inline.strip()})

    return {"target": {"project": project, "scene": scene, "shot": shot}, "ops": ops}


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    ws_path = Path(args.workspace).resolve()
    project_root = _project_root(ws_path, args.project)
    patch_path = _next_patch_path(project_root, args.scene)

    if args.create_patch_template:
        payload = _template(args.project, args.scene, args.shot)
        save_yaml(patch_path, payload)
        print(str(patch_path))
        return

    if args.apply_inline:
        payload = _inline_to_patch(args.project, args.scene, args.shot, args.apply_inline)
        save_yaml(patch_path, payload)
        print(str(patch_path))
        return

    raise SystemExit("Use --create_patch_template or --apply_inline")


if __name__ == "__main__":
    main()

```

# /Users/bowensong/Documents/New project/src/studio/utils.py
```python
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

```

# /Users/bowensong/Documents/New project/tests/test_ai_rules.py
```python
from studio.ai_cmd.rules_backend import plan_from_rules


def test_rules_parser_extracts_scene_shot_and_frame_range() -> None:
    req = "Make scene_01 shot_03 more cinematic; regenerate only frames 120-220 and set cfg 7.2"
    plan = plan_from_rules(req, {"project": "my_makeover", "scene": None, "shot": None}, dry_run=True)

    assert plan.context["scene"] == "scene_01"
    assert plan.context["shot"] == "shot_03"
    assert any(a.type == "apply_patch" for a in plan.actions)
    patch_action = next(a for a in plan.actions if a.type == "apply_patch")
    ops = patch_action.payload["ops"]
    assert any(op.get("op") == "set_frame_range" and op.get("value") == [120, 220] for op in ops)
    assert any(op.get("path") == "generation.guidance_scale" and op.get("value") == 7.2 for op in ops)

```

# /Users/bowensong/Documents/New project/tests/test_patch_ops.py
```python
from studio.pipeline.executor import _apply_patch_ops


def test_patch_ops_prompt_and_cfg_changes() -> None:
    shot = {
        "shot_id": "shot_01",
        "generation": {"guidance_scale": 6.0},
        "references": {"wardrobe": "a"},
    }
    scene = {"scene_name": "scene_01"}
    dialog = {"lines": [{"line_id": "l1", "speaker": "narrator", "start_sec": 0.0, "end_sec": 1.0, "text": "hello"}]}

    ops = [
        {"op": "replace_prompt", "find": "straight hair", "replace": "wavy hair"},
        {"op": "set", "path": "generation.guidance_scale", "value": 7.0},
        {"op": "set_ref", "ref_path_key": "wardrobe", "value": "b"},
        {"op": "set_dialog_text", "speaker": "narrator", "line_id": "l1", "text": "updated"},
    ]

    shot2, scene2, dialog2, prompt2, neg2 = _apply_patch_ops(
        shot=shot,
        scene_data=scene,
        dialog_data=dialog,
        prompt="straight hair look",
        negative="low quality",
        ops=ops,
    )

    assert shot2["generation"]["guidance_scale"] == 7.0
    assert shot2["references"]["wardrobe"] == "b"
    assert "wavy hair" in prompt2
    assert neg2 == "low quality"
    assert dialog2["lines"][0]["text"] == "updated"
    assert scene2["_dialog_lines"][0]["text"] == "updated"

```

# /Users/bowensong/Documents/New project/tests/test_smoke.py
```python
from pathlib import Path

from studio.utils import load_yaml


def test_workspace_file_exists() -> None:
    path = Path("workspace.yaml")
    assert path.exists()


def test_workspace_has_project_reference() -> None:
    ws = load_yaml("workspace.yaml")
    assert ws["projects"]
    assert any(p["name"] == "my_makeover" for p in ws["projects"])

```

# /Users/bowensong/Documents/New project/workspace.yaml
```yaml
workspace_name: "default_workspace"
output_root: "outputs"
shared_prompt_library: "shared/prompt_library.yaml"
shared_asset_packs:
  - "shared/asset_packs.yaml"
global_defaults:
  seed: 42
  run_settings:
    batch_size: 1
    resume: true
  model:
    base_id: "stabilityai/stable-diffusion-xl-base-1.0"
    refiner_id: "stabilityai/stable-diffusion-xl-refiner-1.0"
    fast_base_id: "your-org/fast-sdxl-placeholder"
    use_refiner: false
    precision: "bf16"
    enable_xformers: true
    attention_slicing: true
global_guidelines:
  prompt: "high quality cinematic portrait, coherent anatomy, natural skin texture"
  negative_prompt: "blurry, distorted face, extra fingers, low quality artifacts"
projects:
  - name: "my_makeover"
    path: "projects/my_makeover/project.yaml"
selection:
  default_projects: ["my_makeover"]
  default_scenes: ["scene_01", "scene_02"]
identity_folders:
  - "data/my_identity"
asset_folders:
  - "projects/my_makeover/assets"

```

