"""
DialogWriter: Generates and refines natural dialog with character voice
consistency, matching the existing project YAML format.
"""

import logging
import json
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path

import yaml

from .writer import LLMBackend

logger = logging.getLogger(__name__)


@dataclass
class DialogLine:
    """Single line of dialog with metadata."""
    line_id: str
    speaker: str
    start_sec: float
    end_sec: float
    text: str
    subtext: Optional[str] = None
    emotion: Optional[str] = None


class DialogWriter:
    """
    Generates and refines natural dialog with character voice consistency.

    Ensures dialog reveals character, advances plot, and maintains
    voice consistency across scenes.
    """

    def __init__(self, llm_backend: Optional[LLMBackend] = None):
        """Initialize dialog writer."""
        self.llm = llm_backend or LLMBackend()
        logger.info(f"DialogWriter initialized with {self.llm.backend_name} backend")

    def generate(
        self,
        scenes: List[Any],
        characters_bible: Optional[Dict[str, Any]] = None,
        screenplay_context: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, List[DialogLine]]:
        """
        Generate dialog for all scenes with character interactions.

        Args:
            scenes: List of scene objects from Screenplay
            characters_bible: Character voice profiles for consistency
            screenplay_context: Story context for dialog authenticity
            output_dir: Optional directory to save dialog YAMLs

        Returns:
            Dict mapping scene_ids to lists of DialogLine objects
        """
        logger.info(f"Generating dialog for {len(scenes)} scenes")

        all_dialogs = {}
        for scene in scenes:
            if len(scene.characters) >= 1:
                dialog_lines = self._write_dialog_for_scene(
                    scene, characters_bible, screenplay_context
                )
                all_dialogs[scene.scene_id] = dialog_lines
                logger.info(f"Generated {len(dialog_lines)} dialog lines for {scene.title}")

        if output_dir:
            self._save_dialog_files(all_dialogs, output_dir)
            logger.info(f"Saved dialog files to {output_dir}")

        return all_dialogs

    def _write_dialog_for_scene(
        self,
        scene: Any,
        characters_bible: Optional[Dict[str, Any]] = None,
        screenplay_context: Optional[str] = None,
    ) -> List[DialogLine]:
        """Write dialog for a single scene."""
        character_voices = self._extract_character_voices(scene.characters, characters_bible)

        dialog_prompt = f"""You are writing natural, character-driven dialog for a film scene.

Scene: {scene.title}
Setting: {scene.setting}
Time: {scene.time_of_day}
Characters: {', '.join(scene.characters)}
{character_voices}

Story Context: {screenplay_context or 'A compelling drama with high stakes.'}

Generate a JSON response with EXACTLY this structure (no markdown, just raw JSON):
{{
  "dialog_lines": [
    {{
      "speaker": "character_name",
      "text": "Natural dialog that reveals character and advances plot",
      "subtext": "What the character really means beneath the words",
      "emotion": "the emotional state - angry, vulnerable, determined, etc"
    }},
    {{
      "speaker": "character_name2",
      "text": "Response or reaction",
      "subtext": "Hidden meaning or motivation",
      "emotion": "emotional quality"
    }}
  ]
}}

Write 4-8 lines of crisp, naturalistic dialog. Each line should:
1. Sound like how the character actually speaks
2. Reveal something about personality, motivation, or relationships
3. Move the plot forward or deepen conflict
4. Avoid exposition - show don't tell
5. Have subtext - what's really being said under the surface

Make it sound like real people having a real conversation with stakes."""

        response = self.llm.generate(dialog_prompt, max_tokens=600)

        dialog_lines = []
        try:
            data = json.loads(response)
            current_time = 0.2
            for line_data in data.get("dialog_lines", []):
                # Estimate duration based on text length (rough: ~3 chars per 100ms)
                text_len = len(line_data.get("text", ""))
                duration = max(1.0, text_len / 30)

                dialog_line = DialogLine(
                    line_id=f"l{len(dialog_lines) + 1}",
                    speaker=line_data.get("speaker", "Unknown"),
                    start_sec=current_time,
                    end_sec=current_time + duration,
                    text=line_data.get("text", ""),
                    subtext=line_data.get("subtext"),
                    emotion=line_data.get("emotion"),
                )
                dialog_lines.append(dialog_line)
                current_time += duration + 0.3  # Add gap between lines

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse dialog for {scene.title}")
            # Provide default dialog
            dialog_lines.append(
                DialogLine(
                    line_id="l1",
                    speaker=scene.characters[0] if scene.characters else "Narrator",
                    start_sec=0.5,
                    end_sec=2.5,
                    text=f"Action in {scene.title}.",
                )
            )

        return dialog_lines

    def refine_dialog(
        self,
        dialog_lines: List[DialogLine],
        scene: Any,
        characters_bible: Optional[Dict[str, Any]] = None,
        screenplay_context: Optional[str] = None,
    ) -> List[DialogLine]:
        """Refine existing dialog for better voice consistency and naturalness."""
        character_voices = self._extract_character_voices(scene.characters, characters_bible)

        refine_prompt = f"""You are refining dialog for voice consistency and naturalness.

Scene: {scene.title}
{character_voices}

Current Dialog:
{self._format_dialog_for_prompt(dialog_lines)}

Generate a JSON response with EXACTLY this structure (no markdown, just raw JSON):
{{
  "refined_dialog": [
    {{
      "speaker": "character_name",
      "text": "Improved version maintaining character voice",
      "emotion": "emotional quality"
    }}
  ]
}}

Improve each line while keeping character voice consistent. Make it more natural,
punchy, and true to each character. Remove any exposition. Add more subtext."""

        response = self.llm.generate(refine_prompt, max_tokens=600)

        try:
            data = json.loads(response)
            refined_lines = []
            current_time = 0.2
            for line_data in data.get("refined_dialog", []):
                text_len = len(line_data.get("text", ""))
                duration = max(1.0, text_len / 30)

                dialog_line = DialogLine(
                    line_id=f"l{len(refined_lines) + 1}",
                    speaker=line_data.get("speaker", "Unknown"),
                    start_sec=current_time,
                    end_sec=current_time + duration,
                    text=line_data.get("text", ""),
                    emotion=line_data.get("emotion"),
                )
                refined_lines.append(dialog_line)
                current_time += duration + 0.3

            return refined_lines if refined_lines else dialog_lines

        except json.JSONDecodeError:
            logger.warning("Failed to parse refined dialog")
            return dialog_lines

    def _extract_character_voices(
        self, characters: List[str], characters_bible: Optional[Dict[str, Any]] = None
    ) -> str:
        """Extract character voice profiles for consistency."""
        if not characters_bible:
            return ""

        voices = []
        for char in characters:
            char_id = char.lower().replace(" ", "_")
            if char_id in characters_bible:
                char_info = characters_bible[char_id]
                voice = char_info.get("voice_profile", {})
                personality = char_info.get("personality", {})
                voices.append(
                    f"{char}: {personality.get('archetype', 'Character')}, "
                    f"speaks {voice.get('pace', 'normally')}, "
                    f"tone is {voice.get('tone', 'neutral')}"
                )

        return "\n".join(voices) if voices else ""

    def _format_dialog_for_prompt(self, dialog_lines: List[DialogLine]) -> str:
        """Format dialog lines for inclusion in prompts."""
        lines = []
        for line in dialog_lines:
            lines.append(f"{line.speaker}: \"{line.text}\"")
        return "\n".join(lines)

    def _save_dialog_files(
        self, all_dialogs: Dict[str, List[DialogLine]], output_dir: Path
    ) -> None:
        """Save dialog files matching project format."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for scene_id, dialog_lines in all_dialogs.items():
            # Group lines by speaker to build speakers dict
            speakers = {}
            for line in dialog_lines:
                if line.speaker not in speakers:
                    speakers[line.speaker] = {
                        "voice_profile": f"projects/feature_film_demo/assets/audio/voices/{line.speaker.lower()}/profile.yaml"
                    }

            dialog_data = {
                "scene": scene_id,
                "sample_rate": 24000,
                "speakers": speakers,
                "lines": [],
            }

            for line in dialog_lines:
                line_data = {
                    "line_id": line.line_id,
                    "speaker": line.speaker,
                    "start_sec": round(line.start_sec, 1),
                    "end_sec": round(line.end_sec, 1),
                    "text": line.text,
                }

                if line.subtext:
                    line_data["subtext"] = line.subtext
                if line.emotion:
                    line_data["emotion"] = line.emotion

                dialog_data["lines"].append(line_data)

            # Save dialog YAML with proper naming
            dialog_filename = f"{scene_id}_dialog.yaml"
            dialog_path = output_dir / dialog_filename
            with open(dialog_path, "w") as f:
                yaml.dump(dialog_data, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Saved dialog to {dialog_path}")
