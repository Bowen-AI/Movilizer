"""Example integration of critique system into Movilizer pipeline.

This module shows how to integrate the multi-agent critique system into
your clip generation workflow.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from . import (
    EnsembleConfig,
    EnsembleRunner,
    CritiqueContext,
    ProducerDecision,
)

logger = logging.getLogger(__name__)


async def generate_and_critique_clip(
    generator,  # Your clip generation function
    scene_script: str,
    shot_description: str,
    output_dir: Path,
    genre: str = "drama",
    tone: str = "neutral",
    max_revisions: int = 3,
    use_mock_critique: bool = False,
) -> dict:
    """Generate a clip and run critique, with revision loop.

    Args:
        generator: Async function that generates a clip
        scene_script: Script/dialogue for the scene
        shot_description: Visual description of the shot
        output_dir: Directory to save outputs
        genre: Movie genre
        tone: Emotional tone
        max_revisions: Maximum revision attempts
        use_mock_critique: Use mock LLM for testing

    Returns:
        Dict with final clip path, critique results, and decision
    """
    clip_path = None
    frames = []
    revision_count = 0
    context = None

    # Create critique ensemble
    critique_config = EnsembleConfig(
        critics=["story", "visual", "technical", "director", "audience"],
        use_mock_llm=use_mock_critique,
    )
    ensemble = EnsembleRunner(config=critique_config)

    try:
        while revision_count <= max_revisions:
            logger.info(f"Generating clip (attempt {revision_count + 1})")

            # Generate or regenerate clip
            result = await generator(
                scene_script=scene_script,
                shot_description=shot_description,
                output_dir=output_dir,
                revision_number=revision_count,
            )

            clip_path = result.get("clip_path")
            frames = result.get("frames", [])

            if not clip_path or not frames:
                logger.error("Generator failed to produce clip")
                return {
                    "success": False,
                    "error": "Generator failed",
                }

            # Create critique context
            context = CritiqueContext(
                run_id=f"gen_{output_dir.name}",
                project="movilizer",
                scene=output_dir.parent.name,
                shot=output_dir.name,
                shot_dir=output_dir,
                frames=frames,
                clip_path=clip_path,
                script=scene_script,
                shot_description=shot_description,
                genre=genre,
                tone=tone,
            )

            # Run critique
            logger.info(f"Running critique ensemble on {clip_path.name}")
            critique_result = await ensemble.run(context)

            producer_decision = critique_result["producer_decision"]
            decision = producer_decision.decision

            logger.info(
                f"Critique complete. "
                f"Score: {producer_decision.overall_score:.1f}/10, "
                f"Decision: {decision.value}"
            )

            # Log individual critic scores
            for critic_name, score in producer_decision.critic_scores.items():
                logger.info(f"  {critic_name}: {score:.1f}")

            # Handle decision
            if decision == ProducerDecision.APPROVE:
                logger.info("Clip approved! Ready for output.")
                return {
                    "success": True,
                    "clip_path": clip_path,
                    "score": producer_decision.overall_score,
                    "critique_result": critique_result,
                    "revision_count": revision_count,
                }

            elif decision == ProducerDecision.REJECT:
                logger.warning("Clip rejected. Cannot continue revisions.")
                return {
                    "success": False,
                    "clip_path": clip_path,
                    "score": producer_decision.overall_score,
                    "error": "Clip rejected after critique",
                    "critique_result": critique_result,
                    "revision_count": revision_count,
                }

            else:  # REVISE
                revision_count += 1
                if revision_count > max_revisions:
                    logger.warning("Maximum revisions reached. Accepting current clip.")
                    return {
                        "success": True,
                        "clip_path": clip_path,
                        "score": producer_decision.overall_score,
                        "critique_result": critique_result,
                        "revision_count": revision_count,
                        "forced": True,  # Approved despite revisions needed
                    }

                # Update prompt with revision instructions
                logger.info(
                    f"Revision {revision_count}/{max_revisions}: "
                    f"Applying feedback"
                )

                if producer_decision.revision_instructions:
                    logger.info("Revision instructions:")
                    for instruction in producer_decision.revision_instructions:
                        logger.info(f"  - {instruction}")

                    scene_script = _apply_revision_instructions(
                        scene_script,
                        producer_decision.revision_instructions,
                    )

    except Exception as e:
        logger.error(f"Error in generate_and_critique: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "revision_count": revision_count,
        }

    finally:
        await ensemble.shutdown()


def _apply_revision_instructions(
    original_prompt: str,
    instructions: list[str],
) -> str:
    """Apply revision instructions to the original prompt.

    Args:
        original_prompt: Original generation prompt
        instructions: List of revision instructions

    Returns:
        Updated prompt
    """
    # Simple implementation: append instructions
    # In practice, you'd want smarter prompt engineering here

    revised = original_prompt + "\n\nRevisions needed:\n"
    for instruction in instructions:
        revised += f"- {instruction}\n"

    return revised


async def batch_critique_clips(
    clip_paths: list[Path],
    scene: str = "scene_1",
    genre: str = "drama",
    use_mock: bool = False,
) -> dict:
    """Critique multiple clips in parallel.

    Args:
        clip_paths: Paths to video clips
        scene: Scene name
        genre: Movie genre
        use_mock: Use mock LLM

    Returns:
        Dict with all critique results
    """
    config = EnsembleConfig(
        critics=["technical", "visual", "director"],  # Subset for speed
        parallel=True,
        use_mock_llm=use_mock,
    )

    ensemble = EnsembleRunner(config=config)
    results = {}

    try:
        tasks = {}
        for i, clip_path in enumerate(clip_paths):
            # Extract frames (simplified)
            frames = list(clip_path.parent.glob("frame_*.png"))[:5]

            context = CritiqueContext(
                run_id="batch",
                project="movilizer",
                scene=scene,
                shot=clip_path.stem,
                shot_dir=clip_path.parent,
                frames=frames,
                clip_path=clip_path,
                genre=genre,
            )

            task = ensemble.run(context)
            tasks[clip_path.name] = task

        # Gather results
        for clip_name, task in tasks.items():
            try:
                result = await task
                results[clip_name] = result
            except Exception as e:
                logger.error(f"Failed to critique {clip_name}: {e}")
                results[clip_name] = {"error": str(e)}

    finally:
        await ensemble.shutdown()

    return results


# Example usage
async def main():
    """Example of using the integration."""

    async def mock_generator(
        scene_script,
        shot_description,
        output_dir,
        revision_number=0,
    ):
        """Mock generator that creates dummy output."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create dummy frames
        frames = []
        for i in range(5):
            frame_path = output_dir / f"frame_{i:04d}.png"
            # In real use, create actual frames
            frame_path.touch()
            frames.append(frame_path)

        clip_path = output_dir / "clip.mp4"
        clip_path.touch()

        return {
            "clip_path": clip_path,
            "frames": frames,
        }

    result = await generate_and_critique_clip(
        generator=mock_generator,
        scene_script="Actor delivers powerful monologue",
        shot_description="Close-up of actor with dramatic lighting",
        output_dir=Path("/tmp/test_clip"),
        genre="drama",
        tone="intense",
        max_revisions=2,
        use_mock_critique=True,  # Use mock for demo
    )

    print("Result:", result)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
