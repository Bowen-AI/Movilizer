"""Base classes and enums for the multi-agent critique system."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CritiqueLevel(Enum):
    """Level at which critique is performed."""

    SHOT = "shot"  # Single shot/clip
    SCENE = "scene"  # Full scene with multiple shots
    MOVIE = "movie"  # Full movie assembly


class ProducerDecision(Enum):
    """Producer's decision on a generated clip."""

    APPROVE = "approve"  # Clip meets quality standards
    REVISE = "revise"  # Clip needs revision/regeneration
    REJECT = "reject"  # Clip is fundamentally flawed


@dataclass
class CritiqueResult:
    """Result of a single critic's evaluation."""

    critic_name: str
    score: float  # 0-10, higher is better
    issues: list[str] = field(default_factory=list)  # Problems found
    suggestions: list[str] = field(default_factory=list)  # Improvement suggestions
    reasoning: str = ""  # Explanation of the score
    metadata: dict[str, Any] = field(default_factory=dict)  # Additional data

    def __post_init__(self):
        """Validate score range."""
        if not 0 <= self.score <= 10:
            raise ValueError(f"Score must be 0-10, got {self.score}")

    @property
    def is_passing(self) -> bool:
        """Check if score is passing (>=7)."""
        return self.score >= 7.0

    @property
    def is_critical(self) -> bool:
        """Check if score is critical (<4)."""
        return self.score < 4.0


@dataclass
class CritiqueContext:
    """Context information for critique evaluation."""

    run_id: str
    project: str
    scene: str
    shot: str
    shot_dir: Path
    frames: list[Path]  # Keyframes or all frames
    clip_path: Optional[Path] = None  # Path to generated clip
    script: str = ""  # Scene script/dialog
    shot_description: str = ""  # Visual description of shot
    previous_clips: list[Path] = field(default_factory=list)  # Prior shots in scene
    next_clips: list[Path] = field(default_factory=list)  # Following shots in scene
    genre: str = ""  # Movie genre
    tone: str = ""  # Emotional tone
    metadata: dict[str, Any] = field(default_factory=dict)  # Additional context


class CriticBase(ABC):
    """Abstract base class for all critics."""

    def __init__(self, name: str, level: CritiqueLevel = CritiqueLevel.SHOT):
        """Initialize critic.

        Args:
            name: Name of this critic
            level: Level at which this critic operates
        """
        self.name = name
        self.level = level
        self.logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    async def evaluate(self, context: CritiqueContext) -> CritiqueResult:
        """Evaluate a clip and return critique.

        Args:
            context: Critique context with clip info

        Returns:
            CritiqueResult with score, issues, and suggestions
        """
        pass

    def _create_result(
        self,
        score: float,
        issues: list[str] | None = None,
        suggestions: list[str] | None = None,
        reasoning: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> CritiqueResult:
        """Helper to create CritiqueResult."""
        return CritiqueResult(
            critic_name=self.name,
            score=score,
            issues=issues or [],
            suggestions=suggestions or [],
            reasoning=reasoning,
            metadata=metadata or {},
        )
