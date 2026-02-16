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
