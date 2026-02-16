# Tweaks (Patch System)

Patch files are non-destructive overlays:
- `projects/<proj>/scripts/scenes/patches/<scene>.patch.<N>.yaml`

Supported operations:
- structure ops: `set`, `delete`, `append`, `extend`, `set_ref`, `set_frame_range`
- prompt ops: `replace_prompt`, `add_prompt_prefix/suffix`, `add_negative_prefix/suffix`
- audio ops: `set_dialog_text`, `shift_dialog_time`, `replace_music`

Examples:
```bash
python -m studio.tweak --workspace workspace.yaml --project feature_film_demo --scene scene_001_opening --create_patch_template
python -m studio.tweak --workspace workspace.yaml --project feature_film_demo --scene scene_001_opening --shot shot_001 --apply_inline "replace_prompt: 'street' -> 'rain-soaked street'"
python -m studio.run --workspace workspace.yaml --project feature_film_demo --scene scene_001_opening --patch projects/feature_film_demo/scripts/scenes/patches/scene_001_opening.patch.001.yaml
```
