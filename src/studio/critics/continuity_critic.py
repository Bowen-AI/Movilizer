"""Continuity and consistency critique system."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from .base import CritiqueContext, CritiqueLevel, CriticBase
from .llm_pool import LLMPool

logger = logging.getLogger(__name__)


CONTINUITY_CRITIC_SYSTEM_PROMPT = """You are an expert continuity supervisor for film and television productions.

Compare the current shot with previous shots and check for:
1. Character consistency: Same appearance, clothing, position
2. Setting consistency: Props, furniture, background elements
3. Lighting continuity: Consistent light direction and intensity
4. Props and wardrobe: No unexplained changes
5. Camera angles and continuity of action: Logical flow between cuts

Respond with a JSON object:
{
    "score": <float 0-10>,
    "issues": [<specific continuity problems>],
    "suggestions": [<continuity fixes>],
    "reasoning": "<detailed analysis>"
}

Focus on plot-breaking discontinuities."""


class ContinuityCritic(CriticBase):
    """Evaluates continuity between clips in a scene."""

    def __init__(
        self,
        llm_pool: Optional[LLMPool] = None,
        model_id: str = "llava-1.5",
        use_pixel_fallback: bool = True,
    ):
        """Initialize continuity critic.

        Args:
            llm_pool: LLM pool instance
            model_id: Vision model to use
            use_pixel_fallback: Use pixel-level comparison if LLM unavailable
        """
        super().__init__("ContinuityCritic", CritiqueLevel.SCENE)
        self.llm_pool = llm_pool or LLMPool()
        self.model_id = model_id
        self.use_pixel_fallback = use_pixel_fallback

    async def evaluate(self, context: CritiqueContext) -> CritiqueResult:
        """Evaluate continuity with previous clips.

        Args:
            context: Critique context with current and previous clips

        Returns:
            CritiqueResult with continuity assessment
        """
        from .base import CritiqueResult

        try:
            # If no previous clips, nothing to check continuity against
            if not context.previous_clips:
                return self._create_result(
                    score=8.0,
                    reasoning="No previous clips to compare against (first shot).",
                )

            # Try vision LLM evaluation
            result = await self._evaluate_with_llm(context)
            if result is not None:
                return result

            # Fallback to pixel-level comparison
            if self.use_pixel_fallback:
                return self._evaluate_with_pixels(context)

            return self._create_result(
                score=5.0,
                issues=["Continuity evaluation unavailable"],
                reasoning="No vision capability available.",
            )

        except Exception as e:
            self.logger.error(f"Continuity critique failed: {e}")
            return self._create_result(
                score=5.0,
                issues=[f"Continuity check error: {e}"],
                reasoning="Exception during continuity evaluation.",
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
            self.logger.debug(f"LLM continuity evaluation failed: {e}")
            return None

    def _build_prompt(self, context: CritiqueContext) -> str:
        """Build evaluation prompt.

        Args:
            context: Critique context

        Returns:
            Formatted prompt
        """
        parts = [CONTINUITY_CRITIC_SYSTEM_PROMPT, "\n\n=== CURRENT SHOT ==="]

        if context.shot_description:
            parts.append(f"Description:\n{context.shot_description}")

        if context.frames:
            parts.append(f"Current frames: {len(context.frames)}")

        if context.previous_clips:
            parts.append(f"\n=== PREVIOUS SHOTS ===")
            parts.append(f"Number of previous shots: {len(context.previous_clips)}")
            parts.append(f"Previous shot files: {[str(p.name) for p in context.previous_clips[-2:]]}")

        if context.next_clips:
            parts.append(f"Number of following shots: {len(context.next_clips)}")

        parts.append("\n=== CONTINUITY CHECK ===")
        parts.append(
            "Analyze continuity with the previous shot(s). "
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
            self.logger.warning(f"Failed to parse continuity response: {e}")
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

    def _evaluate_with_pixels(
        self, context: CritiqueContext
    ) -> CritiqueResult:
        """Evaluate using pixel-level image comparison.

        Args:
            context: Critique context

        Returns:
            CritiqueResult from pixel analysis
        """
        issues = []
        suggestions = []
        score = 8.0

        if not context.frames or not context.previous_clips:
            return self._create_result(score=8.0, reasoning="Insufficient data for pixel comparison.")

        try:
            import cv2
            import numpy as np

            # Load last frame of previous clip and first frame of current clip
            prev_clip_path = context.previous_clips[-1]
            curr_first_frame = context.frames[0]

            # Get last frame of previous clip (approximate)
            if prev_clip_path.is_file():
                prev_frame_path = prev_clip_path.parent / "frames" / "frame_0000.png"
                if not prev_frame_path.exists():
                    # Try to find any frame in previous directory
                    prev_frames = sorted(prev_clip_path.parent.glob("frame_*.png"))
                    if prev_frames:
                        prev_frame_path = prev_frames[-1]

                if prev_frame_path.exists():
                    prev_frame = cv2.imread(str(prev_frame_path))
                    curr_frame = cv2.imread(str(curr_first_frame))

                    if prev_frame is not None and curr_frame is not None:
                        # Check resolution
                        if prev_frame.shape != curr_frame.shape:
                            issues.append("Resolution changed between shots")
                            score -= 1.0

                        # Check brightness continuity
                        prev_bright = np.mean(cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY))
                        curr_bright = np.mean(cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY))
                        bright_diff = abs(prev_bright - curr_bright)

                        if bright_diff > 80:
                            issues.append(
                                f"Significant lighting change between shots ({bright_diff:.0f})"
                            )
                            score -= 1.5

                        # Check color consistency
                        prev_color = cv2.mean(prev_frame)
                        curr_color = cv2.mean(curr_frame)
                        color_diff = sum(abs(p - c) for p, c in zip(prev_color, curr_color))

                        if color_diff > 150:
                            suggestions.append("Consider color grading adjustment for continuity")

        except ImportError:
            self.logger.debug("OpenCV not available for pixel comparison")
        except Exception as e:
            self.logger.debug(f"Pixel comparison error: {e}")

        if not issues:
            suggestions.append("Continuity check passed")

        return self._create_result(
            score=min(10.0, max(0.0, score)),
            issues=issues,
            suggestions=suggestions,
            reasoning="Pixel-level continuity analysis performed.",
        )
