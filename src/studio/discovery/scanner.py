"""HuggingFace model scanner for auto-discovery."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..utils import get_logger

logger = get_logger("discovery.scanner")


# Task category to HF task filter mapping
TASK_CATEGORIES = {
    "text-to-video": ["text-to-video", "video-generation"],
    "text-to-image": ["text-to-image", "image-generation"],
    "text-generation": ["text-generation"],
    "text-to-speech": ["text-to-speech", "tts"],
    "text-to-audio": ["text-to-audio", "audio-generation", "music-generation"],
}


@dataclass
class ModelCandidate:
    """Candidate model from HuggingFace."""

    repo_id: str
    task: str
    likes: int = 0
    downloads: int = 0
    last_modified: str = ""
    license: str | None = None
    private: bool = False
    score: float = 0.0

    def __repr__(self) -> str:
        return f"ModelCandidate({self.repo_id}, task={self.task}, score={self.score:.2f})"


@dataclass
class ScanResult:
    """Result of scanning for models in a task category."""

    task_category: str
    candidates: list[ModelCandidate] = field(default_factory=list)
    timestamp: str = ""
    total_scanned: int = 0
    filter_criteria: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class HFModelScanner:
    """Scans HuggingFace for models matching task requirements."""

    HF_API_BASE = "https://huggingface.co/api/models"

    # Minimum thresholds for filtering
    MIN_DOWNLOADS = 100
    MIN_LIKES = 0

    # License whitelist (None means no license specified, considered open)
    OPEN_LICENSES = {
        "openrail",
        "openrail++",
        "mit",
        "apache-2.0",
        "bsd-3-clause",
        "bsd-2-clause",
        "gpl-3.0",
        "gpl-2.0",
        "cc-by-4.0",
        "cc-by-sa-4.0",
        "cc0-1.0",
        "artistic-2.0",
        "wtfpl",
        "isc",
        "mpl-2.0",
        "agpl-3.0",
        None,  # No license specified is considered open
    }

    def __init__(self, timeout: int = 30):
        """Initialize scanner.

        Args:
            timeout: Request timeout in seconds.
        """
        self.timeout = timeout

    def _fetch_hf_models(
        self, task: str, limit: int = 100, sort: str = "trending"
    ) -> list[dict[str, Any]]:
        """Fetch models from HuggingFace API for a given task.

        Args:
            task: HF task filter (e.g., "text-to-image").
            limit: Maximum number of results.
            sort: Sort order ("trending", "recently-updated", "most-liked", etc).

        Returns:
            List of model metadata dicts.
        """
        url = (
            f"{self.HF_API_BASE}"
            f"?task={task}"
            f"&limit={limit}"
            f"&sort={sort}"
        )

        try:
            logger.debug(f"Fetching from HF API: {url}")
            with urllib.request.urlopen(url, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
                if isinstance(data, list):
                    return data
                return []
        except urllib.error.HTTPError as e:
            logger.warning(f"HTTP error fetching {task}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching models for {task}: {e}")
            return []

    def _is_open_license(self, model_data: dict[str, Any]) -> bool:
        """Check if model has an open license.

        Args:
            model_data: Model metadata from HF API.

        Returns:
            True if license is in whitelist.
        """
        license_str = model_data.get("license")
        if license_str is None:
            return True
        # Normalize to lowercase for comparison
        normalized = license_str.lower() if isinstance(license_str, str) else None
        return normalized in self.OPEN_LICENSES

    def _score_candidate(self, model: dict[str, Any], recency_boost: float = 1.0) -> float:
        """Score a candidate model.

        Formula: likes * recency_boost + downloads * 0.1

        Args:
            model: Model metadata.
            recency_boost: Multiplier for recent models (0-2).

        Returns:
            Score (higher is better).
        """
        likes = max(0, model.get("likes", 0) or 0)
        downloads = max(0, model.get("downloads", 0) or 0)

        # Logarithmic scaling to avoid dominance by very popular models
        likes_score = (1 + likes) ** 0.5
        downloads_score = (1 + downloads / 100) ** 0.5

        return likes_score * recency_boost + downloads_score

    def _get_recency_boost(self, last_modified: str | None) -> float:
        """Calculate recency boost (1.0 = baseline, up to 2.0 for very recent).

        Args:
            last_modified: ISO timestamp of last modification.

        Returns:
            Boost multiplier.
        """
        if not last_modified:
            return 1.0

        try:
            mod_time = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days_old = (now - mod_time).days

            # Linear decay: 2.0 at 0 days, 1.0 at 90 days, <1.0 after
            if days_old <= 0:
                return 2.0
            if days_old <= 90:
                return 2.0 - (days_old / 90.0)
            return max(0.5, 1.0 - (days_old - 90) / 365.0)
        except Exception:
            return 1.0

    def scan_task_category(
        self,
        task_category: str,
        limit_per_task: int = 50,
        sort: str = "trending",
    ) -> ScanResult:
        """Scan HuggingFace for models in a task category.

        Args:
            task_category: One of "text-to-video", "text-to-image", "text-generation",
                          "text-to-speech", "text-to-audio".
            limit_per_task: Max models to fetch per HF task type.
            sort: Sort order for HF API results.

        Returns:
            ScanResult with ranked candidates.
        """
        if task_category not in TASK_CATEGORIES:
            logger.error(f"Unknown task category: {task_category}")
            return ScanResult(task_category=task_category)

        candidates_dict: dict[str, ModelCandidate] = {}
        total_scanned = 0

        # Query each HF task type for this category
        for hf_task in TASK_CATEGORIES[task_category]:
            models = self._fetch_hf_models(hf_task, limit=limit_per_task, sort=sort)
            total_scanned += len(models)

            for model_data in models:
                repo_id = model_data.get("id")
                if not repo_id:
                    continue

                # Skip if already processed (prefer higher score later)
                if repo_id in candidates_dict:
                    continue

                # Filter by license
                if not self._is_open_license(model_data):
                    logger.debug(f"Skipping {repo_id}: not open license")
                    continue

                # Filter by private status
                if model_data.get("private", False):
                    logger.debug(f"Skipping {repo_id}: private model")
                    continue

                # Filter by minimum downloads
                downloads = model_data.get("downloads", 0) or 0
                if downloads < self.MIN_DOWNLOADS:
                    logger.debug(f"Skipping {repo_id}: only {downloads} downloads")
                    continue

                # Calculate score
                last_modified = model_data.get("lastModified")
                recency = self._get_recency_boost(last_modified)
                score = self._score_candidate(model_data, recency_boost=recency)

                candidate = ModelCandidate(
                    repo_id=repo_id,
                    task=task_category,
                    likes=model_data.get("likes", 0) or 0,
                    downloads=downloads,
                    last_modified=last_modified or "",
                    license=model_data.get("license"),
                    private=model_data.get("private", False),
                    score=score,
                )
                candidates_dict[repo_id] = candidate
                logger.debug(f"Added candidate: {repo_id} (score={score:.2f})")

        # Sort by score descending
        candidates = sorted(candidates_dict.values(), key=lambda c: c.score, reverse=True)

        return ScanResult(
            task_category=task_category,
            candidates=candidates,
            total_scanned=total_scanned,
            filter_criteria={
                "min_downloads": self.MIN_DOWNLOADS,
                "min_likes": self.MIN_LIKES,
                "open_licenses": True,
                "private_models": False,
            },
        )

    def scan_all_categories(
        self,
        limit_per_task: int = 50,
        sort: str = "trending",
    ) -> dict[str, ScanResult]:
        """Scan all task categories.

        Args:
            limit_per_task: Max models per HF task.
            sort: Sort order.

        Returns:
            Dict mapping task category to ScanResult.
        """
        results: dict[str, ScanResult] = {}
        for task_category in TASK_CATEGORIES:
            logger.info(f"Scanning {task_category}...")
            result = self.scan_task_category(
                task_category, limit_per_task=limit_per_task, sort=sort
            )
            results[task_category] = result
            logger.info(
                f"  Found {len(result.candidates)} candidates "
                f"(scanned {result.total_scanned} total)"
            )

        return results
