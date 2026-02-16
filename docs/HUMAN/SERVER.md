# Server

`studio.server` exposes HTTP APIs for orchestration and model sync.

Start server:
```bash
python -m studio.server --config configs/server/default.yaml
```

Core endpoints:
- `GET /health`
- `POST /run`
- `POST /ai/plan`
- `POST /ai/execute`
- `GET /models`
- `POST /models/pull`
- `POST /models/push`

Model sources supported:
- Hugging Face repo IDs (e.g., `stabilityai/stable-diffusion-xl-base-1.0`)
- local paths

Model targets for push:
- Hugging Face repo ID
- local destination path
