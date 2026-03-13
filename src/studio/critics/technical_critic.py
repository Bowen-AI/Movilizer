"""Technical quality critique system."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from .base import CritiqueContext, CritiqueLevel, CriticBase

logger = logging.getLogger(__name__)


class TechnicalCritic(CriticBase):
    """Evaluates technical quality: artifacts, flicker, resolution, audio, etc."""

    def __init__(self, check_audio: bool = True, min_resolution: tuple[int, int] = (1280, 720)):
        """Initialize technical critic.

        Args:
            check_audio: Check for audio issues
            min_resolution: Minimum acceptable resolution
        """
        super().__init__("TechnicalCritic", CritiqueLevel.SHOT)
        self.check_audio = check_audio
        self.min_resolution = min_resolution

    async def evaluate(self, context: CritiqueContext) -> CritiqueResult:
        """Evaluate technical aspects of a clip.

        Args:
            context: Critique context with clip path and frames

        Returns:
            CritiqueResult with technical assessment
        """
        from .base import CritiqueResult

        issues = []
        suggestions = []
        score = 10.0  # Start with perfect and deduct for issues

        try:
            # Check frames
            if context.frames:
                frame_issues, frame_deduction = await self._check_frames(context)
                issues.extend(frame_issues)
                score -= frame_deduction

            # Check clip file
            if context.clip_path and context.clip_path.exists():
                clip_issues, clip_deduction = await self._check_clip(context)
                issues.extend(clip_issues)
                score -= clip_deduction

            # Check audio if requested
            if self.check_audio and context.clip_path:
                audio_issues, audio_deduction = await self._check_audio(context)
                issues.extend(audio_issues)
                score -= audio_deduction

            # Generate suggestions based on issues
            if "flicker" in str(issues):
                suggestions.append("Stabilize frames or increase keyframe interval")
            if "resolution" in str(issues).lower():
                suggestions.append(f"Ensure output meets {self.min_resolution} minimum")
            if "artifact" in str(issues).lower():
                suggestions.append("Review compression settings or source quality")
            if not suggestions:
                suggestions.append("Technical quality check passed")

            return self._create_result(
                score=min(10.0, max(0.0, score)),
                issues=issues,
                suggestions=suggestions,
                reasoning=f"Technical inspection of {len(context.frames)} frames and clip file.",
                metadata={"min_resolution": self.min_resolution},
            )

        except Exception as e:
            self.logger.error(f"Technical critique failed: {e}")
            return self._create_result(
                score=5.0,
                issues=[f"Technical evaluation error: {e}"],
                reasoning="Exception during technical analysis.",
            )

    async def _check_frames(
        self, context: CritiqueContext
    ) -> tuple[list[str], float]:
        """Check frame quality issues.

        Args:
            context: Critique context

        Returns:
            Tuple of (issues list, score deduction)
        """
        issues = []
        deduction = 0.0

        try:
            import cv2

            if not context.frames:
                return issues, deduction

            # Check resolution of first frame
            first_frame = cv2.imread(str(context.frames[0]))
            if first_frame is None:
                issues.append("Cannot read frame files")
                return issues, 3.0

            height, width = first_frame.shape[:2]

            if width < self.min_resolution[0] or height < self.min_resolution[1]:
                issues.append(
                    f"Low resolution: {width}x{height} (minimum {self.min_resolution[0]}x{self.min_resolution[1]})"
                )
                deduction += 2.0

            # Check for obvious artifacts in first few frames
            if len(context.frames) >= 2:
                artifact_issues, artifact_deduction = self._detect_artifacts(context.frames[:3])
                issues.extend(artifact_issues)
                deduction += artifact_deduction

            # Check for flicker (large differences between consecutive frames)
            if len(context.frames) >= 3:
                flicker_issues, flicker_deduction = self._detect_flicker(context.frames)
                issues.extend(flicker_issues)
                deduction += flicker_deduction

        except ImportError:
            logger.debug("OpenCV not available for frame analysis")
        except Exception as e:
            logger.debug(f"Frame analysis error: {e}")

        return issues, deduction

    async def _check_clip(self, context: CritiqueContext) -> tuple[list[str], float]:
        """Check clip file quality.

        Args:
            context: Critique context

        Returns:
            Tuple of (issues list, score deduction)
        """
        issues = []
        deduction = 0.0

        try:
            clip_path = context.clip_path
            if not clip_path or not clip_path.exists():
                issues.append("Clip file not found")
                return issues, 2.0

            # Check file size (sanity check)
            file_size = clip_path.stat().st_size
            if file_size == 0:
                issues.append("Clip file is empty")
                deduction += 3.0
            elif file_size > 1024 * 1024 * 1024:  # > 1GB
                issues.append(
                    f"Clip file very large ({file_size / (1024**3):.1f}GB); may indicate encoding issue"
                )
                deduction += 0.5

            # Try to analyze video properties
            try:
                import cv2

                cap = cv2.VideoCapture(str(clip_path))
                if not cap.isOpened():
                    issues.append("Cannot open clip file")
                    deduction += 2.0
                else:
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                    if fps == 0 or fps < 20:
                        issues.append(f"Low frame rate: {fps:.1f}fps")
                        deduction += 1.0

                    if width < self.min_resolution[0] or height < self.min_resolution[1]:
                        issues.append(
                            f"Low clip resolution: {width}x{height}"
                        )
                        deduction += 1.5

                    cap.release()

            except ImportError:
                logger.debug("OpenCV not available for clip analysis")

        except Exception as e:
            logger.debug(f"Clip analysis error: {e}")

        return issues, deduction

    async def _check_audio(self, context: CritiqueContext) -> tuple[list[str], float]:
        """Check audio quality if present.

        Args:
            context: Critique context

        Returns:
            Tuple of (issues list, score deduction)
        """
        issues = []
        deduction = 0.0

        try:
            import cv2

            clip_path = context.clip_path
            if not clip_path or not clip_path.exists():
                return issues, 0.0

            cap = cv2.VideoCapture(str(clip_path))
            if not cap.isOpened():
                return issues, 0.0

            # Check for audio stream
            audio_codec = cap.get(cv2.CAP_PROP_AUDIO_CODEC)
            if audio_codec == 0:
                # No audio detected; this may be expected
                pass

            cap.release()

        except ImportError:
            logger.debug("OpenCV not available for audio check")
        except Exception as e:
            logger.debug(f"Audio check error: {e}")

        # Note: Detailed audio analysis would require librosa or similar
        return issues, deduction

    def _detect_artifacts(
        self, frames: list[Path]
    ) -> tuple[list[str], float]:
        """Detect compression or encoding artifacts.

        Args:
            frames: List of frame paths

        Returns:
            Tuple of (issues list, score deduction)
        """
        issues = []
        deduction = 0.0

        try:
            import cv2
            import numpy as np

            # Check for blocking artifacts (common with lossy compression)
            frame = cv2.imread(str(frames[0]))
            if frame is None:
                return issues, 0.0

            # Analyze block structure (DCT-like artifacts)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)

            # Count strong horizontal/vertical lines (block boundaries)
            h_lines = np.sum(edges[:, :], axis=0)
            v_lines = np.sum(edges[:, :], axis=1)

            h_strong = np.sum(h_lines > 50)
            v_strong = np.sum(v_lines > 50)

            if h_strong > frame.shape[1] * 0.1 or v_strong > frame.shape[0] * 0.1:
                issues.append("Possible compression artifacts detected")
                deduction += 0.5

        except Exception as e:
            logger.debug(f"Artifact detection error: {e}")

        return issues, deduction

    def _detect_flicker(self, frames: list[Path]) -> tuple[list[str], float]:
        """Detect flicker between frames.

        Args:
            frames: List of frame paths

        Returns:
            Tuple of (issues list, score deduction)
        """
        issues = []
        deduction = 0.0

        try:
            import cv2
            import numpy as np

            # Compare brightness across frames
            brightnesses = []
            for frame_path in frames[:min(10, len(frames))]:
                frame = cv2.imread(str(frame_path))
                if frame is None:
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                brightness = np.mean(gray)
                brightnesses.append(brightness)

            if len(brightnesses) >= 3:
                # Check for large changes between consecutive frames
                changes = [
                    abs(brightnesses[i + 1] - brightnesses[i])
                    for i in range(len(brightnesses) - 1)
                ]
                max_change = max(changes)

                if max_change > 100:
                    issues.append(f"Possible flicker detected (brightness change: {max_change:.0f})")
                    deduction += 1.0

        except Exception as e:
            logger.debug(f"Flicker detection error: {e}")

        return issues, deduction
