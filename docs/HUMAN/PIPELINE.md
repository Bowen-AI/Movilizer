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
