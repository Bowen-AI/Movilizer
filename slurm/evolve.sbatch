#!/bin/bash
#SBATCH --job-name=evolve_studio
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --gres=gpu:2
#SBATCH --mem=96G
#SBATCH --time=24:00:00
#SBATCH --output=logs/%x_%j.out

set -euo pipefail

export NCCL_DEBUG=INFO
export NCCL_SOCKET_IFNAME=${NCCL_SOCKET_IFNAME:-"^lo,docker0"}
export PYTHONUNBUFFERED=1

WORKSPACE_PATH=${WORKSPACE_PATH:-workspace.yaml}
PROJECTS=${PROJECTS:-my_makeover}
BUDGET=${BUDGET:-small}
RESUME_FLAG=${RESUME_FLAG:-1}

CMD=(python -m studio.evolve --workspace "${WORKSPACE_PATH}" --projects ${PROJECTS} --budget "${BUDGET}")
if [[ "${RESUME_FLAG}" == "1" ]]; then
  CMD+=(--resume)
fi

"${CMD[@]}"
