"""
ScenePlanner: Breaks screenplay scenes into detailed shots with technical
specifications, matching the existing project YAML format.
"""

import logging
import json
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path

import yaml

from .writer import LLMBackend, Screenplay

logger = logging.getLogger(__name__)


@dataclass
class GenerationConfig:
    """Video generation configuration for a shot."""
    method: str  # keyframes_to_video, video_plugin, image_only
    plugin: Optional[str]
    seed: int
    num_inference_steps: int
    guidance_scale: float
    anchor_frames: Optional[List[int]] = None
    prompt_schedule: Optional[List[Dict[str, Any]]] = None


@dataclass
class ShotReferences:
    """Reference materials for generation."""
    pose: Optional[str] = None
    background: Optional[str] = None
    wardrobe: Optional[str] = None
    prompt_images: List[str] = None
    prompt_videos: List[str] = None

    def __post_init__(self):
        if self.prompt_images is None:
            self.prompt_images = []
        if self.prompt_videos is None:
            self.prompt_videos = []


@dataclass
class Shot:
    """Single shot with all technical details."""
    shot_id: str
    duration: float
    fps: int
    resolution: List[int]
    camera: str
    lens: str
    lighting: str
    prompt: str
    negative_prompt: str
    generation: GenerationConfig
    references: ShotReferences
    actors: List[str]
    prompt_media: Optional[Dict[str, List[str]]] = None


class ScenePlanner:
    """
    Plans screenplay scenes into detailed shots with camera directions,
    lighting specs, and generation parameters matching the project format.
    """

    def __init__(self, llm_backend: Optional[LLMBackend] = None):
        """Initialize scene planner."""
        self.llm = llm_backend or LLMBackend()
        logger.info(f"ScenePlanner initialized with {self.llm.backend_name} backend")

    def generate(
        self,
        screenplay: Screenplay,
        characters_bible: Optional[Dict[str, Any]] = None,
        project_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, List[Shot]]:
        """
        Generate detailed shot plans for all scenes in a screenplay.

        Args:
            screenplay: Completed Screenplay object
            characters_bible: Character information for reference
            project_path: Path to the project (for asset references)
            output_dir: Optional directory to save scene YAMLs

        Returns:
            Dict mapping scene_ids to lists of Shot objects
        """
        logger.info(f"Planning {len([s for a in screenplay.acts for s in a.scenes])} scenes")

        all_shots = {}
        for act in screenplay.acts:
            for scene in act.scenes:
                shots = self._plan_scene(
                    scene, screenplay, characters_bible, project_path
                )
                all_shots[scene.scene_id] = shots
                logger.info(f"Planned {len(shots)} shots for {scene.title}")

        # Save if path provided
        if output_dir:
            self._save_scene_files(all_shots, screenplay, output_dir)
            logger.info(f"Saved scene files to {output_dir}")

        return all_shots

    def _plan_scene(
        self,
        scene: Any,
        screenplay: Screenplay,
        characters_bible: Optional[Dict[str, Any]] = None,
        project_path: Optional[Path] = None,
    ) -> List[Shot]:
        """Plan a single scene into shots."""
        characters_context = ""
        if characters_bible:
            characters_context = f"\nCharacters: {', '.join(scene.characters)}"

        scene_prompt = f"""You are a cinematographer planning shots for a scene.

Film: {screenplay.title}
Scene: {scene.title}
Setting: {scene.setting}
Time: {scene.time_of_day}
Characters: {', '.join(scene.characters)}{characters_context}

Generate a JSON response with EXACTLY this structure (no markdown, just raw JSON):
{{
  "shots": [
    {{
      "shot_id": "shot_001",
      "description": "What happens in this shot",
      "camera_movement": "static / pan / tracking / crane / etc",
      "lens": "focal length like 28mm or 50mm",
      "lighting_key": "Key light direction and quality",
      "lighting_description": "Full lighting setup description",
      "duration_seconds": 4.0,
      "generation_method": "keyframes_to_video / video_plugin / image_only",
      "shot_prompt": "Detailed positive prompt for image/video generation",
      "negative_prompt": "What to avoid in generation",
      "anchor_frames": [0, 96],
      "inference_steps": 34,
      "guidance_scale": 6.5,
      "seed": 4101
    }}
  ]
}}

Create 2-4 shots per scene. Each shot should have distinct camera work and lighting.
Make prompts cinematic and specific to the scene's mood and story beat."""

        response = self.llm.generate(scene_prompt, max_tokens=1500)

        shots = []
        try:
            data = json.loads(response)
            for shot_data in data.get("shots", []):
                shot = self._structure_shot(
                    shot_data, scene, screenplay, project_path
                )
                shots.append(shot)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse shots for {scene.title}")
            shots.append(self._create_default_shot(scene))

        return shots

    def _structure_shot(
        self,
        shot_data: Dict[str, Any],
        scene: Any,
        screenplay: Screenplay,
        project_path: Optional[Path] = None,
    ) -> Shot:
        """Structure raw shot data into Shot object."""
        project_str = str(project_path) if project_path else "projects/feature_film_demo"

        generation = GenerationConfig(
            method=shot_data.get("generation_method", "video_plugin"),
            plugin="native_video_stub" if shot_data.get("generation_method") == "video_plugin" else None,
            seed=shot_data.get("seed", 4100),
            num_inference_steps=shot_data.get("inference_steps", 32),
            guidance_scale=shot_data.get("guidance_scale", 6.5),
            anchor_frames=shot_data.get("anchor_frames"),
        )

        references = ShotReferences(
            background=f"{project_str}/assets/refs/{scene.scene_id}_bg.txt",
            wardrobe=f"{project_str}/assets/refs/wardrobe_main.txt",
            pose=f"{project_str}/assets/refs/pose_{shot_data.get('shot_id', 'default')}.txt",
            prompt_images=[
                f"{project_str}/assets/refs/{scene.scene_id}_{shot_data.get('shot_id', 's1')}_refA.txt",
            ],
        )

        shot = Shot(
            shot_id=shot_data.get("shot_id", "shot_001"),
            duration=float(shot_data.get("duration_seconds", 4.0)),
            fps=24,
            resolution=[1280, 720],
            camera=shot_data.get("camera_movement", "static").lower(),
            lens=shot_data.get("lens", "35mm"),
            lighting=shot_data.get("lighting_description", "practical lighting"),
            prompt=shot_data.get("shot_prompt", "Scene action"),
            negative_prompt=shot_data.get("negative_prompt", ""),
            generation=generation,
            references=references,
            actors=scene.characters,
            prompt_media={
                "images": [],
                "videos": [],
            },
        )

        return shot

    def _create_default_shot(self, scene: Any) -> Shot:
        """Create a minimal default shot for error handling."""
        generation = GenerationConfig(
            method="image_only",
            plugin=None,
            seed=4100,
            num_inference_steps=32,
            guidance_scale=6.5,
        )

        references = ShotReferences()

        shot = Shot(
            shot_id="shot_001",
            duration=5.0,
            fps=24,
            resolution=[1280, 720],
            camera="medium shot",
            lens="50mm",
            lighting="natural practical lighting",
            prompt=f"{scene.title} scene with {', '.join(scene.characters)}",
            negative_prompt="",
            generation=generation,
            references=references,
            actors=scene.characters,
        )

        return shot

    def _save_scene_files(
        self,
        all_shots: Dict[str, List[Shot]],
        screenplay: Screenplay,
        output_dir: Path,
    ) -> None:
        """Save each scene as a YAML file matching project format."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for scene_id, shots in all_shots.items():
            scene_data = {
                "scene_name": scene_id,
                "scene_title": shots[0].prompt if shots else "Untitled",
                "vibe_overrides": {
                    "prompt": f"{screenplay.title} - cinematic and immersive",
                    "negative_prompt": "low quality, artifacts",
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

                # Add optional generation parameters
                if shot.generation.method == "keyframes_to_video":
                    shot_data["generation"].update({
                        "seed": shot.generation.seed,
                        "num_inference_steps": shot.generation.num_inference_steps,
                        "guidance_scale": shot.generation.guidance_scale,
                        "anchor_frames": shot.generation.anchor_frames or [0, int(shot.duration * shot.fps)],
                        "prompt_schedule": shot.generation.prompt_schedule or [],
                    })
                else:
                    shot_data["generation"].update({
                        "seed": shot.generation.seed,
                        "num_inference_steps": shot.generation.num_inference_steps,
                        "guidance_scale": shot.generation.guidance_scale,
                    })

                if shot.generation.plugin:
                    shot_data["generation"]["plugin"] = shot.generation.plugin

                if shot.prompt_media:
                    shot_data["prompt_media"] = shot.prompt_media

                scene_data["shots"].append(shot_data)

            # Save scene YAML
            scene_filename = f"{scene_id}.yaml"
            scene_path = output_dir / scene_filename
            with open(scene_path, "w") as f:
                yaml.dump(scene_data, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Saved scene to {scene_path}")
