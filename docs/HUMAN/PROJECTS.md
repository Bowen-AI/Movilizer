# Projects

Each project lives under `projects/<name>/` and must include `project.yaml`.

Use movie-generic naming and avoid personal hardcoding in prompts/configs.

Required sections:
- `identity_packs`: one or more identity datasets.
- `model`: base/refiner source IDs + optional `model_sources` and LoRAs.
- `style_bible`: cinematic vibe and continuity rules.
- `safety_policy`: generation constraints.
- `output_specs`: resolution/fps/loudness.
- `scene_files`: explicit scene YAML paths.

Optional sections:
- `prompt_media.images[]` and `prompt_media.videos[]`
- `assets.identity_folders[]` and `assets.asset_folders[]`

`workspace.yaml` can register multiple projects and run them in one batch.
