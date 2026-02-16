# Scenes

A scene YAML defines scene-level vibe and a list of shots.

Scene-level movie fields:
- `vibe_overrides`
- `prompt_media.images[]` / `prompt_media.videos[]`
- location and wardrobe references
- dialog reference

Shot fields:
- timing: `duration`, `fps`, `resolution`
- cinematic intent: `camera`, `lens`, `lighting`
- prompt controls: `prompt`, `negative_prompt`
- generation method: `image_only`, `keyframes_to_video`, `video_plugin`
- references + multi media refs:
  - `references.prompt_images[]`
  - `references.prompt_videos[]`
  - optional `prompt_media` at shot level
- `actors`: tokens like `<lead_actor>`, `<antagonist>`

Prompt media is merged from workspace -> project -> scene -> shot.
