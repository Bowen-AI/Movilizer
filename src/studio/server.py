from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from .ai_cmd.planner import build_plan, execute_plan
from .models.registry import list_local_models, pull_model, push_model, write_model_registry_index
from .utils import load_yaml, setup_logging


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Studio API server")
    p.add_argument("--config", default="configs/server/default.yaml")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    p.add_argument("--log_level", default="INFO")
    return p.parse_args()


def _run_subprocess(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    cfg = load_yaml(args.config) if Path(args.config).exists() else {}
    host = args.host or str(cfg.get("host", "127.0.0.1"))
    port = int(args.port or int(cfg.get("port", 8080)))
    workspace = Path(cfg.get("workspace", "workspace.yaml")).resolve()
    ai_backend = str(cfg.get("ai_backend", "rules"))
    model_cache = Path(cfg.get("model_cache", "models/cache")).resolve()

    try:
        from fastapi import FastAPI
        from pydantic import BaseModel, Field
        import uvicorn
    except Exception as exc:
        raise SystemExit(
            "FastAPI server dependencies missing. Install: pip install fastapi uvicorn pydantic\n"
            f"Import error: {exc}"
        )

    app = FastAPI(title="Movilizer Studio Server", version="0.2.0")

    class RunRequest(BaseModel):
        workspace_path: str | None = None
        projects: list[str] = Field(default_factory=lambda: ["all"])
        scenes: list[str] = Field(default_factory=lambda: ["all"])
        shots: list[str] = Field(default_factory=list)
        patches: list[str] = Field(default_factory=list)
        compile_only: bool = False
        resume: bool = True
        dry_run: bool = False
        run_id: str | None = None
        run_config: str | None = None

    class PlanRequest(BaseModel):
        request: str
        project: str | None = None
        scene: str | None = None
        shot: str | None = None
        dry_run: bool = True
        backend: str | None = None

    class PlanExecuteRequest(BaseModel):
        request: str
        project: str | None = None
        scene: str | None = None
        shot: str | None = None
        dry_run: bool = False
        yes: bool = True
        run_id: str | None = None
        backend: str | None = None

    class PullModelRequest(BaseModel):
        source: str
        revision: str | None = None
        local_files_only: bool = False

    class PushModelRequest(BaseModel):
        source_dir: str
        target: str
        private: bool = False

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "workspace": str(workspace),
            "model_cache": str(model_cache),
            "ai_backend": ai_backend,
        }

    @app.post("/run")
    def run_job(req: RunRequest) -> dict[str, Any]:
        ws = Path(req.workspace_path).resolve() if req.workspace_path else workspace
        cmd = ["python", "-m", "studio.run", "--workspace", str(ws)]

        if req.projects:
            if len(req.projects) == 1 and req.projects[0] != "all":
                cmd += ["--project", req.projects[0]]
            else:
                cmd += ["--projects", *req.projects]

        if req.scenes:
            if len(req.scenes) == 1 and req.scenes[0] != "all":
                cmd += ["--scene", req.scenes[0]]
            else:
                cmd += ["--scenes", *req.scenes]

        for shot in req.shots:
            cmd += ["--shot", shot]

        for patch in req.patches:
            cmd += ["--patch", patch]

        if req.compile_only:
            cmd.append("--compile_only")
        if req.resume:
            cmd.append("--resume")
        if req.dry_run:
            cmd.append("--dry_run")
        if req.run_id:
            cmd += ["--run_id", req.run_id]
        if req.run_config:
            cmd += ["--run_config", req.run_config]

        return _run_subprocess(cmd)

    @app.post("/ai/plan")
    def ai_plan(req: PlanRequest) -> dict[str, Any]:
        backend = req.backend or ai_backend
        plan = build_plan(
            request=req.request,
            context={"project": req.project, "scene": req.scene, "shot": req.shot},
            backend=backend,
            backend_config=load_yaml("configs/ai_cmd/default.yaml") if Path("configs/ai_cmd/default.yaml").exists() else {},
            dry_run=req.dry_run,
        )
        return plan.to_dict()

    @app.post("/ai/execute")
    def ai_execute(req: PlanExecuteRequest) -> dict[str, Any]:
        backend = req.backend or ai_backend
        ai_cfg = load_yaml("configs/ai_cmd/default.yaml") if Path("configs/ai_cmd/default.yaml").exists() else {}
        plan = build_plan(
            request=req.request,
            context={"project": req.project, "scene": req.scene, "shot": req.shot},
            backend=backend,
            backend_config=ai_cfg,
            dry_run=req.dry_run,
        )
        result = execute_plan(
            plan=plan,
            workspace_path=workspace,
            yes=req.yes,
            dry_run=req.dry_run,
            run_id=req.run_id,
        )
        return {"plan": plan.to_dict(), "result": result}

    @app.get("/models")
    def list_models() -> dict[str, Any]:
        return {
            "cache_root": str(model_cache),
            "models": list_local_models(model_cache),
        }

    @app.post("/models/pull")
    def pull(req: PullModelRequest) -> dict[str, Any]:
        result = pull_model(
            source=req.source,
            revision=req.revision,
            local_files_only=req.local_files_only,
            cache_root=model_cache,
        )
        write_model_registry_index(model_cache)
        return result.__dict__

    @app.post("/models/push")
    def push(req: PushModelRequest) -> dict[str, Any]:
        result = push_model(
            source_dir=req.source_dir,
            target=req.target,
            private=req.private,
        )
        write_model_registry_index(model_cache)
        return result.__dict__

    @app.get("/commands")
    def commands() -> dict[str, Any]:
        commands_path = Path("docs/AI/COMMANDS.md")
        content = commands_path.read_text(encoding="utf-8") if commands_path.exists() else ""
        return {"commands_md": content}

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
