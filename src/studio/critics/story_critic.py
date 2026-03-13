"""Story and narrative critique system."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from .base import CritiqueContext, CritiqueLevel, CriticBase
from .llm_pool import LLMPool

logger = logging.getLogger(__name__)


STORY_CRITIC_SYSTEM_PROMPT = """You are an expert film critic specializing in narrative analysis, dialogue quality, character development, and emotional arcs.

Your task is to evaluate a scene or shot for:
1. Narrative coherence: Does the scene follow logically from context?
2. Pacing: Is the rhythm appropriate for the content?
3. Dialogue quality: Are character voices distinct and natural?
4. Emotional arc: Does the scene effectively convey intended emotions?
5. Character consistency: Do characters act true to their established personalities?

Respond with a JSON object containing:
{
    "score": <float 0-10>,
    "issues": [<list of specific problems found>],
    "suggestions": [<list of actionable improvements>],
    "reasoning": "<detailed explanation of score>"
}

Be constructive and specific. Focus on narrative impact."""


class StoryCritic(CriticBase):
    """Evaluates narrative coherence, pacing, dialogue, and emotional arcs."""

    def __init__(
        self,
        llm_pool: Optional[LLMPool] = None,
        model_id: str = "mistral-7b",
    ):
        """Initialize story critic.

        Args:
            llm_pool: LLM pool instance (creates new one if None)
            model_id: Model to use for critique
        """
        super().__init__("StoryCritic", CritiqueLevel.SHOT)
        self.llm_pool = llm_pool or LLMPool()
        self.model_id = model_id

    async def evaluate(self, context: CritiqueContext) -> CritiqueResult:
        """Evaluate narrative aspects of a clip.

        Args:
            context: Critique context with script and descriptions

        Returns:
            CritiqueResult with narrative assessment
        """
        from .base import CritiqueResult

        try:
            # Build comprehensive prompt with context
            prompt = self._build_prompt(context)

            # Generate critique via LLM
            response = await self.llm_pool.generate(
                self.model_id,
                prompt,
                max_tokens=1024,
                temperature=0.5,  # Lower temperature for consistent analysis
            )

            # Parse response
            result = self._parse_response(response, context)
            return result

        except Exception as e:
            self.logger.error(f"Story critique failed: {e}")
            # Return middle-ground critique on failure
            return self._create_result(
                score=5.0,
                issues=[f"Critique evaluation failed: {e}"],
                reasoning="Unable to evaluate narrative due to error.",
            )

    def _build_prompt(self, context: CritiqueContext) -> str:
        """Build the evaluation prompt.

        Args:
            context: Critique context

        Returns:
            Formatted prompt for LLM
        """
        parts = [STORY_CRITIC_SYSTEM_PROMPT, "\n\n=== SHOT INFORMATION ==="]

        if context.shot_description:
            parts.append(f"Visual Description:\n{context.shot_description}")

        if context.script:
            parts.append(f"Script/Dialogue:\n{context.script}")

        if context.genre:
            parts.append(f"Genre: {context.genre}")

        if context.tone:
            parts.append(f"Intended Tone: {context.tone}")

        # Add scene context
        if context.previous_clips or context.next_clips:
            parts.append("\n=== SCENE CONTEXT ===")
            if context.previous_clips:
                parts.append(
                    f"Previous shots in scene: {len(context.previous_clips)}"
                )
            if context.next_clips:
                parts.append(f"Following shots in scene: {len(context.next_clips)}")

        parts.append("\n=== EVALUATION ===")
        parts.append(
            "Provide detailed narrative critique in the specified JSON format."
        )

        return "\n".join(parts)

    def _parse_response(
        self, response: str, context: CritiqueContext
    ) -> CritiqueResult:
        """Parse LLM response into CritiqueResult.

        Args:
            response: LLM response text
            context: Critique context

        Returns:
            Parsed CritiqueResult
        """
        from .base import CritiqueResult

        try:
            # Extract JSON from response (may be wrapped in other text)
            json_match = re.search(r"\{[\s\S]*\}", response)
            if not json_match:
                # Fallback: try to construct from response text
                return self._parse_text_response(response, context)

            json_str = json_match.group()
            data = json.loads(json_str)

            score = float(data.get("score", 5.0))
            issues = data.get("issues", [])
            suggestions = data.get("suggestions", [])
            reasoning = data.get("reasoning", "")

            return CritiqueResult(
                critic_name=self.name,
                score=min(10.0, max(0.0, score)),  # Clamp to 0-10
                issues=issues if isinstance(issues, list) else [],
                suggestions=suggestions if isinstance(suggestions, list) else [],
                reasoning=reasoning,
            )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            self.logger.warning(f"Failed to parse JSON response: {e}")
            return self._parse_text_response(response, context)

    def _parse_text_response(
        self, response: str, context: CritiqueContext
    ) -> CritiqueResult:
        """Parse free-text response from LLM.

        Args:
            response: LLM response text
            context: Critique context

        Returns:
            Parsed CritiqueResult
        """
        from .base import CritiqueResult

        # Extract score if present
        score_match = re.search(r"score[:\s]+(\d+\.?\d*)", response, re.I)
        score = 5.0
        if score_match:
            try:
                score = float(score_match.group(1))
            except ValueError:
                pass

        # Extract issues
        issues = []
        issues_match = re.search(
            r"issues?[:\s]*\n?((?:[-*]\s*.+\n?)+)", response, re.I
        )
        if issues_match:
            issue_text = issues_match.group(1)
            issues = [
                line.strip("- * ")
                for line in issue_text.split("\n")
                if line.strip()
            ]

        # Extract suggestions
        suggestions = []
        suggestions_match = re.search(
            r"suggestions?[:\s]*\n?((?:[-*]\s*.+\n?)+)", response, re.I
        )
        if suggestions_match:
            sugg_text = suggestions_match.group(1)
            suggestions = [
                line.strip("- * ")
                for line in sugg_text.split("\n")
                if line.strip()
            ]

        return CritiqueResult(
            critic_name=self.name,
            score=min(10.0, max(0.0, score)),
            issues=issues,
            suggestions=suggestions,
            reasoning=response[:500],  # First 500 chars as reasoning
        )
