#!/usr/bin/env python
"""
Example: GPU Resource Management System Usage

This demonstrates how to use the GPU resource management system
for the Movilizer AI movie studio.
"""

from __future__ import annotations

import time
from src.studio.gpu import (
    GPUDiscovery,
    GPUAllocator,
    ModelType,
    ModelVRAMProfile,
    MonitoredGPUCluster,
)
from src.studio.utils import setup_logging, get_logger

logger = get_logger("gpu_example")


def example_discovery() -> None:
    """Example 1: Discover available GPUs."""
    print("\n" + "=" * 60)
    print("Example 1: GPU Discovery")
    print("=" * 60)

    discovery = GPUDiscovery()
    gpus = discovery.get_gpus()

    if not gpus:
        print("No GPUs found")
        return

    print(f"\nFound {len(gpus)} GPU(s):\n")
    for gpu in gpus:
        print(f"  GPU {gpu.index}: {gpu.name}")
        print(f"    UUID: {gpu.uuid}")
        print(f"    VRAM: {gpu.vram_total_gb:.1f}GB")
        print(f"      Used: {gpu.vram_used_gb:.1f}GB")
        print(f"      Free: {gpu.vram_free_gb:.1f}GB")
        print(f"      Utilization: {gpu.vram_utilization_pct:.1f}%")
        print(f"    Compute Capability: {gpu.compute_capability_major}.{gpu.compute_capability_minor}")
        if gpu.temperature_c:
            print(f"    Temperature: {gpu.temperature_c:.1f}°C")
        print()


def example_allocation() -> None:
    """Example 2: Allocate GPUs to models."""
    print("\n" + "=" * 60)
    print("Example 2: GPU Allocation")
    print("=" * 60)

    # Get available GPUs
    discovery = GPUDiscovery()
    gpus = discovery.get_gpus()

    if not gpus:
        print("No GPUs available")
        return

    # Create allocator
    allocator = GPUAllocator()

    # Plan allocation for multiple tasks
    tasks = [
        ("inference-1", ModelType.SDXL_BASE, None),  # Use default VRAM
        ("inference-2", ModelType.CLIP_VISION, None),
        ("training-1", ModelType.SDXL_LORA, None),
    ]

    print(f"\nPlanning allocation for {len(tasks)} tasks...")
    plan = allocator.plan_allocations(tasks, gpus)

    print(f"\n{plan.summary}\n")

    if plan.is_feasible():
        print("✓ All tasks successfully allocated:\n")
        for alloc in plan.allocations:
            print(f"  Task: {alloc.task_id}")
            print(f"    Model: {alloc.model_type.value}")
            print(f"    GPUs: {alloc.gpu_indices}")
            print(f"    VRAM Allocated: {alloc.vram_allocated_gb:.1f}GB")
            if alloc.uses_sharding:
                print(f"    {alloc.allocation_notes}")
            print()
    else:
        print("✗ Some tasks could not be allocated:\n")
        for task_id, reason in plan.failed_allocations:
            print(f"  {task_id}: {reason}")
        print()


def example_custom_profiles() -> None:
    """Example 3: Register custom model VRAM profiles."""
    print("\n" + "=" * 60)
    print("Example 3: Custom Model Profiles")
    print("=" * 60)

    from src.studio.gpu import ModelVRAMRegistry

    registry = ModelVRAMRegistry()

    # Check default profiles
    print("\nDefault profiles:")
    for profile in registry.list_profiles():
        print(f"  {profile.model_type.value}: {profile.vram_required_gb}GB")

    # Register custom profile
    custom_profile = ModelVRAMProfile(
        model_type=ModelType.CUSTOM,
        vram_required_gb=12.0,
        supports_sharding=True,
        max_batch_size=2,
        description="Custom diffusion model with specific VRAM needs",
    )

    registry.register(custom_profile)
    print(f"\n✓ Registered custom profile: {custom_profile.model_type.value}")

    # Use custom profile in allocation
    discovery = GPUDiscovery()
    gpus = discovery.get_gpus()

    if gpus:
        allocator = GPUAllocator(vram_registry=registry)
        try:
            allocation = allocator.allocate(
                task_id="custom-task",
                model_type=ModelType.CUSTOM,
                gpus=gpus,
            )
            print(f"  Allocated: {allocation}")
        except ValueError as e:
            print(f"  Allocation failed: {e}")


def example_monitoring() -> None:
    """Example 4: GPU monitoring with health tracking."""
    print("\n" + "=" * 60)
    print("Example 4: GPU Monitoring")
    print("=" * 60)

    print("\nStarting GPU monitor (5 second sample)...\n")

    cluster = MonitoredGPUCluster(poll_interval_sec=1.0)
    cluster.start()

    try:
        # Let it monitor for a bit
        for i in range(5):
            time.sleep(1)

            gpus = cluster.get_gpus()
            health = cluster.get_health_report()

            if health:
                print(f"Sample {i+1}: {health}")

                # Show metrics for first GPU
                if gpus:
                    metrics_buf = cluster.get_metrics(gpus[0].index)
                    if metrics_buf:
                        history = metrics_buf.get_history()
                        if history:
                            avg_util = metrics_buf.avg_vram_utilization_pct()
                            print(f"  GPU 0 avg utilization: {avg_util:.1f}%")

    finally:
        cluster.stop()
        print("\n✓ Monitor stopped")


def example_rebalancing_callback() -> None:
    """Example 5: Rebalancing callbacks."""
    print("\n" + "=" * 60)
    print("Example 5: Rebalancing Callbacks")
    print("=" * 60)

    def on_rebalance_needed(health_report) -> None:
        """Callback when rebalancing is needed."""
        print(f"\n⚠ Rebalancing triggered: {health_report.summary}")

    cluster = MonitoredGPUCluster(poll_interval_sec=2.0)
    cluster.register_rebalance_callback(on_rebalance_needed)

    print("\nMonitor with rebalancing callback (10 second sample)...")
    cluster.start()

    try:
        time.sleep(10)
    finally:
        cluster.stop()
        print("\n✓ Monitor stopped")


def main() -> None:
    """Run all examples."""
    setup_logging("INFO")

    print("\n" + "=" * 60)
    print("MOVILIZER GPU RESOURCE MANAGEMENT SYSTEM")
    print("=" * 60)

    try:
        example_discovery()
    except Exception as e:
        logger.error(f"Discovery example failed: {e}")

    try:
        example_allocation()
    except Exception as e:
        logger.error(f"Allocation example failed: {e}")

    try:
        example_custom_profiles()
    except Exception as e:
        logger.error(f"Custom profiles example failed: {e}")

    try:
        example_monitoring()
    except Exception as e:
        logger.error(f"Monitoring example failed: {e}")

    try:
        example_rebalancing_callback()
    except Exception as e:
        logger.error(f"Rebalancing example failed: {e}")

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
