#!/bin/bash
#SBATCH --job-name=train_identity_2gpu
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --gres=gpu:2
#SBATCH --mem=160G
#SBATCH --time=48:00:00
#SBATCH --output=logs/%x_%j.out

set -euo pipefail

export NCCL_DEBUG=INFO
export NCCL_IB_DISABLE=0
export NCCL_P2P_DISABLE=0
export NCCL_SOCKET_IFNAME=${NCCL_SOCKET_IFNAME:-"^lo,docker0"}
export PYTHONUNBUFFERED=1

CONFIG_PATH=${1:-configs/train/sdxl_lora.yaml}
RESUME_FROM=${RESUME_FROM:-""}

if [[ -n "${RESUME_FROM}" ]]; then
  python -m studio.train_identity --config "${CONFIG_PATH}" --log_level INFO
else
  python -m studio.train_identity --config "${CONFIG_PATH}" --log_level INFO
fi
