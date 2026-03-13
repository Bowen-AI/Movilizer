"""GPU discovery via nvidia-smi, torch.cuda, and optional pynvml."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class GPUInfo:
    """Immutable GPU information snapshot."""

    index: int
    name: str
    uuid: str
    vram_total_gb: float
    vram_used_mb: float
    vram_free_mb: float
    compute_capability_major: int
    compute_capability_minor: int
    power_draw_w: Optional[float] = None
    power_limit_w: Optional[float] = None
    temperature_c: Optional[float] = None

    @property
    def vram_used_gb(self) -> float:
        """GPU VRAM used in GB."""
        return self.vram_used_mb / 1024.0

    @property
    def vram_free_gb(self) -> float:
        """GPU VRAM free in GB."""
        return self.vram_free_mb / 1024.0

    @property
    def vram_utilization_pct(self) -> float:
        """GPU VRAM utilization as percentage."""
        if self.vram_total_gb <= 0:
            return 0.0
        return (self.vram_used_gb / self.vram_total_gb) * 100.0

    @property
    def is_a100_80gb(self) -> bool:
        """Check if this is an A100 80GB."""
        return "A100" in self.name and self.vram_total_gb >= 79.0

    @property
    def is_a100_40gb(self) -> bool:
        """Check if this is an A100 40GB."""
        return "A100" in self.name and self.vram_total_gb >= 39.0 and self.vram_total_gb < 79.0

    def __repr__(self) -> str:
        return (
            f"GPUInfo(idx={self.index}, name={self.name}, "
            f"vram={self.vram_total_gb:.1f}GB, "
            f"used={self.vram_used_gb:.1f}GB, "
            f"compute={self.compute_capability_major}.{self.compute_capability_minor})"
        )


class GPUDiscovery:
    """Discover and interrogate available GPU resources."""

    def __init__(self) -> None:
        """Initialize GPU discovery with fallback chain."""
        self._nvidia_smi_path = self._find_nvidia_smi()
        self._has_torch_cuda = self._check_torch_cuda()
        self._has_pynvml = self._check_pynvml()

    @staticmethod
    def _find_nvidia_smi() -> Optional[str]:
        """Find nvidia-smi executable in PATH."""
        import shutil

        path = shutil.which("nvidia-smi")
        if path:
            logger.debug(f"Found nvidia-smi at {path}")
            return path
        logger.debug("nvidia-smi not found in PATH")
        return None

    @staticmethod
    def _check_torch_cuda() -> bool:
        """Check if torch with CUDA support is available."""
        try:
            import torch

            has_cuda = torch.cuda.is_available()
            if has_cuda:
                logger.debug(f"torch.cuda available ({torch.__version__})")
            return has_cuda
        except ImportError:
            logger.debug("torch not installed")
            return False
        except Exception as e:
            logger.debug(f"torch.cuda check failed: {e}")
            return False

    @staticmethod
    def _check_pynvml() -> bool:
        """Check if pynvml is available."""
        try:
            import pynvml

            pynvml.nvmlInit()
            logger.debug(f"pynvml available ({pynvml.__version__})")
            return True
        except ImportError:
            logger.debug("pynvml not installed")
            return False
        except Exception as e:
            logger.debug(f"pynvml init failed: {e}")
            return False

    def get_gpus(self) -> list[GPUInfo]:
        """
        Discover all available GPUs.

        Returns list of GPUInfo, trying multiple methods in order:
        1. nvidia-smi (most reliable, works without Python deps)
        2. torch.cuda (requires PyTorch)
        3. pynvml (requires pynvml)
        """
        # Try nvidia-smi first (most robust)
        if self._nvidia_smi_path:
            try:
                gpus = self._discover_via_nvidia_smi()
                if gpus:
                    logger.info(f"Discovered {len(gpus)} GPU(s) via nvidia-smi")
                    return gpus
            except Exception as e:
                logger.warning(f"nvidia-smi discovery failed: {e}")

        # Try torch.cuda second
        if self._has_torch_cuda:
            try:
                gpus = self._discover_via_torch_cuda()
                if gpus:
                    logger.info(f"Discovered {len(gpus)} GPU(s) via torch.cuda")
                    return gpus
            except Exception as e:
                logger.warning(f"torch.cuda discovery failed: {e}")

        # Try pynvml third
        if self._has_pynvml:
            try:
                gpus = self._discover_via_pynvml()
                if gpus:
                    logger.info(f"Discovered {len(gpus)} GPU(s) via pynvml")
                    return gpus
            except Exception as e:
                logger.warning(f"pynvml discovery failed: {e}")

        logger.warning("No GPUs discovered - no discovery method available")
        return []

    def _discover_via_nvidia_smi(self) -> list[GPUInfo]:
        """Discover GPUs using nvidia-smi subprocess."""
        if not self._nvidia_smi_path:
            return []

        try:
            # Query GPU info via nvidia-smi JSON output
            output = subprocess.check_output(
                [
                    self._nvidia_smi_path,
                    "--query-gpu=index,name,uuid,memory.total,memory.used,memory.free,compute_cap,power.draw,power.limit,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                text=True,
                timeout=10,
            )

            gpus: list[GPUInfo] = []
            for line in output.strip().split("\n"):
                if not line.strip():
                    continue

                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 7:
                    logger.warning(f"Unexpected nvidia-smi output: {line}")
                    continue

                try:
                    index = int(parts[0])
                    name = parts[1]
                    uuid = parts[2]

                    # Memory in MB
                    vram_total_mb = float(parts[3])
                    vram_used_mb = float(parts[4])
                    vram_free_mb = float(parts[5])

                    # Compute capability e.g. "8.0"
                    compute_cap_str = parts[6]
                    compute_cap = tuple(map(int, compute_cap_str.split(".")))
                    compute_capability_major = compute_cap[0]
                    compute_capability_minor = compute_cap[1]

                    # Optional power and temperature
                    power_draw_w = None
                    power_limit_w = None
                    temperature_c = None

                    if len(parts) > 7 and parts[7]:
                        try:
                            power_draw_w = float(parts[7])
                        except ValueError:
                            pass

                    if len(parts) > 8 and parts[8]:
                        try:
                            power_limit_w = float(parts[8])
                        except ValueError:
                            pass

                    if len(parts) > 9 and parts[9]:
                        try:
                            temperature_c = float(parts[9])
                        except ValueError:
                            pass

                    gpu = GPUInfo(
                        index=index,
                        name=name,
                        uuid=uuid,
                        vram_total_gb=vram_total_mb / 1024.0,
                        vram_used_mb=vram_used_mb,
                        vram_free_mb=vram_free_mb,
                        compute_capability_major=compute_capability_major,
                        compute_capability_minor=compute_capability_minor,
                        power_draw_w=power_draw_w,
                        power_limit_w=power_limit_w,
                        temperature_c=temperature_c,
                    )
                    gpus.append(gpu)
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse nvidia-smi line: {line} - {e}")

            return gpus

        except subprocess.TimeoutExpired:
            logger.error("nvidia-smi query timed out")
            return []
        except subprocess.CalledProcessError as e:
            logger.error(f"nvidia-smi failed: {e}")
            return []
        except Exception as e:
            logger.error(f"nvidia-smi discovery error: {e}")
            return []

    def _discover_via_torch_cuda(self) -> list[GPUInfo]:
        """Discover GPUs using torch.cuda."""
        if not self._has_torch_cuda:
            return []

        try:
            import torch

            num_gpus = torch.cuda.device_count()
            if num_gpus == 0:
                return []

            gpus: list[GPUInfo] = []
            for idx in range(num_gpus):
                try:
                    name = torch.cuda.get_device_name(idx)

                    # Get compute capability
                    capability = torch.cuda.get_device_capability(idx)
                    compute_capability_major = capability[0]
                    compute_capability_minor = capability[1]

                    # Get memory info
                    total_memory = torch.cuda.get_device_properties(idx).total_memory
                    vram_total_gb = total_memory / (1024**3)

                    # Get current utilization (may be 0 if not queried via nvidia-smi)
                    try:
                        reserved = torch.cuda.memory_reserved(idx)
                        allocated = torch.cuda.memory_allocated(idx)
                        vram_used_mb = (allocated / (1024**2)) if allocated > 0 else 0.0
                        vram_free_mb = (
                            (total_memory - reserved) / (1024**2)
                            if reserved < total_memory
                            else 0.0
                        )
                    except RuntimeError:
                        vram_used_mb = 0.0
                        vram_free_mb = (total_memory / (1024**2))

                    # Generate a UUID (torch doesn't provide one, use synthetic)
                    uuid = f"torch-cuda-{idx}"

                    gpu = GPUInfo(
                        index=idx,
                        name=name,
                        uuid=uuid,
                        vram_total_gb=vram_total_gb,
                        vram_used_mb=vram_used_mb,
                        vram_free_mb=vram_free_mb,
                        compute_capability_major=compute_capability_major,
                        compute_capability_minor=compute_capability_minor,
                    )
                    gpus.append(gpu)

                except Exception as e:
                    logger.warning(f"Failed to query GPU {idx} via torch: {e}")

            return gpus

        except Exception as e:
            logger.error(f"torch.cuda discovery error: {e}")
            return []

    def _discover_via_pynvml(self) -> list[GPUInfo]:
        """Discover GPUs using pynvml."""
        if not self._has_pynvml:
            return []

        try:
            import pynvml

            device_count = pynvml.nvmlDeviceGetCount()
            if device_count == 0:
                return []

            gpus: list[GPUInfo] = []
            for idx in range(device_count):
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(idx)
                    name = pynvml.nvmlDeviceGetName(handle)
                    uuid = pynvml.nvmlDeviceGetUUID(handle)

                    # Memory info
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    vram_total_gb = mem_info.total / (1024**3)
                    vram_used_mb = mem_info.used / (1024**2)
                    vram_free_mb = mem_info.free / (1024**2)

                    # Compute capability
                    major, minor = pynvml.nvmlDeviceGetComputeCapability(handle)

                    # Optional power and temperature
                    power_draw_w = None
                    power_limit_w = None
                    temperature_c = None

                    try:
                        power_draw_w = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
                    except pynvml.NVMLError:
                        pass

                    try:
                        power_limit_w = pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000.0
                    except pynvml.NVMLError:
                        pass

                    try:
                        temperature_c = float(pynvml.nvmlDeviceGetTemperature(handle, 0))
                    except pynvml.NVMLError:
                        pass

                    gpu = GPUInfo(
                        index=idx,
                        name=name,
                        uuid=uuid,
                        vram_total_gb=vram_total_gb,
                        vram_used_mb=vram_used_mb,
                        vram_free_mb=vram_free_mb,
                        compute_capability_major=major,
                        compute_capability_minor=minor,
                        power_draw_w=power_draw_w,
                        power_limit_w=power_limit_w,
                        temperature_c=temperature_c,
                    )
                    gpus.append(gpu)

                except Exception as e:
                    logger.warning(f"Failed to query GPU {idx} via pynvml: {e}")

            return gpus

        except Exception as e:
            logger.error(f"pynvml discovery error: {e}")
            return []
