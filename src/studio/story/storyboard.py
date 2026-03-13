"""
Storyboarder: Translates scene and shot descriptions into optimized prompts
for video generation models (CogVideoX, SDXL), with advanced prompt engineering.
"""

import logging
import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path

import yaml

from .writer import LLMBackend

logger = logging.getLogger(__name__)


@dataclass
class PromptOptimization:
    """Prompt optimization for specific video generation models."""
    model: str  # cogvideox, sdxl, etc
    positive_prompt: str
    negative_prompt: str
    reference_images: List[str] = field(default_factory=list)
    camera_movement: str = "static"
    frame_count: int = 96
    quality_modifiers: List[str] = field(default_factory=list)


@dataclass
class Storyboard:
    """Complete storyboard entry for a shot."""
    shot_id: str
    scene_id: str
    shot_description: str
    optimizations: List[PromptOptimization]
    mood_board: Optional[List[str]] = None
    lighting_notes: Optional[str] = None
    movement_notes: Optional[str] = None


class Storyboarder:
    """
    Translates scene/shot descriptions into optimized video generation prompts.

    Uses advanced prompt engineering tuned for CogVideoX, SDXL, and other
    video/image generation models. Embeds all data into shot YAML structure.
    """

    def __init__(self, llm_backend: Optional[LLMBackend] = None):
        """Initialize storyboarder."""
        self.llm = llm_backend or LLMBackend()
        logger.info(f"Storyboarder initialized with {self.llm.backend_name} backend")

        # Model-specific prompt engineering knowledge
        self.model_templates = {
            "cogvideox": self._cogvideox_prompt_template,
            "sdxl": self._sdxl_prompt_template,
            "default": self._default_prompt_template,
        }

    def generate(
        self,
        scenes_with_shots: Dict[str, List[Any]],
        screenplay_title: str,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Storyboard]:
        """
        Generate optimized prompts for all shots.

        Args:
            scenes_with_shots: Dict mapping scene_ids to lists of Shot objects
            screenplay_title: Title of the screenplay for context
            output_dir: Optional directory to save enhanced scene YAML files

        Returns:
            Dict mapping shot_ids to Storyboard objects
        """
        logger.info(f"Generating storyboards for {len(scenes_with_shots)} scenes")

        all_storyboards = {}
        enhanced_scenes = {}

        for scene_id, shots in scenes_with_shots.items():
            for shot in shots:
                storyboard = self._create_storyboard(
                    shot, scene_id, screenplay_title
                )
                all_storyboards[shot.shot_id] = storyboard
                logger.info(f"Optimized prompts for {shot.shot_id}")

            # Store enhanced scene data
            enhanced_scenes[scene_id] = shots

        if output_dir:
            self._save_enhanced_scenes(enhanced_scenes, all_storyboards, output_dir)
            logger.info(f"Saved enhanced scene files to {output_dir}")

        return all_storyboards

    def _create_storyboard(self, shot: Any, scene_id: str, screenplay_title: str) -> Storyboard:
        """Create a storyboard entry for a single shot."""
        optimizations = [
            self._optimize_for_cogvideox(shot, screenplay_title),
            self._optimize_for_sdxl(shot, screenplay_title),
        ]

        # Analyze shot for additional notes
        lighting_notes = self._analyze_lighting(shot)
        movement_notes = self._analyze_movement(shot)

        storyboard = Storyboard(
            shot_id=shot.shot_id,
            scene_id=scene_id,
            shot_description=shot.prompt,
            optimizations=optimizations,
            lighting_notes=lighting_notes,
            movement_notes=movement_notes,
        )

        return storyboard

    def _optimize_for_cogvideox(self, shot: Any, screenplay_title: str) -> PromptOptimization:
        """Optimize prompt for CogVideoX video generation."""
        # CogVideoX excels at motion and cinematic shots
        optimization_prompt = f"""You are optimizing a shot description for CogVideoX, a video generation model.

Film: {screenplay_title}
Shot: {shot.prompt}
Camera: {shot.camera}
Lighting: {shot.lighting}
Duration: {shot.duration} seconds

CogVideoX strengths: smooth camera movement, cinematic motion, realistic lighting,
natural character movement and interactions.

Generate a JSON response with EXACTLY this structure (no markdown, just raw JSON):
{{
  "positive_prompt": "Detailed positive prompt optimized for CogVideoX (80-120 words)",
  "negative_prompt": "What to avoid for this model",
  "camera_movement": "smooth pan / tracking shot / static / crane / etc",
  "frame_count": 96,
  "quality_modifiers": ["cinema mode", "professional color grading", "shallow depth of field"]
}}

The prompt should:
1. Use active, dynamic language describing motion and action
2. Include cinematic camera language
3. Reference lighting quality and mood
4. Suggest realistic character behavior
5. Be between 80-120 words of detailed description"""

        response = self.llm.generate(optimization_prompt, max_tokens=500)

        try:
            data = json.loads(response)
            return PromptOptimization(
                model="cogvideox",
                positive_prompt=data.get("positive_prompt", shot.prompt),
                negative_prompt=data.get("negative_prompt", shot.negative_prompt),
                reference_images=shot.references.prompt_images if shot.references else [],
                camera_movement=data.get("camera_movement", shot.camera),
                frame_count=data.get("frame_count", 96),
                quality_modifiers=data.get("quality_modifiers", []),
            )
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse CogVideoX optimization for {shot.shot_id}")
            return PromptOptimization(
                model="cogvideox",
                positive_prompt=shot.prompt,
                negative_prompt=shot.negative_prompt,
                camera_movement=shot.camera,
            )

    def _optimize_for_sdxl(self, shot: Any, screenplay_title: str) -> PromptOptimization:
        """Optimize prompt for SDXL image generation (keyframes)."""
        # SDXL excels at photorealistic detail and complex compositions
        optimization_prompt = f"""You are optimizing a shot description for SDXL image generation.

Film: {screenplay_title}
Shot: {shot.prompt}
Lighting: {shot.lighting}

SDXL strengths: photorealistic details, complex scenes, intricate lighting,
high-quality textures, cinematic composition.

Generate a JSON response with EXACTLY this structure (no markdown, just raw JSON):
{{
  "positive_prompt": "Highly detailed positive prompt for SDXL (100-150 words)",
  "negative_prompt": "Specific negatives to avoid SDXL artifacts",
  "quality_modifiers": ["photorealistic", "professional photography", "cinema photography"]
}}

The prompt should:
1. Be extremely detailed and specific
2. Include photorealism language
3. Describe lighting with technical precision
4. Reference filmography and cinematography styles
5. Include texture and material descriptions
6. Be 100-150 words of rich, detailed description"""

        response = self.llm.generate(optimization_prompt, max_tokens=600)

        try:
            data = json.loads(response)
            return PromptOptimization(
                model="sdxl",
                positive_prompt=data.get("positive_prompt", shot.prompt),
                negative_prompt=data.get("negative_prompt", shot.negative_prompt),
                reference_images=shot.references.prompt_images if shot.references else [],
                frame_count=1,
                quality_modifiers=data.get("quality_modifiers", []),
            )
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse SDXL optimization for {shot.shot_id}")
            return PromptOptimization(
                model="sdxl",
                positive_prompt=shot.prompt,
                negative_prompt=shot.negative_prompt,
            )

    def _analyze_lighting(self, shot: Any) -> str:
        """Analyze and enhance lighting notes."""
        lighting_prompt = f"""Analyze the lighting setup for this shot and provide technical notes.

Lighting Description: {shot.lighting}
Camera: {shot.camera}

Provide 2-3 sentences of technical lighting guidance for cinematographers:
- Key light position and quality
- Fill and backlight suggestions
- Color temperature considerations
- Any practicals or special effects lighting"""

        response = self.llm.generate(lighting_prompt, max_tokens=200)
        return response

    def _analyze_movement(self, shot: Any) -> str:
        """Analyze and enhance movement notes."""
        movement_prompt = f"""Analyze the camera and subject movement for this shot.

Camera Type: {shot.camera}
Lens: {shot.lens}
Duration: {shot.duration} seconds
Shot Purpose: {shot.prompt[:100]}

Provide 2-3 sentences of movement guidance:
- Specific camera moves and speeds
- Actor/subject movement patterns
- How movement reveals space or emotion
- Timing and choreography notes"""

        response = self.llm.generate(movement_prompt, max_tokens=200)
        return response

    def _cogvideox_prompt_template(self, shot: Any) -> str:
        """Template for CogVideoX prompts."""
        return f"""
Cinematic video: {shot.prompt}.
Camera: {shot.camera} lens {shot.lens}.
Lighting: {shot.lighting}.
Quality: cinema mode, professional color grading, 24fps.
""".strip()

    def _sdxl_prompt_template(self, shot: Any) -> str:
        """Template for SDXL prompts."""
        return f"""
Professional cinematic photograph: {shot.prompt}.
{shot.lighting}.
Professional cinema photography, high quality, detailed.
Shot on arri alexa, anamorphic lens, color graded.
""".strip()

    def _default_prompt_template(self, shot: Any) -> str:
        """Template for unknown models."""
        return f"""
{shot.prompt}.
{shot.lighting}.
Professional quality, cinematic, detailed.
""".strip()

    def _save_enhanced_scenes(
        self,
        enhanced_scenes: Dict[str, List[Any]],
        all_storyboards: Dict[str, Any],
        output_dir: Path,
    ) -> None:
        """
        Save enhanced scene files with integrated storyboard prompts.

        Merges storyboard optimizations into the existing scene YAML structure.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for scene_id, shots in enhanced_scenes.items():
            scene_data = {
                "scene_name": scene_id,
                "scene_title": shots[0].prompt[:50] if shots else "Scene",
                "vibe_overrides": {
                    "prompt": "cinematic and immersive",
                    "negative_prompt": "low quality, artifacts, blurry",
                },
                "prompt_media": {
                    "images": [],
                    "videos": [],
                },
                "location_refs": [],
                "wardrobe_refs": [],
                "shots": [],
            }

            for shot in shots:
                storyboard = all_storyboards.get(shot.shot_id)

                shot_data = {
                    "shot_id": shot.shot_id,
                    "duration": shot.duration,
                    "fps": shot.fps,
                    "resolution": shot.resolution,
                    "camera": shot.camera,
                    "lens": shot.lens,
                    "lighting": shot.lighting,
                    "prompt": shot.prompt,
                    "negative_prompt": shot.negative_prompt,
                    "generation": {
                        "method": shot.generation.method,
                        "seed": shot.generation.seed,
                        "num_inference_steps": shot.generation.num_inference_steps,
                        "guidance_scale": shot.generation.guidance_scale,
                    },
                    "references": {
                        "pose": shot.references.pose,
                        "background": shot.references.background,
                        "wardrobe": shot.references.wardrobe,
                        "prompt_images": shot.references.prompt_images,
                        "prompt_videos": shot.references.prompt_videos,
                    },
                    "actors": shot.actors,
                }

                # Add generation method specific params
                if shot.generation.method == "keyframes_to_video":
                    shot_data["generation"].update({
                        "anchor_frames": shot.generation.anchor_frames or [0, int(shot.duration * shot.fps)],
                        "prompt_schedule": shot.generation.prompt_schedule or [],
                    })

                if shot.generation.plugin:
                    shot_data["generation"]["plugin"] = shot.generation.plugin

                # Add storyboard optimizations
                if storyboard:
                    shot_data["storyboard"] = {
                        "shot_description": storyboard.shot_description,
                        "lighting_notes": storyboard.lighting_notes,
                        "movement_notes": storyboard.movement_notes,
                        "optimizations": [],
                    }

                    for opt in storyboard.optimizations:
                        shot_data["storyboard"]["optimizations"].append({
                            "model": opt.model,
                            "positive_prompt": opt.positive_prompt,
                            "negative_prompt": opt.negative_prompt,
                            "camera_movement": opt.camera_movement,
                            "frame_count": opt.frame_count,
                            "quality_modifiers": opt.quality_modifiers,
                            "reference_images": opt.reference_images,
                        })

                if shot.prompt_media:
                    shot_data["prompt_media"] = shot.prompt_media

                scene_data["shots"].append(shot_data)

            # Save enhanced scene
            scene_filename = f"{scene_id}.yaml"
            scene_path = output_dir / scene_filename
            with open(scene_path, "w") as f:
                yaml.dump(scene_data, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Saved enhanced scene to {scene_path}")

    # Simple prompt template utilities (could be expanded)
    def create_cogvideox_negative_prompt(self) -> str:
        """Standard negative prompt for CogVideoX."""
        return (
            "low quality, blurry, distorted, jerky motion, unnatural movement, "
            "static, boring composition, amateur, watermark, text overlay"
        )

    def create_sdxl_negative_prompt(self) -> str:
        """Standard negative prompt for SDXL."""
        return (
            "low quality, blurry, distorted, artifacts, watermark, text, "
            "duplicate, username, signature, worst quality, bad anatomy"
        )
