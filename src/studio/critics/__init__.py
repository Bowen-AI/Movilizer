"""Multi-agent critique system for Movilizer.

This module provides comprehensive AI-based critique of generated video clips
using multiple specialized critics (story, visual, technical, etc.) that
evaluate different aspects of quality. A producer agent aggregates the results
and makes decisions on whether clips should be approved, revised, or rejected.

Key components:
- CriticBase: Abstract base class for all critics
- StoryCritic: Evaluates narrative and dialogue
- VisualCritic: Evaluates composition and aesthetics
- ContinuityCritic: Checks continuity between clips
- AudienceCritic: Simulates audience reactions
- TechnicalCritic: Checks technical quality (flicker, artifacts, resolution)
- DirectorCritic: Evaluates cinematography
- ProducerAgent: Aggregates critiques and makes decisions
- EnsembleRunner: Orchestrates running all critics
"""

from .audience_critic import AudienceCritic
from .base import (
    CritiqueContext,
    CritiqueLevel,
    CritiqueResult,
    CriticBase,
    ProducerDecision,
)
from .continuity_critic import ContinuityCritic
from .director_critic import DirectorCritic
from .ensemble import EnsembleConfig, EnsembleRunner, run_ensemble_critique
from .llm_pool import LLMPool
from .producer import ProducerAgent, ProducerConfig, ProducerDecision_Result
from .story_critic import StoryCritic
from .technical_critic import TechnicalCritic
from .visual_critic import VisualCritic

__all__ = [
    # Base classes and enums
    "CriticBase",
    "CritiqueResult",
    "CritiqueContext",
    "CritiqueLevel",
    "ProducerDecision",
    # Critics
    "StoryCritic",
    "VisualCritic",
    "ContinuityCritic",
    "AudienceCritic",
    "TechnicalCritic",
    "DirectorCritic",
    # LLM management
    "LLMPool",
    # Producer and ensemble
    "ProducerAgent",
    "ProducerConfig",
    "ProducerDecision_Result",
    "EnsembleRunner",
    "EnsembleConfig",
    "run_ensemble_critique",
]

__version__ = "0.1.0"
