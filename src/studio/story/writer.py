"""
ScreenplayWriter: Main class for generating Hollywood-quality screenplays
from text and image prompts using multi-step generation process.
"""

import logging
import json
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class Beat:
    """A single beat in a scene (unit of action/emotion)."""
    beat_id: str
    description: str
    duration_seconds: float


@dataclass
class SceneBlock:
    """A scene in a screenplay act."""
    scene_id: str
    scene_number: int
    title: str
    setting: str
    time_of_day: str
    beats: List[Beat]
    characters: List[str]


@dataclass
class Act:
    """One of three acts in a three-act screenplay."""
    act_number: int
    title: str
    scenes: List[SceneBlock]


@dataclass
class Screenplay:
    """Complete screenplay with three-act structure."""
    title: str
    logline: str
    genre: str
    themes: List[str]
    acts: List[Act]
    duration_minutes: float


class LLMBackend:
    """Abstraction for different LLM backends with fallback support."""

    def __init__(self):
        self.backend_name = "mock"
        self._init_backend()

    def _init_backend(self):
        """Try to initialize vllm, then transformers, fallback to mock."""
        try:
            import vllm
            self.backend_name = "vllm"
            self.model = vllm.LLM(
                model="meta-llama/Llama-2-7b-hf",
                gpu_memory_utilization=0.7,
                dtype="float16",
            )
            logger.info("Initialized vllm backend with Llama-2-7b")
        except (ImportError, Exception) as e:
            logger.debug(f"vllm not available: {e}")
            try:
                from transformers import pipeline
                self.backend_name = "transformers"
                self.model = pipeline(
                    "text-generation",
                    model="distilgpt2",
                    device=0,
                )
                logger.info("Initialized transformers backend with distilgpt2")
            except (ImportError, Exception) as e:
                logger.debug(f"transformers not available: {e}")
                logger.warning("Using mock LLM backend for testing")
                self.backend_name = "mock"
                self.model = None

    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        """Generate text from a prompt."""
        if self.backend_name == "vllm":
            outputs = self.model.generate([prompt], max_tokens=max_tokens)
            return outputs[0].outputs[0].text
        elif self.backend_name == "transformers":
            outputs = self.model(prompt, max_length=max_tokens, do_sample=True)
            return outputs[0]["generated_text"]
        else:
            # Mock response for testing
            return self._mock_generate(prompt)

    def _mock_generate(self, prompt: str) -> str:
        """Generate mock response for testing."""
        if "concept" in prompt.lower() or "high-concept" in prompt.lower():
            return json.dumps({
                "title": "Neon Shadows",
                "logline": "A rogue AI operative must stop a corporate conspiracy before a citywide blackout exposes the truth.",
                "genre": "Sci-Fi Thriller",
                "themes": ["identity", "corporate greed", "redemption"],
            })
        elif "outline" in prompt.lower():
            return json.dumps({
                "acts": [
                    {"act": 1, "description": "Introduction of protagonist and inciting incident"},
                    {"act": 2, "description": "Rising action and complications"},
                    {"act": 3, "description": "Climax and resolution"},
                ]
            })
        elif "scene" in prompt.lower() and "breakdown" in prompt.lower():
            return json.dumps({
                "scenes": [
                    {"id": "s1", "title": "Opening", "setting": "Neon-lit corridor"},
                    {"id": "s2", "title": "Confrontation", "setting": "Server room"},
                ]
            })
        elif "dialog" in prompt.lower():
            return json.dumps({
                "dialog": "A meaningful exchange that reveals character and advances plot"
            })
        else:
            return json.dumps({"content": "Generated content"})


class ScreenplayWriter:
    """
    Main screenplay generation engine.

    Takes text prompts and optional image references, then generates
    complete Hollywood-quality screenplays with three-act structure
    through a multi-step generation process.
    """

    def __init__(self, llm_backend: Optional[LLMBackend] = None):
        """
        Initialize the screenplay writer.

        Args:
            llm_backend: Optional custom LLM backend. If None, auto-initializes.
        """
        self.llm = llm_backend or LLMBackend()
        logger.info(f"ScreenplayWriter initialized with {self.llm.backend_name} backend")

    def generate(
        self,
        text_prompt: str,
        image_references: Optional[List[str]] = None,
        output_path: Optional[Path] = None,
    ) -> Screenplay:
        """
        Generate a complete screenplay from prompts.

        Multi-step process:
        1. Concept generation (high-concept + logline)
        2. Three-act outline
        3. Scene breakdown with beats
        4. Dialog writing
        5. Polish and refinement

        Args:
            text_prompt: User's story prompt
            image_references: Optional list of image paths for reference
            output_path: Optional path to save screenplay.yaml

        Returns:
            Screenplay object with complete structure
        """
        logger.info(f"Starting screenplay generation from prompt: {text_prompt[:50]}...")

        # Step 1: Concept generation
        concept = self._generate_concept(text_prompt, image_references)
        logger.info(f"Generated concept: {concept['title']}")

        # Step 2: Three-act outline
        outline = self._generate_outline(text_prompt, concept)
        logger.info(f"Generated three-act outline")

        # Step 3: Scene breakdown
        scenes = self._generate_scenes(concept, outline)
        logger.info(f"Generated {len(scenes)} scenes with beats")

        # Step 4: Dialog refinement
        scenes = self._generate_dialog(scenes, concept)
        logger.info(f"Refined dialog for all scenes")

        # Step 5: Polish
        screenplay = self._polish_screenplay(concept, outline, scenes)
        logger.info(f"Polished screenplay: {screenplay.title}")

        # Save if path provided
        if output_path:
            self._save_screenplay(screenplay, output_path)
            logger.info(f"Saved screenplay to {output_path}")

        return screenplay

    def _generate_concept(
        self, text_prompt: str, image_references: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Step 1: Generate high-concept pitch and logline."""
        image_context = ""
        if image_references:
            image_context = (
                f"\n\nReference images provided: {len(image_references)} images\n"
                "Use these as visual inspiration for tone, setting, and style."
            )

        concept_prompt = f"""You are a legendary Hollywood screenwriter tasked with developing a high-concept pitch.

User's Story Prompt:
{text_prompt}{image_context}

Generate a JSON response with EXACTLY this structure (no markdown, just raw JSON):
{{
  "title": "Compelling single-word or two-word movie title",
  "logline": "One sentence that hooks studios (30-50 words): Who is the protagonist, what do they want, what's stopping them?",
  "genre": "Primary genre (Sci-Fi Thriller, Drama, etc.)",
  "themes": ["theme1", "theme2", "theme3"],
  "visual_style": "Detailed description of cinematography and color grading",
  "tone": "Description of how the story should feel"
}}

Ensure the concept is cinematic, high-stakes, and commercially viable."""

        response = self.llm.generate(concept_prompt, max_tokens=400)

        try:
            concept = json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse concept JSON, using defaults")
            concept = {
                "title": "Untitled",
                "logline": text_prompt[:100],
                "genre": "Drama",
                "themes": ["survival"],
                "visual_style": "cinematic",
                "tone": "dramatic",
            }

        return concept

    def _generate_outline(self, text_prompt: str, concept: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Step 2: Generate three-act structure outline."""
        outline_prompt = f"""You are structuring a screenplay with the three-act paradigm.

Story: {concept['title']}
Logline: {concept['logline']}
Genres: {concept['genre']}
Themes: {', '.join(concept['themes'])}

Generate a JSON response with EXACTLY this structure (no markdown, just raw JSON):
{{
  "acts": [
    {{
      "act": 1,
      "title": "Setup/Inciting Incident",
      "page_count": 25,
      "key_events": ["event1", "event2", "event3"],
      "description": "Opening that establishes world, protagonist, and central problem"
    }},
    {{
      "act": 2,
      "title": "Rising Action/Midpoint",
      "page_count": 50,
      "key_events": ["event1", "event2", "event3"],
      "description": "Complications, conflicts, and stakes escalate"
    }},
    {{
      "act": 3,
      "title": "Climax/Resolution",
      "page_count": 25,
      "key_events": ["event1", "event2"],
      "description": "Final confrontation and thematic resolution"
    }}
  ]
}}

Each act should feel complete but interconnected. Make key_events specific and dramatic."""

        response = self.llm.generate(outline_prompt, max_tokens=600)

        try:
            outline_data = json.loads(response)
            return outline_data.get("acts", [])
        except json.JSONDecodeError:
            logger.warning("Failed to parse outline JSON, using default structure")
            return [
                {
                    "act": 1,
                    "title": "Setup",
                    "key_events": ["Introduction"],
                    "description": "Establishing the world and problem",
                },
                {
                    "act": 2,
                    "title": "Confrontation",
                    "key_events": ["Escalation"],
                    "description": "Rising complications",
                },
                {
                    "act": 3,
                    "title": "Resolution",
                    "key_events": ["Resolution"],
                    "description": "Final confrontation and ending",
                },
            ]

    def _generate_scenes(
        self, concept: Dict[str, Any], outline: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Step 3: Break outline into scenes with beats."""
        scenes = []
        scene_number = 1

        for act_data in outline:
            act_num = act_data["act"]
            key_events = act_data.get("key_events", [])

            scene_prompt = f"""You are breaking down act {act_num} into individual scenes with beats.

Story: {concept['title']}
Act {act_num} Key Events: {', '.join(key_events)}

Generate a JSON response with EXACTLY this structure (no markdown, just raw JSON):
{{
  "scenes": [
    {{
      "scene_id": "s{scene_number}",
      "title": "Scene title describing action",
      "setting": "Location and environment",
      "time_of_day": "Morning/Afternoon/Night/etc",
      "characters": ["character1", "character2"],
      "beats": [
        {{"beat_id": "b1", "description": "What happens here", "duration_seconds": 30}},
        {{"beat_id": "b2", "description": "Next action", "duration_seconds": 45}}
      ],
      "purpose": "How this scene advances plot/character"
    }}
  ]
}}

Create 3-4 scenes per act. Each beat should be specific and visual. Duration is the beat's screen time."""

            response = self.llm.generate(scene_prompt, max_tokens=1000)

            try:
                scenes_data = json.loads(response)
                for scene in scenes_data.get("scenes", []):
                    scene["act"] = act_num
                    scene["scene_number"] = scene_number
                    scenes.append(scene)
                    scene_number += 1
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse scenes for act {act_num}")
                # Create minimal scene
                scenes.append({
                    "act": act_num,
                    "scene_number": scene_number,
                    "scene_id": f"s{scene_number}",
                    "title": f"Act {act_num} Scene",
                    "setting": "Unknown location",
                    "time_of_day": "Day",
                    "characters": ["Protagonist"],
                    "beats": [
                        {
                            "beat_id": "b1",
                            "description": "Scene action",
                            "duration_seconds": 60,
                        }
                    ],
                })
                scene_number += 1

        return scenes

    def _generate_dialog(
        self, scenes: List[Dict[str, Any]], concept: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Step 4: Generate and refine dialog for scenes with character interactions."""
        for scene in scenes:
            characters = scene.get("characters", [])
            if len(characters) < 2:
                continue

            dialog_prompt = f"""You are writing crisp, character-driven dialog.

Story: {concept['title']}
Themes: {', '.join(concept['themes'])}
Scene: {scene['title']}
Setting: {scene['setting']}
Characters: {', '.join(characters)}

Generate a JSON response with EXACTLY this structure (no markdown, just raw JSON):
{{
  "dialog_lines": [
    {{"speaker": "character1", "text": "First line of dialog"}},
    {{"speaker": "character2", "text": "Response that reveals character"}},
    {{"speaker": "character1", "text": "Reply with subtext"}}
  ]
}}

Write 3-5 lines of snappy, natural dialog that reveals character and advances plot.
Each line should have subtext. Avoid exposition. Make it sound like real people talking."""

            response = self.llm.generate(dialog_prompt, max_tokens=400)

            try:
                dialog_data = json.loads(response)
                scene["dialog_lines"] = dialog_data.get("dialog_lines", [])
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse dialog for {scene['title']}")
                scene["dialog_lines"] = []

        return scenes

    def _polish_screenplay(
        self,
        concept: Dict[str, Any],
        outline: List[Dict[str, Any]],
        scenes: List[Dict[str, Any]],
    ) -> Screenplay:
        """Step 5: Polish and structure into final Screenplay object."""
        acts = []
        for act_data in outline:
            act_scenes = [s for s in scenes if s.get("act") == act_data["act"]]

            scene_blocks = []
            for scene_data in act_scenes:
                beats = [
                    Beat(
                        beat_id=b["beat_id"],
                        description=b["description"],
                        duration_seconds=b.get("duration_seconds", 60),
                    )
                    for b in scene_data.get("beats", [])
                ]

                scene_block = SceneBlock(
                    scene_id=scene_data["scene_id"],
                    scene_number=scene_data.get("scene_number", 1),
                    title=scene_data["title"],
                    setting=scene_data["setting"],
                    time_of_day=scene_data.get("time_of_day", "Day"),
                    beats=beats,
                    characters=scene_data.get("characters", []),
                )
                scene_blocks.append(scene_block)

            act = Act(
                act_number=act_data["act"],
                title=act_data.get("title", f"Act {act_data['act']}"),
                scenes=scene_blocks,
            )
            acts.append(act)

        # Calculate total duration
        total_duration = sum(
            sum(b.duration_seconds for b in scene.beats)
            for act in acts
            for scene in act.scenes
        ) / 60

        screenplay = Screenplay(
            title=concept["title"],
            logline=concept["logline"],
            genre=concept["genre"],
            themes=concept["themes"],
            acts=acts,
            duration_minutes=total_duration,
        )

        return screenplay

    def _save_screenplay(self, screenplay: Screenplay, output_path: Path) -> None:
        """Save screenplay to YAML file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        screenplay_dict = {
            "title": screenplay.title,
            "logline": screenplay.logline,
            "genre": screenplay.genre,
            "themes": screenplay.themes,
            "duration_minutes": screenplay.duration_minutes,
            "acts": [
                {
                    "act_number": act.act_number,
                    "title": act.title,
                    "scenes": [
                        {
                            "scene_id": scene.scene_id,
                            "scene_number": scene.scene_number,
                            "title": scene.title,
                            "setting": scene.setting,
                            "time_of_day": scene.time_of_day,
                            "characters": scene.characters,
                            "beats": [
                                {
                                    "beat_id": beat.beat_id,
                                    "description": beat.description,
                                    "duration_seconds": beat.duration_seconds,
                                }
                                for beat in scene.beats
                            ],
                        }
                        for scene in act.scenes
                    ],
                }
                for act in screenplay.acts
            ],
        }

        with open(output_path, "w") as f:
            yaml.dump(screenplay_dict, f, default_flow_style=False, sort_keys=False)
