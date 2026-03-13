"""GPU allocation and scheduling with multi-GPU sharding support."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .discovery import GPUInfo

logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """Model types with known VRAM profiles."""

    SDXL_BASE = "sdxl_base"
    SDXL_REFINER = "sdxl_refiner"
    SDXL_LORA = "sdxl_lora"
    SDXL_CONTROLNET = "sdxl_controlnet"
    FLUX_DEV = "flux_dev"
    FLUX_PRO = "flux_pro"
    CLIP_VISION = "clip_vision"
    FACE_DETECTION = "face_detection"
    FACE_RECOGNITION = "face_recognition"
    UPSCALER = "upscaler"
    CUSTOM = "custom"


@dataclass
class ModelVRAMProfile:
    """VRAM requirements for a model."""

    model_type: ModelType
    vram_required_gb: float
    supports_sharding: bool = True
    max_batch_size: int = 1
    description: str = ""

    def __post_init__(self) -> None:
        """Validate profile."""
        if self.vram_required_gb <= 0:
            raise ValueError(f"Invalid VRAM requirement: {self.vram_required_gb}GB")
        if self.max_batch_size < 1:
            raise ValueError(f"Invalid max_batch_size: {self.max_batch_size}")


@dataclass
class GPUAllocation:
    """Result of allocating a task to GPU(s)."""

    task_id: str
    model_type: ModelType
    gpu_indices: list[int]
    vram_required_gb: float
    vram_allocated_gb: float
    uses_sharding: bool
    allocation_notes: str = ""

    @property
    def num_gpus(self) -> int:
        """Number of GPUs allocated."""
        return len(self.gpu_indices)

    def __repr__(self) -> str:
        sharding_str = " (sharded)" if self.uses_sharding else ""
        return (
            f"GPUAllocation(task={self.task_id}, model={self.model_type.value}, "
            f"gpus={self.gpu_indices}, alloc={self.vram_allocated_gb:.1f}GB{sharding_str})"
        )


@dataclass
class AllocationPlan:
    """Complete GPU allocation plan for a set of tasks."""

    allocations: list[GPUAllocation] = field(default_factory=list)
    failed_allocations: list[tuple[str, str]] = field(default_factory=list)
    summary: str = ""

    def is_feasible(self) -> bool:
        """Check if all tasks could be allocated."""
        return len(self.failed_allocations) == 0

    def total_vram_allocated_gb(self) -> float:
        """Total VRAM allocated across all successful allocations."""
        return sum(a.vram_allocated_gb for a in self.allocations)

    def __repr__(self) -> str:
        return (
            f"AllocationPlan(success={len(self.allocations)}, "
            f"failed={len(self.failed_allocations)}, "
            f"total_vram={self.total_vram_allocated_gb():.1f}GB)"
        )


class ModelVRAMRegistry:
    """Registry of known model VRAM profiles."""

    # Default profiles based on common models
    _DEFAULT_PROFILES: dict[ModelType, ModelVRAMProfile] = {
        ModelType.SDXL_BASE: ModelVRAMProfile(
            model_type=ModelType.SDXL_BASE,
            vram_required_gb=6.5,
            max_batch_size=1,
            description="SDXL Base 1.0 fp32",
        ),
        ModelType.SDXL_REFINER: ModelVRAMProfile(
            model_type=ModelType.SDXL_REFINER,
            vram_required_gb=4.5,
            max_batch_size=1,
            description="SDXL Refiner 1.0 fp32",
        ),
        ModelType.SDXL_LORA: ModelVRAMProfile(
            model_type=ModelType.SDXL_LORA,
            vram_required_gb=0.5,
            supports_sharding=False,
            description="SDXL LoRA adapter",
        ),
        ModelType.SDXL_CONTROLNET: ModelVRAMProfile(
            model_type=ModelType.SDXL_CONTROLNET,
            vram_required_gb=2.0,
            description="SDXL ControlNet adapter",
        ),
        ModelType.FLUX_DEV: ModelVRAMProfile(
            model_type=ModelType.FLUX_DEV,
            vram_required_gb=10.0,
            description="FLUX Dev (bf16)",
        ),
        ModelType.FLUX_PRO: ModelVRAMProfile(
            model_type=ModelType.FLUX_PRO,
            vram_required_gb=20.0,
            description="FLUX Pro (fp8 quantized)",
        ),
        ModelType.CLIP_VISION: ModelVRAMProfile(
            model_type=ModelType.CLIP_VISION,
            vram_required_gb=1.5,
            supports_sharding=False,
            description="CLIP Vision encoder",
        ),
        ModelType.FACE_DETECTION: ModelVRAMProfile(
            model_type=ModelType.FACE_DETECTION,
            vram_required_gb=0.3,
            supports_sharding=False,
            description="Face detection model",
        ),
        ModelType.FACE_RECOGNITION: ModelVRAMProfile(
            model_type=ModelType.FACE_RECOGNITION,
            vram_required_gb=0.5,
            supports_sharding=False,
            description="Face recognition/embedding model",
        ),
        ModelType.UPSCALER: ModelVRAMProfile(
            model_type=ModelType.UPSCALER,
            vram_required_gb=2.0,
            description="Image upscaler (typically RealESRGAN)",
        ),
    }

    def __init__(self) -> None:
        """Initialize with default profiles."""
        self.profiles: dict[ModelType, ModelVRAMProfile] = self._DEFAULT_PROFILES.copy()

    def register(self, profile: ModelVRAMProfile) -> None:
        """Register a model VRAM profile."""
        self.profiles[profile.model_type] = profile
        logger.debug(
            f"Registered VRAM profile: {profile.model_type.value} "
            f"({profile.vram_required_gb}GB)"
        )

    def get(self, model_type: ModelType) -> ModelVRAMProfile:
        """Get VRAM profile for a model type."""
        if model_type not in self.profiles:
            raise KeyError(f"No VRAM profile registered for {model_type.value}")
        return self.profiles[model_type]

    def get_or_default(self, model_type: ModelType, default_gb: float = 4.0) -> ModelVRAMProfile:
        """Get VRAM profile or return a default."""
        if model_type in self.profiles:
            return self.profiles[model_type]
        logger.warning(
            f"No VRAM profile for {model_type.value}, using default {default_gb}GB"
        )
        return ModelVRAMProfile(
            model_type=model_type, vram_required_gb=default_gb, description="default"
        )

    def list_profiles(self) -> list[ModelVRAMProfile]:
        """List all registered profiles."""
        return list(self.profiles.values())


class GPUAllocator:
    """Allocate GPU resources to models/tasks."""

    def __init__(self, vram_registry: Optional[ModelVRAMRegistry] = None) -> None:
        """Initialize allocator with optional custom registry."""
        self.vram_registry = vram_registry or ModelVRAMRegistry()
        self._allocations: dict[str, GPUAllocation] = {}

    def allocate(
        self,
        task_id: str,
        model_type: ModelType,
        gpus: list[GPUInfo],
        custom_vram_gb: Optional[float] = None,
    ) -> GPUAllocation:
        """
        Allocate GPUs for a task.

        Args:
            task_id: Unique task identifier
            model_type: Type of model to run
            gpus: Available GPUs to choose from
            custom_vram_gb: Override default VRAM requirement

        Returns:
            GPUAllocation with assigned GPU(s)

        Raises:
            ValueError: If allocation is not feasible
        """
        if not gpus:
            raise ValueError("No GPUs available for allocation")

        # Get VRAM requirement
        profile = self.vram_registry.get_or_default(model_type)
        vram_required = custom_vram_gb or profile.vram_required_gb

        # Try best-fit allocation
        allocation = self._best_fit_allocation(
            task_id=task_id,
            model_type=model_type,
            vram_required=vram_required,
            gpus=gpus,
            supports_sharding=profile.supports_sharding,
        )

        if not allocation:
            raise ValueError(
                f"Cannot allocate {vram_required}GB for {model_type.value} "
                f"(best available: {max(g.vram_free_gb for g in gpus):.1f}GB)"
            )

        self._allocations[task_id] = allocation
        logger.info(f"Allocated: {allocation}")

        return allocation

    def plan_allocations(
        self,
        tasks: list[tuple[str, ModelType, Optional[float]]],
        gpus: list[GPUInfo],
    ) -> AllocationPlan:
        """
        Create an allocation plan for multiple tasks.

        Args:
            tasks: List of (task_id, model_type, optional_vram_gb) tuples
            gpus: Available GPUs

        Returns:
            AllocationPlan with results for all tasks
        """
        plan = AllocationPlan()
        allocated_gpus = self._copy_gpu_states(gpus)

        for task_id, model_type, custom_vram_gb in tasks:
            try:
                profile = self.vram_registry.get_or_default(model_type)
                vram_required = custom_vram_gb or profile.vram_required_gb

                allocation = self._best_fit_allocation(
                    task_id=task_id,
                    model_type=model_type,
                    vram_required=vram_required,
                    gpus=allocated_gpus,
                    supports_sharding=profile.supports_sharding,
                )

                if allocation:
                    plan.allocations.append(allocation)
                    # Update GPU states
                    for gpu_idx in allocation.gpu_indices:
                        allocated_gpus[gpu_idx].vram_free_mb -= allocation.vram_allocated_gb * 1024
                else:
                    plan.failed_allocations.append(
                        (task_id, f"Insufficient VRAM for {model_type.value}")
                    )

            except Exception as e:
                plan.failed_allocations.append((task_id, str(e)))

        # Generate summary
        total_allocated = plan.total_vram_allocated_gb()
        plan.summary = (
            f"Allocated {len(plan.allocations)}/{len(tasks)} tasks, "
            f"{total_allocated:.1f}GB VRAM used"
        )

        logger.info(plan.summary)
        return plan

    def deallocate(self, task_id: str) -> bool:
        """Remove allocation for a task."""
        if task_id in self._allocations:
            allocation = self._allocations.pop(task_id)
            logger.info(f"Deallocated: {allocation}")
            return True
        return False

    def get_allocation(self, task_id: str) -> Optional[GPUAllocation]:
        """Get allocation for a task."""
        return self._allocations.get(task_id)

    def get_allocations(self) -> dict[str, GPUAllocation]:
        """Get all current allocations."""
        return self._allocations.copy()

    @staticmethod
    def _copy_gpu_states(gpus: list[GPUInfo]) -> list[GPUInfo]:
        """Create mutable copies of GPU states for planning."""
        import copy

        return [copy.copy(gpu) for gpu in gpus]

    def _best_fit_allocation(
        self,
        task_id: str,
        model_type: ModelType,
        vram_required: float,
        gpus: list[GPUInfo],
        supports_sharding: bool,
    ) -> Optional[GPUAllocation]:
        """
        Find best GPU(s) for a task using best-fit algorithm.

        Priority: Single GPU (no sharding overhead), then multi-GPU sharding.
        """
        # Sort by free VRAM descending
        sorted_gpus = sorted(gpus, key=lambda g: g.vram_free_gb, reverse=True)

        # Try single GPU allocation first
        for gpu in sorted_gpus:
            if gpu.vram_free_gb >= vram_required:
                return GPUAllocation(
                    task_id=task_id,
                    model_type=model_type,
                    gpu_indices=[gpu.index],
                    vram_required_gb=vram_required,
                    vram_allocated_gb=vram_required,
                    uses_sharding=False,
                )

        # Try multi-GPU sharding if supported
        if supports_sharding and len(sorted_gpus) > 1:
            # Greedy multi-GPU packing
            selected_gpus: list[GPUInfo] = []
            allocated_vram = 0.0

            for gpu in sorted_gpus:
                if allocated_vram >= vram_required:
                    break
                selected_gpus.append(gpu)
                allocated_vram += gpu.vram_free_gb

            if allocated_vram >= vram_required:
                return GPUAllocation(
                    task_id=task_id,
                    model_type=model_type,
                    gpu_indices=[g.index for g in selected_gpus],
                    vram_required_gb=vram_required,
                    vram_allocated_gb=allocated_vram,
                    uses_sharding=True,
                    allocation_notes=f"Sharded across {len(selected_gpus)} GPUs",
                )

        return None
