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
