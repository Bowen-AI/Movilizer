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
