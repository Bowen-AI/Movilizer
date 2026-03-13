#!/usr/bin/env python3
"""Example usage of the Model Auto-Discovery agent.

This script demonstrates how to use the discovery system to:
1. Scan HuggingFace for better models
2. Benchmark candidates
3. Integrate passing models
4. Schedule periodic discovery
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from studio.utils import get_logger, load_yaml, setup_logging
from studio.discovery.scanner import HFModelScanner
from studio.discovery.benchmark import BenchmarkRunner, BenchmarkResult
from studio.discovery.integrator import ModelIntegrator
from studio.discovery.scheduler import DiscoveryScheduler

logger = get_logger("discovery.example")


def example_scan_models() -> None:
    """Example: Scan HuggingFace for models."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Scanning HuggingFace for Models")
    print("=" * 70)

    scanner = HFModelScanner(timeout=30)

    # Scan text-to-image category
    print("\nScanning text-to-image models...")
    result = scanner.scan_task_category(
        "text-to-image", limit_per_task=20, sort="trending"
    )

    print(f"\nResults for {result.task_category}:")
    print(f"  Total scanned: {result.total_scanned}")
    print(f"  Candidates found: {len(result.candidates)}")
    print(f"  Filter criteria: {result.filter_criteria}")

    if result.candidates:
        print("\nTop 5 candidates:")
        for i, candidate in enumerate(result.candidates[:5], 1):
            print(
                f"  {i}. {candidate.repo_id}"
                f" (likes={candidate.likes}, downloads={candidate.downloads}, "
                f"score={candidate.score:.2f})"
            )


def example_scan_all_categories() -> None:
    """Example: Scan all task categories."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Scanning All Categories")
    print("=" * 70)

    scanner = HFModelScanner(timeout=30)
    results = scanner.scan_all_categories(limit_per_task=10)

    for task_category, scan_result in results.items():
        print(f"\n{task_category}:")
        print(f"  Candidates: {len(scan_result.candidates)}")
        if scan_result.candidates:
            best = scan_result.candidates[0]
            print(f"  Best: {best.repo_id} (score={best.score:.2f})")


def example_benchmark() -> None:
    """Example: Benchmark a candidate model."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Benchmarking a Model")
    print("=" * 70)

    runner = BenchmarkRunner(timeout=600)
    cache_root = Path("models/cache")

    # This would benchmark a real model (requires the model to be available)
    print("\nNote: Benchmarking requires the model to be pulled first.")
    print("Example benchmark result structure:")

    example_result = BenchmarkResult(
        repo_id="stabilityai/stable-diffusion-xl-base-1.0",
        task="text-to-image",
        passed=True,
        score=0.85,
        generation_time_sec=12.5,
        peak_vram_mb=8192,
        quality_score=0.88,
        comparison_score=0.15,
        message="Benchmark passed with good results",
    )

    print(f"\n  repo_id: {example_result.repo_id}")
    print(f"  task: {example_result.task}")
    print(f"  passed: {example_result.passed}")
    print(f"  score: {example_result.score:.2f}")
    print(f"  generation_time_sec: {example_result.generation_time_sec:.1f}")
    print(f"  peak_vram_mb: {example_result.peak_vram_mb:.0f}")
    print(f"  quality_score: {example_result.quality_score:.2f}")
    print(f"  comparison_score: {example_result.comparison_score:.2f}")


def example_integration() -> None:
    """Example: Integration configuration."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Integration Configuration")
    print("=" * 70)

    cache_root = Path("models/cache")
    integrator = ModelIntegrator(cache_root=cache_root)

    print(f"\nIntegrator Configuration:")
    print(f"  Cache root: {integrator.cache_root}")
    print(f"  Integration threshold: {integrator.INTEGRATION_THRESHOLD}")
    print(f"  Workspace config: {integrator.workspace_config_path}")

    print("\nIntegration workflow:")
    print("  1. Pull candidate model to cache")
    print("  2. Update workspace configuration")
    print("  3. Run validation pipeline")
    print("  4. Save migration report")


def example_scheduler() -> None:
    """Example: Scheduler configuration and usage."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Scheduler Configuration")
    print("=" * 70)

    # Load default config
    config_path = Path("configs/discovery/default.yaml")
    if config_path.exists():
        config = load_yaml(config_path)
        print(f"\nLoaded config from {config_path}")
    else:
        config = {
            "scan_interval_hours": 24,
            "benchmark_interval_hours": 168,
            "check_interval_seconds": 3600,
        }
        print("\nUsing example configuration")

    scheduler = DiscoveryScheduler(config)

    print(f"\nScheduler Status:")
    status = scheduler.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")

    print(f"\nScheduler Features:")
    print(f"  ✓ Periodic scan ({config.get('scan_interval_hours', 24)} hours)")
    print(f"  ✓ Periodic benchmark ({config.get('benchmark_interval_hours', 168)} hours)")
    print(f"  ✓ Manual trigger capability")
    print(f"  ✓ State persistence")
    print(f"  ✓ Error tracking")

    print(f"\nScheduler Methods:")
    print(f"  scheduler.start() - Start periodic tasks")
    print(f"  scheduler.stop() - Stop periodic tasks")
    print(f"  scheduler.trigger_scan() - Manually trigger scan")
    print(f"  scheduler.trigger_benchmark() - Manually trigger benchmarks")
    print(f"  scheduler.get_status() - Get current status")


def example_full_workflow() -> None:
    """Example: Full discovery workflow."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Full Discovery Workflow")
    print("=" * 70)

    print("""
Discovery Workflow:

1. SCAN PHASE (Daily)
   ├─ Query HuggingFace API for each task category
   ├─ Filter by: open licenses, minimum downloads, recent updates
   ├─ Score candidates: likes * recency + downloads * popularity
   └─ Output: ranked list of candidates per task

2. BENCHMARK PHASE (Weekly)
   ├─ Pull candidate models to cache
   ├─ Run task-specific benchmarks:
   │  ├─ Generation time measurement
   │  ├─ VRAM usage tracking
   │  └─ Quality scoring
   ├─ Compare against current model
   └─ Output: benchmark results for top candidates

3. INTEGRATION PHASE (On Pass)
   ├─ Check benchmark score >= threshold (0.75)
   ├─ Pull model to permanent cache
   ├─ Update workspace configuration
   ├─ Run validation pipeline
   └─ Output: migration report & updated config

4. SCHEDULE PHASE (Continuous)
   ├─ Daily scan trigger (configurable)
   ├─ Weekly benchmark trigger (configurable)
   ├─ State persistence
   └─ Error tracking & recovery
    """)


def main() -> None:
    """Run all examples."""
    setup_logging("INFO")

    print("\n" + "=" * 70)
    print("Model Auto-Discovery Agent - Usage Examples")
    print("=" * 70)

    # Example 1: Basic scanning
    try:
        example_scan_models()
    except Exception as e:
        logger.warning(f"Scan example skipped: {e}")

    # Example 2: All categories (commented out to avoid multiple API calls)
    # example_scan_all_categories()

    # Example 3: Benchmark structure
    example_benchmark()

    # Example 4: Integration
    example_integration()

    # Example 5: Scheduler
    example_scheduler()

    # Example 6: Full workflow
    example_full_workflow()

    print("\n" + "=" * 70)
    print("Examples Complete")
    print("=" * 70)
    print("\nFor more information, see:")
    print("  - configs/discovery/default.yaml (configuration)")
    print("  - src/studio/discovery/scanner.py (scanning)")
    print("  - src/studio/discovery/benchmark.py (evaluation)")
    print("  - src/studio/discovery/integrator.py (integration)")
    print("  - src/studio/discovery/scheduler.py (scheduling)")


if __name__ == "__main__":
    main()
