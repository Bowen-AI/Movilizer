"""Audience engagement and emotional response critique system."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from .base import CritiqueContext, CritiqueLevel, CriticBase
from .llm_pool import LLMPool

logger = logging.getLogger(__name__)


# Different personas for audience simulation
AUDIENCE_PERSONAS = {
    "general": """You are evaluating this scene for a general mainstream audience.
Focus on broad appeal, emotional engagement, and entertainment value.
Would typical viewers find this engaging and emotionally resonant?""",
    "critic": """You are a professional film critic evaluating craft and artistic merit.
Focus on storytelling sophistication, acting quality, directorial choices, and originality.
Does this demonstrate strong filmmaking?""",
    "genre_fan": """You are an enthusiast of the film's genre (action, romance, horror, etc).
Focus on genre conventions, tropes, and whether it delivers expected elements well.
Does this satisfy genre expectations and deliver the goods fans want?""",
    "casual": """You are a casual viewer watching for fun without high expectations.
Focus on whether the scene is entertaining, whether you'd keep watching.
Is this fun? Would you stay interested?""",
}


def get_audience_prompt(persona_key: str, context: CritiqueContext) -> str:
    """Get persona-specific prompt for audience critique.

    Args:
        persona_key: Key into AUDIENCE_PERSONAS
        context: Critique context

    Returns:
        Formatted system prompt
    """
    base_prompt = AUDIENCE_PERSONAS.get(
        persona_key, AUDIENCE_PERSONAS["general"]
    )

    return f"""{base_prompt}

Scene/Shot Information:
- Genre: {context.genre or "Not specified"}
- Tone: {context.tone or "Not specified"}
- Description: {context.shot_description or "No description"}

Evaluate for engagement, emotional impact, and audience satisfaction.

Respond with JSON:
{{
    "score": <float 0-10 for engagement>,
    "engagement": <float 0-10 predicted engagement level>,
    "emotional_impact": "<prediction of emotional response>",
    "issues": [<what might turn off audience>],
    "suggestions": [<improvements for audience appeal>],
    "reasoning": "<why this would or wouldn't work for this audience>"
}}"""


class AudienceCritic(CriticBase):
    """Role-plays different audience segments and predicts engagement."""

    def __init__(
        self,
        llm_pool: Optional[LLMPool] = None,
        model_id: str = "mistral-7b",
        personas: Optional[list[str]] = None,
    ):
        """Initialize audience critic.

        Args:
            llm_pool: LLM pool instance
            model_id: Model to use
            personas: Audience personas to simulate (default: all)
        """
        super().__init__("AudienceCritic", CritiqueLevel.SHOT)
        self.llm_pool = llm_pool or LLMPool()
        self.model_id = model_id
        self.personas = personas or list(AUDIENCE_PERSONAS.keys())

    async def evaluate(self, context: CritiqueContext) -> CritiqueResult:
        """Evaluate audience appeal across different personas.

        Args:
            context: Critique context

        Returns:
            CritiqueResult with audience analysis
        """
        from .base import CritiqueResult

        try:
            # Evaluate with each persona
            persona_results = {}
            for persona in self.personas:
                result = await self._evaluate_persona(persona, context)
                persona_results[persona] = result

            # Aggregate results
            return self._aggregate_results(persona_results, context)

        except Exception as e:
            self.logger.error(f"Audience critique failed: {e}")
            return self._create_result(
                score=5.0,
                issues=[f"Audience evaluation error: {e}"],
                reasoning="Exception during audience simulation.",
            )

    async def _evaluate_persona(
        self, persona: str, context: CritiqueContext
    ) -> dict[str, Any]:
        """Evaluate from a specific audience perspective.

        Args:
            persona: Audience persona key
            context: Critique context

        Returns:
            Persona-specific evaluation result
        """
        try:
            prompt = get_audience_prompt(persona, context)

            response = await self.llm_pool.generate(
                self.model_id,
                prompt,
                max_tokens=1024,
                temperature=0.7,  # Higher temperature for varied perspectives
            )

            return self._parse_persona_response(persona, response)

        except Exception as e:
            self.logger.warning(f"Persona evaluation failed for {persona}: {e}")
            return {
                "persona": persona,
                "score": 5.0,
                "engagement": 5.0,
                "error": str(e),
            }

    def _parse_persona_response(
        self, persona: str, response: str
    ) -> dict[str, Any]:
        """Parse persona evaluation response.

        Args:
            persona: Persona key
            response: LLM response

        Returns:
            Parsed persona result
        """
        try:
            json_match = re.search(r"\{[\s\S]*\}", response)
            if not json_match:
                return self._parse_text_persona_response(persona, response)

            data = json.loads(json_match.group())
            return {
                "persona": persona,
                "score": float(data.get("score", 5.0)),
                "engagement": float(data.get("engagement", 5.0)),
                "emotional_impact": data.get("emotional_impact", ""),
                "issues": data.get("issues", []),
                "suggestions": data.get("suggestions", []),
                "reasoning": data.get("reasoning", ""),
            }

        except (json.JSONDecodeError, ValueError) as e:
            self.logger.warning(f"Failed to parse {persona} response: {e}")
            return self._parse_text_persona_response(persona, response)

    def _parse_text_persona_response(
        self, persona: str, response: str
    ) -> dict[str, Any]:
        """Parse text persona response.

        Args:
            persona: Persona key
            response: LLM response

        Returns:
            Parsed persona result
        """
        score_match = re.search(r"score[:\s]+(\d+\.?\d*)", response, re.I)
        score = 5.0
        if score_match:
            try:
                score = float(score_match.group(1))
            except ValueError:
                pass

        engagement_match = re.search(
            r"engagement[:\s]+(\d+\.?\d*)", response, re.I
        )
        engagement = score
        if engagement_match:
            try:
                engagement = float(engagement_match.group(1))
            except ValueError:
                pass

        issues = []
        issues_match = re.search(
            r"issues?[:\s]*\n?((?:[-*]\s*.+\n?)+)", response, re.I
        )
        if issues_match:
            issues = [
                line.strip("- * ")
                for line in issues_match.group(1).split("\n")
                if line.strip()
            ]

        suggestions = []
        suggestions_match = re.search(
            r"suggestions?[:\s]*\n?((?:[-*]\s*.+\n?)+)", response, re.I
        )
        if suggestions_match:
            suggestions = [
                line.strip("- * ")
                for line in suggestions_match.group(1).split("\n")
                if line.strip()
            ]

        emotional_match = re.search(
            r"emotional[_\s]impact[:\s]+([^\n]+)", response, re.I
        )
        emotional = emotional_match.group(1) if emotional_match else ""

        return {
            "persona": persona,
            "score": min(10.0, max(0.0, score)),
            "engagement": min(10.0, max(0.0, engagement)),
            "emotional_impact": emotional,
            "issues": issues,
            "suggestions": suggestions,
            "reasoning": response[:300],
        }

    def _aggregate_results(
        self,
        persona_results: dict[str, dict[str, Any]],
        context: CritiqueContext,
    ) -> CritiqueResult:
        """Aggregate results from all personas.

        Args:
            persona_results: Results per persona
            context: Critique context

        Returns:
            Aggregated CritiqueResult
        """
        from .base import CritiqueResult

        # Calculate average scores
        scores = [
            r["score"]
            for r in persona_results.values()
            if "score" in r and "error" not in r
        ]
        engagements = [
            r["engagement"]
            for r in persona_results.values()
            if "engagement" in r and "error" not in r
        ]

        avg_score = sum(scores) / len(scores) if scores else 5.0
        avg_engagement = sum(engagements) / len(engagements) if engagements else 5.0

        # Collect all issues and suggestions
        all_issues = []
        all_suggestions = []
        emotional_impacts = []

        for result in persona_results.values():
            if "error" not in result:
                all_issues.extend(result.get("issues", []))
                all_suggestions.extend(result.get("suggestions", []))
                if result.get("emotional_impact"):
                    emotional_impacts.append(
                        f"{result['persona']}: {result['emotional_impact']}"
                    )

        # Remove duplicates while preserving order
        unique_issues = list(dict.fromkeys(all_issues))
        unique_suggestions = list(dict.fromkeys(all_suggestions))

        reasoning = f"Audience analysis across {len(persona_results)} personas. "
        reasoning += f"Average engagement: {avg_engagement:.1f}/10. "
        if emotional_impacts:
            reasoning += "Emotional responses: " + " | ".join(emotional_impacts)

        return CritiqueResult(
            critic_name=self.name,
            score=avg_score,
            issues=unique_issues[:5],  # Top issues
            suggestions=unique_suggestions[:5],  # Top suggestions
            reasoning=reasoning,
            metadata={
                "persona_results": persona_results,
                "avg_engagement": avg_engagement,
                "personas_evaluated": len(persona_results),
            },
        )
