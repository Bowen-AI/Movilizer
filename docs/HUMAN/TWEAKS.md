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
