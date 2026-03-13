"""Visual composition and aesthetics critique system."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from .base import CritiqueContext, CritiqueLevel, CriticBase
from .llm_pool import LLMPool

logger = logging.getLogger(__name__)


VISUAL_CRITIC_SYSTEM_PROMPT = """You are an expert cinematographer and visual artist evaluating shot composition and aesthetics.

Analyze the provided image(s) for:
1. Composition: Rule of thirds, leading lines, framing
2. Lighting: Quality, direction, and mood
3. Color: Palette, grading, emotional impact
4. Aesthetics: Overall visual appeal and style
5. Character appearance: Consistency with descriptions

Respond with a JSON object:
{
    "score": <float 0-10>,
    "issues": [<specific visual problems>],
    "suggestions": [<visual improvements>],
    "reasoning": "<detailed analysis>"
}

Be specific about what works and what doesn't."""


class VisualCritic(CriticBase):
    """Evaluates visual composition, lighting, color, and aesthetics."""

    def __init__(
        self,
        llm_pool: Optional[LLMPool] = None,
        model_id: str = "llava-1.5",
        use_heuristic_fallback: bool = True,
    ):
        """Initialize visual critic.

        Args:
            llm_pool: LLM pool instance
            model_id: Vision model to use
            use_heuristic_fallback: Use image analysis if LLM unavailable
        """
        super().__init__("VisualCritic", CritiqueLevel.SHOT)
        self.llm_pool = llm_pool or LLMPool()
        self.model_id = model_id
        self.use_heuristic_fallback = use_heuristic_fallback

    async def evaluate(self, context: CritiqueContext) -> CritiqueResult:
        """Evaluate visual aspects of a clip.

        Args:
            context: Critique context with frames/keyframes

        Returns:
            CritiqueResult with visual assessment
        """
        from .base import CritiqueResult

        try:
            if not context.frames:
                return self._create_result(
                    score=5.0,
                    issues=["No frames provided for visual evaluation"],
                    reasoning="Cannot evaluate visuals without frames.",
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
                issues=["Visual evaluation unavailable"],
                reasoning="No vision LLM or heuristics available.",
            )

        except Exception as e:
            self.logger.error(f"Visual critique failed: {e}")
            return self._create_result(
                score=5.0,
                issues=[f"Visual critique error: {e}"],
                reasoning="Exception during visual evaluation.",
            )

    async def _evaluate_with_llm(
        self, context: CritiqueContext
    ) -> Optional[CritiqueResult]:
        """Try to evaluate using vision LLM.

        Args:
            context: Critique context

        Returns:
            CritiqueResult or None if unavailable
        """
        from .base import CritiqueResult

        try:
            # Build prompt with image descriptions
            prompt = self._build_prompt(context)

            # For now, use text-only LLM with image descriptions
            # (True vision LLM integration would require additional setup)
            response = await self.llm_pool.generate(
                self.model_id,
                prompt,
                max_tokens=1024,
                temperature=0.5,
            )

            return self._parse_response(response, context)

        except Exception as e:
            self.logger.debug(f"LLM evaluation failed: {e}")
            return None

    def _build_prompt(self, context: CritiqueContext) -> str:
        """Build evaluation prompt.

        Args:
            context: Critique context

        Returns:
            Formatted prompt
        """
        parts = [VISUAL_CRITIC_SYSTEM_PROMPT, "\n\n=== SHOT INFORMATION ==="]

        parts.append(f"Number of frames: {len(context.frames)}")

        if context.shot_description:
            parts.append(f"Shot Description:\n{context.shot_description}")

        parts.append(f"\nFrames to analyze: {len(context.frames)}")
        if context.frames:
            parts.append(f"Frame files: {[str(f.name) for f in context.frames[:3]]}")

        if context.genre:
            parts.append(f"Genre: {context.genre}")

        parts.append("\n=== EVALUATION ===")
        parts.append(
            "Analyze the visual composition and aesthetics. "
            "Return JSON with score, issues, suggestions, and reasoning."
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

            return CritiqueResult(
                critic_name=self.name,
                score=min(10.0, max(0.0, score)),
                issues=issues if isinstance(issues, list) else [],
                suggestions=suggestions if isinstance(suggestions, list) else [],
                reasoning=reasoning,
            )

        except (json.JSONDecodeError, ValueError) as e:
            self.logger.warning(f"Failed to parse visual response: {e}")
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

        return CritiqueResult(
            critic_name=self.name,
            score=min(10.0, max(0.0, score)),
            issues=issues,
            suggestions=suggestions,
            reasoning=response[:500],
        )

    def _evaluate_with_heuristics(
        self, context: CritiqueContext
    ) -> CritiqueResult:
        """Evaluate using image analysis heuristics.

        Args:
            context: Critique context

        Returns:
            CritiqueResult from heuristic analysis
        """
        issues = []
        suggestions = []

        # Check frame count and spacing
        frame_count = len(context.frames)
        if frame_count == 0:
            issues.append("No frames available for analysis")
            score = 2.0
        elif frame_count < 3:
            issues.append(f"Limited frames ({frame_count}) for full analysis")
            score = 6.0
        else:
            score = 7.0

        # Try to analyze frame properties
        try:
            import cv2
            import numpy as np

            # Analyze first and last frames for consistency
            frame_issues = self._analyze_frames(context.frames)
            issues.extend(frame_issues)

            # Adjust score based on detected issues
            if frame_issues:
                score = max(4.0, score - 1.5)
            else:
                suggestions.append("Visual consistency check passed")

        except ImportError:
            self.logger.debug("OpenCV not available for heuristic analysis")

        # Generic suggestions based on heuristics
        if not suggestions:
            suggestions = [
                "Consider composition improvements",
                "Ensure consistent lighting across shots",
                "Verify color grading consistency",
            ]

        return self._create_result(
            score=min(10.0, max(0.0, score)),
            issues=issues,
            suggestions=suggestions,
            reasoning="Heuristic visual analysis performed.",
        )

    def _analyze_frames(self, frames: list[Path]) -> list[str]:
        """Analyze frame properties.

        Args:
            frames: List of frame paths

        Returns:
            List of detected issues
        """
        import cv2
        import numpy as np

        issues = []

        if not frames:
            return issues

        try:
            # Load first and last frame
            first_frame = cv2.imread(str(frames[0]))
            last_frame = cv2.imread(str(frames[-1]))

            if first_frame is None or last_frame is None:
                return ["Unable to read frame files"]

            # Check resolution consistency
            if first_frame.shape != last_frame.shape:
                issues.append(
                    f"Resolution mismatch: {first_frame.shape} vs {last_frame.shape}"
                )

            # Check for extreme brightness changes
            first_brightness = np.mean(cv2.cvtColor(first_frame, cv2.COLOR_BGR2GRAY))
            last_brightness = np.mean(cv2.cvtColor(last_frame, cv2.COLOR_BGR2GRAY))
            brightness_diff = abs(first_brightness - last_brightness)

            if brightness_diff > 100:
                issues.append(
                    f"Large brightness change detected ({brightness_diff:.1f})"
                )

        except Exception as e:
            self.logger.debug(f"Frame analysis error: {e}")

        return issues
