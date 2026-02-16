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
