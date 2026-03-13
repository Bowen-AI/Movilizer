"""Model integrator for pulling and configuring discovered models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..models.registry import pull_model
from ..utils import get_logger, load_yaml, now_utc_iso, save_json, save_yaml
from .benchmark import BenchmarkResult

logger = get_logger("discovery.integrator")


@dataclass
class IntegrationResult:
    """Result of integrating a discovered model."""

    repo_id: str
    task: str
    integrated: bool = False
    message: str = ""
    model_path: str = ""
    config_updated: bool = False
    validation_passed: bool = False
    timestamp: str = ""
    migration_report: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = now_utc_iso()


class ModelIntegrator:
    """Integrates discovered models into the workspace."""

    # Benchmark score threshold for integration
    INTEGRATION_THRESHOLD = 0.75

    def __init__(self, cache_root: Path, workspace_config_path: Path | None = None):
        """Initialize integrator.

        Args:
            cache_root: Model cache directory.
            workspace_config_path: Path to workspace config file (optional).
        """
        self.cache_root = Path(cache_root)
        self.workspace_config_path = workspace_config_path
        self.cache_root.mkdir(parents=True, exist_ok=True)

    def _pull_candidate(self, repo_id: str, revision: str | None = None) -> str | None:
        """Pull a candidate model to cache.

        Args:
            repo_id: HuggingFace repo ID.
            revision: Optional revision (commit/branch/tag).

        Returns:
            Path to pulled model, or None if failed.
        """
        logger.info(f"Pulling model {repo_id}...")

        result = pull_model(
            source=repo_id,
            cache_root=self.cache_root,
            revision=revision,
            local_files_only=False,
        )

        if result.pulled:
            logger.info(f"Successfully pulled {repo_id} to {result.resolved_path}")
            return result.resolved_path

        logger.error(f"Failed to pull {repo_id}: {result.message}")
        return None

    def _update_workspace_config(
        self, repo_id: str, task: str, model_path: str
    ) -> bool:
        """Update workspace config with new model.

        Args:
            repo_id: HuggingFace repo ID.
            task: Task category.
            model_path: Path to pulled model.

        Returns:
            True if config was updated successfully.
        """
        if not self.workspace_config_path or not self.workspace_config_path.exists():
            logger.warning("Workspace config not found, skipping config update")
            return False

        try:
            config = load_yaml(self.workspace_config_path)

            # Initialize models section if needed
            if "models" not in config:
                config["models"] = {}

            # Add or update model entry
            config["models"][task] = {
                "repo_id": repo_id,
                "path": model_path,
                "integrated_at": now_utc_iso(),
            }

            # Save updated config
            save_yaml(self.workspace_config_path, config)
            logger.info(f"Updated workspace config with {repo_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update workspace config: {e}")
            return False

    def _validate_model(self, repo_id: str, model_path: str, task: str) -> bool:
        """Run validation pipeline on integrated model.

        Args:
            repo_id: HuggingFace repo ID.
            model_path: Path to pulled model.
            task: Task category.

        Returns:
            True if validation passed.
        """
        logger.info(f"Validating model {repo_id}...")

        try:
            # Basic validation: check model files exist
            path = Path(model_path)
            if not path.exists():
                logger.error(f"Model path does not exist: {model_path}")
                return False

            # Task-specific validation
            if task == "text-to-image":
                required_files = ["model_index.json", "unet"]
                for fname in required_files:
                    if not (path / fname).exists():
                        logger.warning(f"Missing expected file: {fname}")

            elif task == "text-to-video":
                required_files = ["model_index.json"]
                for fname in required_files:
                    if not (path / fname).exists():
                        logger.warning(f"Missing expected file: {fname}")

            elif task == "text-generation":
                required_files = ["config.json", "pytorch_model.bin"]
                for fname in required_files:
                    if not (path / fname).exists() and not (path / fname.replace(".bin", ".safetensors")).exists():
                        logger.warning(f"Missing expected file: {fname}")

            logger.info(f"Validation passed for {repo_id}")
            return True

        except Exception as e:
            logger.error(f"Validation failed for {repo_id}: {e}")
            return False

    def integrate_candidate(
        self, repo_id: str, task: str, benchmark_result: BenchmarkResult
    ) -> IntegrationResult:
        """Integrate a candidate model if it passes threshold.

        Args:
            repo_id: HuggingFace repo ID.
            task: Task category.
            benchmark_result: BenchmarkResult from evaluation.

        Returns:
            IntegrationResult with integration status.
        """
        result = IntegrationResult(repo_id=repo_id, task=task)

        # Check benchmark threshold
        if benchmark_result.score < self.INTEGRATION_THRESHOLD:
            result.message = (
                f"Benchmark score {benchmark_result.score:.2f} "
                f"below integration threshold {self.INTEGRATION_THRESHOLD}"
            )
            logger.warning(result.message)
            return result

        if not benchmark_result.passed:
            result.message = f"Benchmark did not pass: {benchmark_result.message}"
            logger.warning(result.message)
            return result

        # Pull model to cache
        model_path = self._pull_candidate(repo_id)
        if not model_path:
            result.message = "Failed to pull model"
            return result

        result.model_path = model_path

        # Update workspace config
        config_updated = self._update_workspace_config(repo_id, task, model_path)
        result.config_updated = config_updated

        # Validate model
        validation_passed = self._validate_model(repo_id, model_path, task)
        result.validation_passed = validation_passed

        # Determine overall success
        result.integrated = validation_passed
        if result.integrated:
            result.message = (
                f"Successfully integrated {repo_id}: "
                f"score={benchmark_result.score:.2f}, "
                f"quality={benchmark_result.quality_score:.2f}"
            )
            logger.info(result.message)
        else:
            result.message = "Integration failed validation"
            logger.error(result.message)

        # Create migration report
        result.migration_report = {
            "repo_id": repo_id,
            "task": task,
            "integrated_at": now_utc_iso(),
            "model_path": model_path,
            "benchmark_score": benchmark_result.score,
            "benchmark_quality": benchmark_result.quality_score,
            "benchmark_time_sec": benchmark_result.generation_time_sec,
            "benchmark_vram_mb": benchmark_result.peak_vram_mb,
            "config_updated": config_updated,
            "validation_passed": validation_passed,
        }

        return result

    def save_migration_report(
        self, result: IntegrationResult, output_dir: Path
    ) -> Path:
        """Save migration report to JSON.

        Args:
            result: IntegrationResult to save.
            output_dir: Directory to save to.

        Returns:
            Path to saved report.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = (
            f"migration_{result.repo_id.replace('/', '_')}_{result.timestamp}.json"
        )
        filepath = output_dir / filename

        save_json(filepath, result.migration_report)
        logger.info(f"Saved migration report to {filepath}")
        return filepath

    def rollback_integration(self, repo_id: str) -> bool:
        """Rollback an integration by removing model and updating config.

        Args:
            repo_id: HuggingFace repo ID to rollback.

        Returns:
            True if rollback was successful.
        """
        logger.info(f"Rolling back integration for {repo_id}...")

        # Could implement model removal and config revert here
        # For now, just log the intent
        logger.warning(f"Rollback not fully implemented for {repo_id}")
        return False
