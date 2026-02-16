# Troubleshooting

## ffmpeg missing
Install ffmpeg and rerun. Without ffmpeg, MP4 creation falls back to warning files.

## Heavy ML dependencies missing
`studio.train_identity` and advanced judges degrade gracefully.
Install optional packages from `requirements.txt` for full capability.

## Empty outputs
Check project/scene selection flags and ensure `scene_files` exist in `project.yaml`.

## Cache confusion
Use a new `--run_id` or disable resume behavior by omitting `--resume`.
