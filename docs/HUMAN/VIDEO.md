# Video

Generation methods:
- `image_only`
- `keyframes_to_video`
- `video_plugin` (native stub included)

Assembly chain:
- `frames/` -> `clip.mp4` per shot
- shot clips -> `scene.mp4`
- scene clips -> `final.mp4`

Consistency controls:
- seed locking
- anchor frames
- prompt schedule by frame index
- merged prompt media references (images/videos)
- per-shot metadata with provenance

Debug profile:
- use `configs/run/local_debug.yaml` for fast local iteration
