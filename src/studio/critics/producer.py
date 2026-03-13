"""Producer agent that aggregates critiques and makes generation decisions."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from .base import CritiqueResult, ProducerDecision

logger = logging.getLogger(__name__)


@dataclass
class ProducerConfig:
    """Configuration for producer decision logic."""

    # Scoring thresholds
    approval_threshold: float = 7.0  # Score >= this → APPROVE
    critical_threshold: float = 4.0  # Score < this → REJECT
    revision_threshold: float = 7.0  # Between critical and approval → REVISE

    # Weights per critic (defaults to equal weighting)
    critic_weights: dict[str, float] = field(default_factory=dict)

    # Genre-specific weights
    genre_weights: dict[str, dict[str, float]] = field(default_factory=dict)

    # Maximum revision cycles
    max_revisions: int = 3

    # Require specific critics to pass
    required_critics: list[str] = field(default_factory=list)

    # Critic importance for veto (scores below threshold veto approval)
    veto_critics: dict[str, float] = field(default_factory=dict)

    def get_critic_weight(self, critic_name: str, genre: Optional[str] = None) -> float:
        """Get weight for a critic, considering genre.

        Args:
            critic_name: Name of critic
            genre: Optional genre for genre-specific weighting

        Returns:
            Weight value (default 1.0)
        """
        if genre and genre in self.genre_weights:
            return self.genre_weights[genre].get(critic_name, 1.0)
        return self.critic_weights.get(critic_name, 1.0)


@dataclass
class ProducerDecision_Result:
    """Producer's decision on a clip."""

    decision: ProducerDecision
    overall_score: float
    critic_scores: dict[str, float]
    reasoning: str
    revision_instructions: list[str] = field(default_factory=list)
    revision_count: int = 0


class ProducerAgent:
    """Aggregates critiques and makes generation decisions."""

    def __init__(self, config: Optional[ProducerConfig] = None):
        """Initialize producer agent.

        Args:
            config: Producer configuration
        """
        self.config = config or ProducerConfig()

    def decide(
        self,
        critiques: dict[str, CritiqueResult],
        genre: Optional[str] = None,
        revision_count: int = 0,
    ) -> ProducerDecision_Result:
        """Make a decision based on aggregate critique results.

        Args:
            critiques: Dict of critic_name -> CritiqueResult
            genre: Optional genre for weighted scoring
            revision_count: Number of revisions attempted so far

        Returns:
            ProducerDecision_Result with decision and instructions
        """
        # Calculate weighted average score
        overall_score = self._calculate_overall_score(critiques, genre)

        # Extract individual scores
        critic_scores = {
            name: result.score for name, result in critiques.items()
        }

        # Check veto conditions
        veto_decision = self._check_vetoes(critiques)
        if veto_decision is not None:
            return ProducerDecision_Result(
                decision=veto_decision,
                overall_score=overall_score,
                critic_scores=critic_scores,
                reasoning=f"Vetoed by low score on critical reviewer. Score: {overall_score:.1f}",
                revision_count=revision_count,
            )

        # Check revision limit
        if revision_count >= self.config.max_revisions:
            logger.warning(f"Maximum revisions ({self.config.max_revisions}) reached")
            return ProducerDecision_Result(
                decision=ProducerDecision.APPROVE,
                overall_score=overall_score,
                critic_scores=critic_scores,
                reasoning=f"Maximum revision cycles reached. Approving current best effort. Score: {overall_score:.1f}",
                revision_count=revision_count,
            )

        # Make decision based on scores
        decision, reasoning = self._make_decision(
            overall_score, critic_scores, revision_count
        )

        # Generate revision instructions if needed
        revision_instructions = []
        if decision == ProducerDecision.REVISE:
            revision_instructions = self._generate_revision_instructions(
                critiques
            )

        return ProducerDecision_Result(
            decision=decision,
            overall_score=overall_score,
            critic_scores=critic_scores,
            reasoning=reasoning,
            revision_instructions=revision_instructions,
            revision_count=revision_count,
        )

    def _calculate_overall_score(
        self,
        critiques: dict[str, CritiqueResult],
        genre: Optional[str] = None,
    ) -> float:
        """Calculate weighted average score.

        Args:
            critiques: Critique results
            genre: Optional genre

        Returns:
            Weighted average score
        """
        if not critiques:
            return 5.0

        total_weight = 0.0
        weighted_sum = 0.0

        for critic_name, result in critiques.items():
            weight = self.config.get_critic_weight(critic_name, genre)
            weighted_sum += result.score * weight
            total_weight += weight

        if total_weight == 0:
            return 5.0

        return weighted_sum / total_weight

    def _check_vetoes(
        self, critiques: dict[str, CritiqueResult]
    ) -> Optional[ProducerDecision]:
        """Check if any critic has veto power.

        Args:
            critiques: Critique results

        Returns:
            REJECT decision if veto triggered, None otherwise
        """
        for critic_name, veto_threshold in self.config.veto_critics.items():
            if critic_name in critiques:
                result = critiques[critic_name]
                if result.score < veto_threshold:
                    logger.info(
                        f"{critic_name} veto triggered (score {result.score:.1f} < {veto_threshold})"
                    )
                    return ProducerDecision.REJECT

        return None

    def _make_decision(
        self,
        overall_score: float,
        critic_scores: dict[str, float],
        revision_count: int,
    ) -> tuple[ProducerDecision, str]:
        """Decide based on aggregate score.

        Args:
            overall_score: Weighted average score
            critic_scores: Per-critic scores
            revision_count: Number of revisions so far

        Returns:
            Tuple of (decision, reasoning)
        """
        # Check if all high-threshold critics pass
        failed_critics = [
            name
            for name, score in critic_scores.items()
            if name in self.config.required_critics and score < self.config.approval_threshold
        ]

        if failed_critics:
            reasoning = (
                f"Required critics did not pass: {', '.join(failed_critics)}"
            )
            return ProducerDecision.REVISE, reasoning

        # Check for critical failures
        critical_failures = [
            name
            for name, score in critic_scores.items()
            if score < self.config.critical_threshold
        ]

        if critical_failures:
            reasoning = (
                f"Critical issues from {', '.join(critical_failures)}: "
                f"Score {overall_score:.1f}/10"
            )
            return ProducerDecision.REJECT, reasoning

        # Check for approval
        passing_count = sum(
            1
            for score in critic_scores.values()
            if score >= self.config.approval_threshold
        )
        total_count = len(critic_scores)

        if overall_score >= self.config.approval_threshold:
            if passing_count == total_count:
                reasoning = (
                    f"All critics satisfied. Score: {overall_score:.1f}/10"
                )
                return ProducerDecision.APPROVE, reasoning
            elif passing_count >= total_count * 0.75:
                # Most critics are happy
                reasoning = (
                    f"Most critics satisfied ({passing_count}/{total_count}). "
                    f"Score: {overall_score:.1f}/10"
                )
                return ProducerDecision.APPROVE, reasoning

        # Default to revision if we haven't hit limits
        if revision_count < self.config.max_revisions:
            reasoning = (
                f"Score {overall_score:.1f}/10 below approval threshold "
                f"({self.config.approval_threshold}). Revision {revision_count + 1}."
            )
            return ProducerDecision.REVISE, reasoning

        # Fallback to approval after max revisions
        reasoning = (
            f"Maximum revisions reached. Accepting current quality. "
            f"Score: {overall_score:.1f}/10"
        )
        return ProducerDecision.APPROVE, reasoning

    def _generate_revision_instructions(
        self, critiques: dict[str, CritiqueResult]
    ) -> list[str]:
        """Generate revision instructions from critique suggestions.

        Args:
            critiques: Critique results

        Returns:
            List of revision instructions
        """
        instructions = []
        instruction_priority = {}

        # Collect suggestions from all critics
        for critic_name, result in critiques.items():
            # Weight suggestions by inverse of score (lower score = higher priority)
            priority = 10.0 - result.score

            for suggestion in result.suggestions:
                key = suggestion.lower()
                if key not in instruction_priority or priority > instruction_priority[key][1]:
                    instruction_priority[key] = (suggestion, priority)

        # Sort by priority and return top instructions
        sorted_instructions = sorted(
            instruction_priority.values(),
            key=lambda x: x[1],
            reverse=True,
        )

        instructions = [inst[0] for inst in sorted_instructions[:5]]

        # Add explicit issue-based instructions
        for critic_name, result in critiques.items():
            if result.score < self.config.approval_threshold and result.issues:
                for issue in result.issues[:2]:  # Top 2 issues per critic
                    instructions.append(f"Fix: {issue}")

        return list(dict.fromkeys(instructions))[:10]  # Remove duplicates, limit to 10

    def export_decision(
        self, decision_result: ProducerDecision_Result
    ) -> str:
        """Export decision to JSON format.

        Args:
            decision_result: Producer decision result

        Returns:
            JSON string representation
        """
        return json.dumps(
            {
                "decision": decision_result.decision.value,
                "overall_score": decision_result.overall_score,
                "critic_scores": decision_result.critic_scores,
                "reasoning": decision_result.reasoning,
                "revision_instructions": decision_result.revision_instructions,
                "revision_count": decision_result.revision_count,
            },
            indent=2,
        )
