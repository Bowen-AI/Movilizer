#!/bin/bash
#SBATCH --job-name=run_studio_2gpu
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --gres=gpu:2
#SBATCH --mem=160G
#SBATCH --time=24:00:00
#SBATCH --output=logs/%x_%j.out

set -euo pipefail

export NCCL_DEBUG=INFO
export NCCL_IB_DISABLE=0
export NCCL_P2P_DISABLE=0
export NCCL_SOCKET_IFNAME=${NCCL_SOCKET_IFNAME:-"^lo,docker0"}
export PYTHONUNBUFFERED=1

WORKSPACE_PATH=${WORKSPACE_PATH:-workspace.yaml}
PROJECTS=${PROJECTS:-all}
SCENES=${SCENES:-all}
RUN_ID=${RUN_ID:-""}
RESUME_FLAG=${RESUME_FLAG:-1}
RUN_CONFIG=${RUN_CONFIG:-configs/run/default_run.yaml}

CMD=(python -m studio.run --workspace "${WORKSPACE_PATH}" --run_config "${RUN_CONFIG}")

if [[ "${PROJECTS}" == "all" ]]; then
  CMD+=(--projects all)
else
  CMD+=(--projects ${PROJECTS})
fi

if [[ "${SCENES}" == "all" ]]; then
  CMD+=(--scenes all)
else
  CMD+=(--scenes ${SCENES})
fi

if [[ -n "${RUN_ID}" ]]; then
  CMD+=(--run_id "${RUN_ID}")
fi

if [[ "${RESUME_FLAG}" == "1" ]]; then
  CMD+=(--resume)
fi

"${CMD[@]}"
