# Pipeline

Execution DAG per shot/scene:
1. optional model resolution (local/HF -> cache)
2. compile scene + shot + prompt-media merge
3. apply patches
4. generate frames
5. assemble shot clip
6. assemble scene video
7. render dialog track
8. render/select music track
9. mix final audio
10. mux scene video + audio
11. concat scenes into project final
12. evaluate judges

Caching/resume:
- deterministic signatures per task
- skip unchanged tasks
- if only audio changes, frame generation is skipped
- frame-range patches regenerate only selected frames and reassemble clip

Run profiles:
- `configs/run/default_run.yaml` for normal mode
- `configs/run/local_debug.yaml` for fast local debugging
