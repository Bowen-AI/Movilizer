"""Ensemble runner orchestrating all critics."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from .audience_critic import AudienceCritic
from .base import CritiqueContext, CritiqueLevel, CritiqueResult
from .continuity_critic import ContinuityCritic
from .director_critic import DirectorCritic
from .llm_pool import LLMPool
from .producer import ProducerAgent, ProducerConfig, ProducerDecision_Result
from .story_critic import StoryCritic
from .technical_critic import TechnicalCritic
from .visual_critic import VisualCritic

logger = logging.getLogger(__name__)


@dataclass
class EnsembleConfig:
    """Configuration for ensemble critique runner."""

    # Which critics to run
    critics: list[str] = field(
        default_factory=lambda: [
            "story",
            "visual",
            "technical",
            "director",
            "audience",
            "continuity",
        ]
    )

    # Critique level
    level: CritiqueLevel = CritiqueLevel.SHOT

    # Run critics in parallel
    parallel: bool = True

    # Producer configuration
    producer_config: Optional[ProducerConfig] = None

    # LLM settings
    use_mock_llm: bool = False
    default_model: str = "mistral-7b"


class EnsembleRunner:
    """Orchestrates running all critics on a clip."""

    def __init__(
        self,
        config: Optional[EnsembleConfig] = None,
        llm_pool: Optional[LLMPool] = None,
    ):
        """Initialize ensemble runner.

        Args:
            config: Ensemble configuration
            llm_pool: Shared LLM pool (creates new one if None)
        """
        self.config = config or EnsembleConfig()
        self.llm_pool = llm_pool or LLMPool(use_mock=self.config.use_mock_llm)
        self.producer = ProducerAgent(self.config.producer_config)

        # Initialize critics (lazy)
        self._critics = {}

    async def run(self, context: CritiqueContext) -> dict[str, Any]:
        """Run all critics on a clip and get producer decision.

        Args:
            context: Critique context with clip information

        Returns:
            Dict with critic_results and producer_decision
        """
        try:
            # Run all critics
            critique_results = await self._run_critics(context)

            logger.info(
                f"Completed critique of {context.shot} with "
                f"{len(critique_results)} critics"
            )

            # Get producer decision
            producer_decision = self.producer.decide(
                critique_results, genre=context.genre
            )

            return {
                "critic_results": critique_results,
                "producer_decision": producer_decision,
                "context": {
                    "run_id": context.run_id,
                    "project": context.project,
                    "scene": context.scene,
                    "shot": context.shot,
                },
            }

        except Exception as e:
            logger.error(f"Ensemble critique failed: {e}")
            raise

    async def _run_critics(
        self, context: CritiqueContext
    ) -> dict[str, CritiqueResult]:
        """Run all critics.

        Args:
            context: Critique context

        Returns:
            Dict of critic_name -> CritiqueResult
        """
        if self.config.parallel:
            return await self._run_critics_parallel(context)
        else:
            return await self._run_critics_sequential(context)

    async def _run_critics_parallel(
        self, context: CritiqueContext
    ) -> dict[str, CritiqueResult]:
        """Run critics in parallel using asyncio.

        Args:
            context: Critique context

        Returns:
            Dict of critic_name -> CritiqueResult
        """
        tasks = {}

        for critic_name in self.config.critics:
            critic = self._get_critic(critic_name)
            if critic:
                task = asyncio.create_task(critic.evaluate(context))
                tasks[critic_name] = task

        results = {}
        for critic_name, task in tasks.items():
            try:
                result = await task
                results[critic_name] = result
                logger.info(
                    f"{critic_name} critique: score {result.score:.1f}/10"
                )
            except Exception as e:
                logger.error(f"{critic_name} critique failed: {e}")

        return results

    async def _run_critics_sequential(
        self, context: CritiqueContext
    ) -> dict[str, CritiqueResult]:
        """Run critics sequentially.

        Args:
            context: Critique context

        Returns:
            Dict of critic_name -> CritiqueResult
        """
        results = {}

        for critic_name in self.config.critics:
            critic = self._get_critic(critic_name)
            if not critic:
                continue

            try:
                result = await critic.evaluate(context)
                results[critic_name] = result
                logger.info(
                    f"{critic_name} critique: score {result.score:.1f}/10"
                )
            except Exception as e:
                logger.error(f"{critic_name} critique failed: {e}")

        return results

    def _get_critic(self, critic_name: str) -> Optional[object]:
        """Get or initialize a critic by name.

        Args:
            critic_name: Name of critic

        Returns:
            Critic instance or None if unknown
        """
        if critic_name in self._critics:
            return self._critics[critic_name]

        critic = self._create_critic(critic_name)
        if critic:
            self._critics[critic_name] = critic

        return critic

    def _create_critic(self, critic_name: str) -> Optional[object]:
        """Create a critic instance.

        Args:
            critic_name: Name of critic

        Returns:
            Critic instance or None if unknown
        """
        try:
            if critic_name == "story":
                return StoryCritic(
                    llm_pool=self.llm_pool,
                    model_id=self.config.default_model,
                )
            elif critic_name == "visual":
                return VisualCritic(
                    llm_pool=self.llm_pool,
                    model_id=self.config.default_model,
                )
            elif critic_name == "continuity":
                return ContinuityCritic(
                    llm_pool=self.llm_pool,
                    model_id=self.config.default_model,
                )
            elif critic_name == "audience":
                return AudienceCritic(
                    llm_pool=self.llm_pool,
                    model_id=self.config.default_model,
                )
            elif critic_name == "technical":
                return TechnicalCritic()
            elif critic_name == "director":
                return DirectorCritic(
                    llm_pool=self.llm_pool,
                    model_id=self.config.default_model,
                )
            else:
                logger.warning(f"Unknown critic: {critic_name}")
                return None

        except Exception as e:
            logger.error(f"Failed to create {critic_name} critic: {e}")
            return None

    async def shutdown(self) -> None:
        """Shutdown LLM pool and resources."""
        await self.llm_pool.shutdown()
        logger.info("Ensemble runner shutdown complete")

    def reset_critics(self) -> None:
        """Reset all critic instances."""
        self._critics.clear()
        logger.info("Critics reset")


async def run_ensemble_critique(
    context: CritiqueContext,
    config: Optional[EnsembleConfig] = None,
) -> dict[str, Any]:
    """Convenience function to run ensemble critique.

    Args:
        context: Critique context
        config: Optional ensemble config

    Returns:
        Dict with critique results and producer decision
    """
    runner = EnsembleRunner(config=config)
    try:
        return await runner.run(context)
    finally:
        await runner.shutdown()
