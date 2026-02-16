#!/bin/bash
#SBATCH --job-name=eval_studio
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:2
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --output=logs/%x_%j.out

set -euo pipefail

export NCCL_DEBUG=INFO
export NCCL_SOCKET_IFNAME=${NCCL_SOCKET_IFNAME:-"^lo,docker0"}
export PYTHONUNBUFFERED=1

WORKSPACE_PATH=${WORKSPACE_PATH:-workspace.yaml}
RUN_ID=${RUN_ID:?RUN_ID environment variable is required}

python -m studio.eval --workspace "${WORKSPACE_PATH}" --run_id "${RUN_ID}"
