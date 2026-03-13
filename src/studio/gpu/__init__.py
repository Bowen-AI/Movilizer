"""GPU resource management and allocation system."""

from __future__ import annotations

from .allocator import (
    AllocationPlan,
    GPUAllocation,
    GPUAllocator,
    ModelType,
    ModelVRAMProfile,
    ModelVRAMRegistry,
)
from .discovery import GPUDiscovery, GPUInfo
from .monitor import (
    GPUMetrics,
    GPUMonitor,
    HealthReport,
    MetricsBuffer,
    MonitoredGPUCluster,
)

__all__ = [
    # Discovery
    "GPUInfo",
    "GPUDiscovery",
    # Allocation
    "ModelType",
    "ModelVRAMProfile",
    "ModelVRAMRegistry",
    "GPUAllocation",
    "AllocationPlan",
    "GPUAllocator",
    # Monitoring
    "GPUMetrics",
    "MetricsBuffer",
    "HealthReport",
    "GPUMonitor",
    "MonitoredGPUCluster",
]
