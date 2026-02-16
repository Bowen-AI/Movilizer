# Troubleshooting

## ffmpeg missing
Install ffmpeg (`conda install -c conda-forge ffmpeg`) and rerun.

## Server won't start
Install server deps:
```bash
pip install fastapi uvicorn pydantic
```
Then run:
```bash
python -m studio.server --config configs/server/default.yaml
```

## Hugging Face model pull/push fails
- Install `huggingface_hub`.
- Ensure network access.
- Set token when pushing private repos:
```bash
export HF_TOKEN=...
```

## Heavy ML dependencies missing
`studio.train_identity` and advanced judges degrade gracefully.
Install optional packages from `requirements.txt` for full capability.

## Cache confusion
Use a new `--run_id` or omit `--resume`.

## Need a fast debug run
Use:
```bash
python -m studio.run --workspace workspace.yaml --run_config configs/run/local_debug.yaml --projects feature_film_demo --scenes all
```
