"""Cinematographic and directorial critique system."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from .base import CritiqueContext, CritiqueLevel, CriticBase
from .llm_pool import LLMPool

logger = logging.getLogger(__name__)


DIRECTOR_CRITIC_SYSTEM_PROMPT = """You are an expert cinematographer and film director evaluating cinematic language and visual storytelling.

Analyze the shot for:
1. Composition: Rule of thirds, symmetry, framing, depth
2. Camera angle: Establishing, medium, close-up; high/low angles for emotional effect
3. Leading lines: Visual paths that guide viewer's eye
4. Visual storytelling: How does framing convey narrative/emotion?
5. Cinematic technique: Focus, motion, staging for dramatic effect

Respond with JSON:
{
    "score": <float 0-10>,
    "cinematic_quality": "<assessment of directorial choices>",
    "composition_score": <float 0-10>,
    "issues": [<directorial/composition problems>],
    "suggestions": [<improvements to cinematic language>],
    "reasoning": "<detailed cinematographic analysis>"
}

Focus on visual storytelling effectiveness."""


class DirectorCritic(CriticBase):
    """Evaluates cinematic language, composition, and directorial choices."""

    def __init__(
        self,
        llm_pool: Optional[LLMPool] = None,
        model_id: str = "llava-1.5",
        use_heuristic_fallback: bool = True,
    ):
        """Initialize director critic.

        Args:
            llm_pool: LLM pool instance
            model_id: Vision model to use
            use_heuristic_fallback: Use heuristic analysis if LLM unavailable
        """
        super().__init__("DirectorCritic", CritiqueLevel.SHOT)
        self.llm_pool = llm_pool or LLMPool()
        self.model_id = model_id
        self.use_heuristic_fallback = use_heuristic_fallback

    async def evaluate(self, context: CritiqueContext) -> CritiqueResult:
        """Evaluate cinematic aspects of a clip.

        Args:
            context: Critique context with frames

        Returns:
            CritiqueResult with cinematic assessment
        """
        from .base import CritiqueResult

        try:
            if not context.frames:
                return self._create_result(
                    score=5.0,
                    issues=["No frames provided for cinematic evaluation"],
                    reasoning="Cannot evaluate cinematography without frames.",
                )

            # Try vision LLM first
            result = await self._evaluate_with_llm(context)
            if result is not None:
                return result

            # Fallback to heuristic analysis
            if self.use_heuristic_fallback:
                return self._evaluate_with_heuristics(context)

            return self._create_result(
                score=5.0,
                issues=["Cinematic evaluation unavailable"],
                reasoning="No vision LLM available.",
            )

        except Exception as e:
            self.logger.error(f"Director critique failed: {e}")
            return self._create_result(
                score=5.0,
                issues=[f"Director evaluation error: {e}"],
                reasoning="Exception during cinematographic evaluation.",
            )

    async def _evaluate_with_llm(
        self, context: CritiqueContext
    ) -> Optional[CritiqueResult]:
        """Evaluate using vision LLM.

        Args:
            context: Critique context

        Returns:
            CritiqueResult or None if unavailable
        """
        from .base import CritiqueResult

        try:
            prompt = self._build_prompt(context)

            response = await self.llm_pool.generate(
                self.model_id,
                prompt,
                max_tokens=1024,
                temperature=0.5,
            )

            return self._parse_response(response, context)

        except Exception as e:
            self.logger.debug(f"LLM director evaluation failed: {e}")
            return None

    def _build_prompt(self, context: CritiqueContext) -> str:
        """Build evaluation prompt.

        Args:
            context: Critique context

        Returns:
            Formatted prompt
        """
        parts = [DIRECTOR_CRITIC_SYSTEM_PROMPT, "\n\n=== SHOT INFORMATION ==="]

        if context.shot_description:
            parts.append(f"Shot Description:\n{context.shot_description}")

        parts.append(f"Number of frames: {len(context.frames)}")

        if context.genre:
            parts.append(f"Genre: {context.genre}")

        if context.tone:
            parts.append(f"Emotional Tone: {context.tone}")

        parts.append("\n=== CINEMATOGRAPHIC EVALUATION ===")
        parts.append(
            "Analyze the cinematic language and directorial choices. "
            "Return JSON with score, composition assessment, issues, suggestions, and reasoning."
        )

        return "\n".join(parts)

    def _parse_response(
        self, response: str, context: CritiqueContext
    ) -> CritiqueResult:
        """Parse LLM response.

        Args:
            response: LLM response text
            context: Critique context

        Returns:
            Parsed CritiqueResult
        """
        from .base import CritiqueResult

        try:
            json_match = re.search(r"\{[\s\S]*\}", response)
            if not json_match:
                return self._parse_text_response(response)

            data = json.loads(json_match.group())
            score = float(data.get("score", 6.0))
            issues = data.get("issues", [])
            suggestions = data.get("suggestions", [])
            reasoning = data.get("reasoning", "")

            metadata = {
                "cinematic_quality": data.get("cinematic_quality", ""),
                "composition_score": data.get("composition_score", score),
            }

            return CritiqueResult(
                critic_name=self.name,
                score=min(10.0, max(0.0, score)),
                issues=issues if isinstance(issues, list) else [],
                suggestions=suggestions if isinstance(suggestions, list) else [],
                reasoning=reasoning,
                metadata=metadata,
            )

        except (json.JSONDecodeError, ValueError) as e:
            self.logger.warning(f"Failed to parse director response: {e}")
            return self._parse_text_response(response)

    def _parse_text_response(self, response: str) -> CritiqueResult:
        """Parse text response.

        Args:
            response: LLM response text

        Returns:
            Parsed CritiqueResult
        """
        from .base import CritiqueResult

        score_match = re.search(r"score[:\s]+(\d+\.?\d*)", response, re.I)
        score = 6.0
        if score_match:
            try:
                score = float(score_match.group(1))
            except ValueError:
                pass

        composition_match = re.search(
            r"composition[_\s]score[:\s]+(\d+\.?\d*)", response, re.I
        )
        composition = score
        if composition_match:
            try:
                composition = float(composition_match.group(1))
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

        cinematic_match = re.search(
            r"cinematic[_\s]quality[:\s]+([^\n]+)", response, re.I
        )
        cinematic = cinematic_match.group(1) if cinematic_match else ""

        return CritiqueResult(
            critic_name=self.name,
            score=min(10.0, max(0.0, score)),
            issues=issues,
            suggestions=suggestions,
            reasoning=response[:500],
            metadata={
                "cinematic_quality": cinematic,
                "composition_score": composition,
            },
        )

    def _evaluate_with_heuristics(
        self, context: CritiqueContext
    ) -> CritiqueResult:
        """Evaluate using composition heuristics.

        Args:
            context: Critique context

        Returns:
            CritiqueResult from heuristic analysis
        """
        issues = []
        suggestions = []
        score = 7.0

        try:
            import cv2
            import numpy as np

            if not context.frames:
                return self._create_result(
                    score=5.0,
                    reasoning="No frames for heuristic analysis.",
                )

            frame = cv2.imread(str(context.frames[0]))
            if frame is None:
                issues.append("Cannot read frame file")
                return self._create_result(
                    score=4.0,
                    issues=issues,
                    reasoning="Failed to load frame for analysis.",
                )

            height, width = frame.shape[:2]

            # Rule of thirds analysis (simple heuristic)
            third_h = height // 3
            third_w = width // 3

            # Analyze center of mass
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            moments = cv2.moments(binary)

            if moments["m00"] > 0:
                cx = int(moments["m10"] / moments["m00"])
                cy = int(moments["m01"] / moments["m00"])

                # Check if subject is on rule of thirds lines
                thirds_w = [third_w, 2 * third_w]
                thirds_h = [third_h, 2 * third_h]

                on_third = any(
                    abs(cx - tw) < width * 0.15 for tw in thirds_w
                ) or any(abs(cy - th) < height * 0.15 for th in thirds_h)

                if on_third:
                    suggestions.append("Good composition: subject on rule of thirds")
                else:
                    suggestions.append(
                        "Consider recomposing to follow rule of thirds"
                    )

            # Color analysis (palette consistency)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hue = hsv[:, :, 0]
            dominant_hue = np.argmax(np.histogram(hue, 180)[0])

            suggestions.append(f"Color palette: dominant hue region ~{dominant_hue * 2}°")

            # Check for proper exposure
            brightness = np.mean(gray)
            if brightness < 50:
                issues.append("Image appears underexposed")
                score -= 1.0
            elif brightness > 200:
                issues.append("Image appears overexposed")
                score -= 1.0

            # Depth analysis (edge distribution)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            if edge_density < 0.01:
                suggestions.append("Limited depth cues; consider adding background variation")
            elif edge_density > 0.3:
                suggestions.append("High visual complexity; ensure clarity for primary subject")

        except ImportError:
            logger.debug("OpenCV not available for heuristic analysis")
        except Exception as e:
            logger.debug(f"Heuristic analysis error: {e}")

        if not suggestions:
            suggestions = [
                "Composition analysis completed",
                "Review lighting and framing",
            ]

        return self._create_result(
            score=min(10.0, max(0.0, score)),
            issues=issues,
            suggestions=suggestions,
            reasoning="Heuristic cinematographic analysis performed.",
        )
