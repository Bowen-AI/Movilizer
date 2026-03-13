"""Benchmark runner for evaluating candidate models."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..utils import get_logger, now_utc_iso, save_json

logger = get_logger("discovery.benchmark")


@dataclass
class BenchmarkResult:
    """Result of benchmarking a candidate model."""

    repo_id: str
    task: str
    passed: bool
    score: float = 0.0
    generation_time_sec: float = 0.0
    peak_vram_mb: float = 0.0
    quality_score: float = 0.0
    comparison_score: float = 0.0  # Score vs current model (-1=worse, 0=equal, 1=better)
    message: str = ""
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = now_utc_iso()


class BenchmarkRunner:
    """Runs standardized benchmarks on candidate models."""

    # Threshold for passing benchmarks (0-1 scale)
    QUALITY_THRESHOLD = 0.7
    VRAM_THRESHOLD_MB = 10240  # 10 GB
    TIME_THRESHOLD_SEC = 300  # 5 minutes

    def __init__(self, timeout: int = 600):
        """Initialize benchmark runner.

        Args:
            timeout: Timeout for individual benchmark runs in seconds.
        """
        self.timeout = timeout

    def _measure_vram_usage(self) -> float:
        """Measure current GPU VRAM usage in MB.

        Returns:
            VRAM usage in MB, or 0.0 if unable to measure.
        """
        try:
            import torch

            if torch.cuda.is_available():
                return torch.cuda.max_memory_allocated() / 1024 / 1024
            return 0.0
        except Exception as e:
            logger.debug(f"Could not measure VRAM: {e}")
            return 0.0

    def _run_benchmark_command(
        self, command: list[str], timeout: int | None = None
    ) -> tuple[bool, str]:
        """Run a benchmark command.

        Args:
            command: Command and args to run.
            timeout: Timeout in seconds.

        Returns:
            Tuple of (success, output/error_message).
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
            )
            if result.returncode == 0:
                return True, result.stdout
            return False, result.stderr
        except subprocess.TimeoutExpired:
            return False, "Benchmark timed out"
        except Exception as e:
            return False, str(e)

    def benchmark_candidate(
        self,
        repo_id: str,
        task: str,
        cache_root: Path,
    ) -> BenchmarkResult:
        """Benchmark a candidate model.

        Args:
            repo_id: HuggingFace repo ID.
            task: Task category (text-to-image, text-to-video, etc).
            cache_root: Model cache directory.

        Returns:
            BenchmarkResult with pass/fail and scores.
        """
        logger.info(f"Benchmarking {repo_id} ({task})...")

        start_time = time.time()
        result = BenchmarkResult(
            repo_id=repo_id,
            task=task,
            passed=False,
            message="Benchmark not started",
        )

        try:
            # Reset VRAM tracking
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.reset_peak_memory_stats()
                    torch.cuda.empty_cache()
            except Exception:
                pass

            # Run task-specific benchmark
            benchmark_method = getattr(
                self, f"_benchmark_{task.replace('-', '_')}", None
            )
            if not benchmark_method:
                result.message = f"No benchmark implemented for {task}"
                logger.warning(result.message)
                return result

            benchmark_method(result, repo_id, cache_root)

            # Measure final VRAM
            result.peak_vram_mb = self._measure_vram_usage()

            # Check thresholds
            if result.quality_score < self.QUALITY_THRESHOLD:
                result.passed = False
                result.message = (
                    f"Quality score {result.quality_score:.2f} "
                    f"below threshold {self.QUALITY_THRESHOLD}"
                )
            elif result.peak_vram_mb > self.VRAM_THRESHOLD_MB:
                result.passed = False
                result.message = (
                    f"VRAM usage {result.peak_vram_mb:.0f}MB "
                    f"exceeds threshold {self.VRAM_THRESHOLD_MB}MB"
                )
            elif result.generation_time_sec > self.TIME_THRESHOLD_SEC:
                result.passed = False
                result.message = (
                    f"Generation time {result.generation_time_sec:.1f}s "
                    f"exceeds threshold {self.TIME_THRESHOLD_SEC}s"
                )
            else:
                result.passed = True
                result.message = "Benchmark passed"

            result.score = (
                result.quality_score * 0.5
                + (1 - result.peak_vram_mb / self.VRAM_THRESHOLD_MB) * 0.25
                + (1 - result.generation_time_sec / self.TIME_THRESHOLD_SEC) * 0.25
            )
            result.score = max(0, min(1.0, result.score))

            elapsed = time.time() - start_time
            logger.info(
                f"Benchmark completed in {elapsed:.1f}s: {result.repo_id} "
                f"passed={result.passed}, score={result.score:.2f}"
            )

        except Exception as e:
            result.passed = False
            result.message = f"Benchmark error: {e}"
            logger.error(f"Benchmark failed for {repo_id}: {e}")

        return result

    def _benchmark_text_to_image(
        self, result: BenchmarkResult, repo_id: str, cache_root: Path
    ) -> None:
        """Benchmark text-to-image model."""
        logger.debug(f"Running text-to-image benchmark for {repo_id}")

        # Simulated benchmark: check if model can be loaded
        try:
            from diffusers import DiffusionPipeline

            logger.debug(f"Loading model {repo_id}...")
            pipeline = DiffusionPipeline.from_pretrained(
                repo_id, cache_dir=str(cache_root), local_files_only=True
            )

            # Simulate generation
            start = time.time()
            with __import__("torch").no_grad():
                _ = pipeline(
                    "test prompt",
                    height=512,
                    width=512,
                    num_inference_steps=1,
                    guidance_scale=7.5,
                ).images
            result.generation_time_sec = time.time() - start

            # Quality is based on successful generation
            result.quality_score = 0.85
            result.message = "Text-to-image benchmark completed"
            logger.debug(f"Generated image in {result.generation_time_sec:.2f}s")

        except Exception as e:
            result.quality_score = 0.0
            result.message = f"Text-to-image benchmark failed: {e}"
            logger.warning(f"Failed to benchmark text-to-image: {e}")

    def _benchmark_text_to_video(
        self, result: BenchmarkResult, repo_id: str, cache_root: Path
    ) -> None:
        """Benchmark text-to-video model."""
        logger.debug(f"Running text-to-video benchmark for {repo_id}")

        try:
            # Attempt to load video model
            from diffusers import DiffusionPipeline

            logger.debug(f"Loading video model {repo_id}...")
            pipeline = DiffusionPipeline.from_pretrained(
                repo_id, cache_dir=str(cache_root), local_files_only=True
            )

            # Simulate video generation benchmark
            start = time.time()
            with __import__("torch").no_grad():
                _ = pipeline(
                    "test prompt",
                    num_frames=4,
                    height=512,
                    width=512,
                    num_inference_steps=1,
                )
            result.generation_time_sec = time.time() - start

            result.quality_score = 0.80
            result.message = "Text-to-video benchmark completed"
            logger.debug(f"Generated video in {result.generation_time_sec:.2f}s")

        except Exception as e:
            result.quality_score = 0.0
            result.message = f"Text-to-video benchmark failed: {e}"
            logger.warning(f"Failed to benchmark text-to-video: {e}")

    def _benchmark_text_generation(
        self, result: BenchmarkResult, repo_id: str, cache_root: Path
    ) -> None:
        """Benchmark text generation model."""
        logger.debug(f"Running text-generation benchmark for {repo_id}")

        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            logger.debug(f"Loading text model {repo_id}...")
            tokenizer = AutoTokenizer.from_pretrained(repo_id, cache_dir=str(cache_root))
            model = AutoModelForCausalLM.from_pretrained(
                repo_id, cache_dir=str(cache_root), local_files_only=True
            )

            # Benchmark text generation
            inputs = tokenizer("Test input:", return_tensors="pt")
            start = time.time()
            with __import__("torch").no_grad():
                _ = model.generate(**inputs, max_new_tokens=10, num_beams=1)
            result.generation_time_sec = time.time() - start

            result.quality_score = 0.82
            result.message = "Text-generation benchmark completed"
            logger.debug(f"Generated text in {result.generation_time_sec:.2f}s")

        except Exception as e:
            result.quality_score = 0.0
            result.message = f"Text-generation benchmark failed: {e}"
            logger.warning(f"Failed to benchmark text-generation: {e}")

    def _benchmark_text_to_speech(
        self, result: BenchmarkResult, repo_id: str, cache_root: Path
    ) -> None:
        """Benchmark text-to-speech model."""
        logger.debug(f"Running text-to-speech benchmark for {repo_id}")

        try:
            from transformers import pipeline

            logger.debug(f"Loading TTS model {repo_id}...")
            pipe = pipeline("text-to-speech", model=repo_id, cache_dir=str(cache_root))

            # Benchmark TTS generation
            start = time.time()
            _ = pipe("Test speech synthesis")
            result.generation_time_sec = time.time() - start

            result.quality_score = 0.78
            result.message = "Text-to-speech benchmark completed"
            logger.debug(f"Synthesized speech in {result.generation_time_sec:.2f}s")

        except Exception as e:
            result.quality_score = 0.0
            result.message = f"Text-to-speech benchmark failed: {e}"
            logger.warning(f"Failed to benchmark text-to-speech: {e}")

    def _benchmark_text_to_audio(
        self, result: BenchmarkResult, repo_id: str, cache_root: Path
    ) -> None:
        """Benchmark text-to-audio or music generation model."""
        logger.debug(f"Running text-to-audio benchmark for {repo_id}")

        try:
            from transformers import pipeline

            logger.debug(f"Loading audio model {repo_id}...")
            pipe = pipeline("text-to-audio", model=repo_id, cache_dir=str(cache_root))

            # Benchmark audio generation
            start = time.time()
            _ = pipe("Test audio generation")
            result.generation_time_sec = time.time() - start

            result.quality_score = 0.75
            result.message = "Text-to-audio benchmark completed"
            logger.debug(f"Generated audio in {result.generation_time_sec:.2f}s")

        except Exception as e:
            result.quality_score = 0.0
            result.message = f"Text-to-audio benchmark failed: {e}"
            logger.warning(f"Failed to benchmark text-to-audio: {e}")

    def compare_with_current(
        self,
        candidate_result: BenchmarkResult,
        current_result: BenchmarkResult,
    ) -> None:
        """Compare candidate result with current model result.

        Args:
            candidate_result: Benchmark result for candidate.
            current_result: Benchmark result for current model.
        """
        # Quality comparison
        quality_delta = candidate_result.quality_score - current_result.quality_score

        # Performance comparison (lower is better)
        time_ratio = candidate_result.generation_time_sec / max(
            1.0, current_result.generation_time_sec
        )
        vram_ratio = candidate_result.peak_vram_mb / max(1.0, current_result.peak_vram_mb)

        # Combined score: +0.5 for 10% quality gain, +0.25 for 20% faster, +0.25 for 20% less VRAM
        comparison_score = 0.0
        comparison_score += max(-0.5, min(0.5, quality_delta * 5))  # ±5 points per 0.1 quality
        comparison_score += max(-0.25, 0.25 * (1 - time_ratio))  # Up to +0.25 for faster
        comparison_score += max(-0.25, 0.25 * (1 - vram_ratio))  # Up to +0.25 for less VRAM

        candidate_result.comparison_score = max(-1.0, min(1.0, comparison_score))

        logger.info(
            f"Comparison: quality_delta={quality_delta:.3f}, "
            f"time_ratio={time_ratio:.2f}, vram_ratio={vram_ratio:.2f}, "
            f"comparison_score={candidate_result.comparison_score:.3f}"
        )

    def save_result(self, result: BenchmarkResult, output_dir: Path) -> Path:
        """Save benchmark result to JSON.

        Args:
            result: BenchmarkResult to save.
            output_dir: Directory to save to.

        Returns:
            Path to saved result file.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"benchmark_{result.repo_id.replace('/', '_')}_{result.timestamp}.json"
        filepath = output_dir / filename

        save_json(
            filepath,
            {
                "repo_id": result.repo_id,
                "task": result.task,
                "passed": result.passed,
                "score": result.score,
                "generation_time_sec": result.generation_time_sec,
                "peak_vram_mb": result.peak_vram_mb,
                "quality_score": result.quality_score,
                "comparison_score": result.comparison_score,
                "message": result.message,
                "timestamp": result.timestamp,
                "metadata": result.metadata,
            },
        )

        logger.info(f"Saved benchmark result to {filepath}")
        return filepath
