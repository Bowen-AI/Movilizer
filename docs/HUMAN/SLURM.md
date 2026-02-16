# Slurm

Provided scripts:
- `slurm/train_identity_2gpu.sbatch`
- `slurm/run_studio_2gpu.sbatch`
- `slurm/eval.sbatch`
- `slurm/evolve.sbatch`

All scripts:
- request 2 GPUs
- set NCCL environment variables
- log to `logs/%x_%j.out`
- support workspace/project/scene args
- support resume flags

Recommended movie run:
```bash
sbatch --export=WORKSPACE_PATH=workspace.yaml,PROJECTS=feature_film_demo,SCENES=all,RESUME_FLAG=1 slurm/run_studio_2gpu.sbatch
```

Override profile with `RUN_CONFIG`, for example `configs/run/local_debug.yaml`.
