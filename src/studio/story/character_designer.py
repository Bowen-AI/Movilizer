"""
CharacterDesigner: Generates detailed character bibles from descriptions
or reference images, optimized for image generation models.
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
class CharacterAppearance:
    """Physical description optimized for image generation prompts."""
    age_range: str
    height: str
    build: str
    skin_tone: str
    hair_description: str
    distinctive_features: List[str]
    style_essence: str


@dataclass
class CharacterPersonality:
    """Personality and psychology."""
    archetype: str
    core_motivation: str
    fears: List[str]
    strengths: List[str]
    flaws: List[str]
    background_snippet: str


@dataclass
class WardrobeItem:
    """Single wardrobe piece optimized for generation."""
    scene_ids: List[str]
    description: str
    color: str
    style: str
    mood: str


@dataclass
class VoiceProfile:
    """Voice characteristics for TTS."""
    pitch: str  # high, medium, low
    pace: str  # slow, moderate, fast
    accent: str
    tone: str  # warm, crisp, gravelly, etc


@dataclass
class Character:
    """Complete character definition."""
    character_id: str
    name: str
    role: str
    appearance: CharacterAppearance
    personality: CharacterPersonality
    wardrobe: List[WardrobeItem]
    voice_profile: VoiceProfile
    image_gen_prompt: str


class CharacterDesigner:
    """
    Generates detailed character bibles from text descriptions or reference images.

    Each character includes physical descriptions optimized for image generation,
    personality profiles, wardrobe specifications per scene, and voice profiles.
    """

    def __init__(self, llm_backend: Optional[LLMBackend] = None):
        """
        Initialize character designer.

        Args:
            llm_backend: Optional custom LLM backend.
        """
        self.llm = llm_backend or LLMBackend()
        logger.info(f"CharacterDesigner initialized with {self.llm.backend_name} backend")

    def generate(
        self,
        character_descriptions: Dict[str, str],
        reference_images: Optional[Dict[str, List[str]]] = None,
        screenplay_context: Optional[str] = None,
        output_path: Optional[Path] = None,
    ) -> Dict[str, Character]:
        """
        Generate character bibles from descriptions and reference images.

        Args:
            character_descriptions: Dict mapping character names to descriptions
            reference_images: Dict mapping character names to image paths
            screenplay_context: Optional screenplay context for consistency
            output_path: Optional path to save characters.yaml

        Returns:
            Dict mapping character IDs to Character objects
        """
        logger.info(f"Generating character bibles for {len(character_descriptions)} characters")

        characters = {}
        for char_name, description in character_descriptions.items():
            images = reference_images.get(char_name, []) if reference_images else []
            character = self._design_character(
                char_name, description, images, screenplay_context
            )
            characters[character.character_id] = character
            logger.info(f"Generated character: {character.name}")

        if output_path:
            self._save_characters(characters, output_path)
            logger.info(f"Saved character bibles to {output_path}")

        return characters

    def _design_character(
        self,
        name: str,
        description: str,
        reference_images: List[str],
        context: Optional[str] = None,
    ) -> Character:
        """Design a single character with all details."""
        # Step 1: Generate appearance
        appearance = self._generate_appearance(name, description, reference_images, context)

        # Step 2: Generate personality
        personality = self._generate_personality(name, description, context)

        # Step 3: Generate wardrobe variations
        wardrobe = self._generate_wardrobe(name, appearance, description, context)

        # Step 4: Generate voice profile
        voice = self._generate_voice(name, personality, context)

        # Step 5: Create image generation prompt
        prompt = self._create_image_prompt(appearance, personality, name)

        character_id = name.lower().replace(" ", "_")
        character = Character(
            character_id=character_id,
            name=name,
            role="Supporting",  # Simplified, could be enhanced
            appearance=appearance,
            personality=personality,
            wardrobe=wardrobe,
            voice_profile=voice,
            image_gen_prompt=prompt,
        )

        return character

    def _generate_appearance(
        self,
        name: str,
        description: str,
        reference_images: List[str],
        context: Optional[str] = None,
    ) -> CharacterAppearance:
        """Generate physical appearance from description and images."""
        image_context = ""
        if reference_images:
            image_context = (
                f"\n\nReference images: {len(reference_images)} images showing "
                "the character's appearance, style, and essence."
            )

        appearance_prompt = f"""You are designing a character's physical appearance for a film.

Character: {name}
Description: {description}{image_context}
{f'Story Context: {context}' if context else ''}

Generate a JSON response with EXACTLY this structure (no markdown, just raw JSON):
{{
  "age_range": "20s-30s",
  "height": "5'10\" (athletic build)",
  "build": "lean and muscular",
  "skin_tone": "warm medium",
  "hair_description": "Dark brown shoulder-length, slightly wavy",
  "distinctive_features": ["scar on left cheekbone", "intense dark eyes"],
  "style_essence": "Practical streetwear mixed with corporate pieces; minimalist aesthetic"
}}

Make the appearance visually distinctive and suitable for image generation models.
Include specific details that will help generate consistent character images."""

        response = self.llm.generate(appearance_prompt, max_tokens=400)

        try:
            data = json.loads(response)
            return CharacterAppearance(
                age_range=data.get("age_range", "30s"),
                height=data.get("height", "Average height"),
                build=data.get("build", "Medium build"),
                skin_tone=data.get("skin_tone", "Medium"),
                hair_description=data.get("hair_description", "Brown hair"),
                distinctive_features=data.get("distinctive_features", []),
                style_essence=data.get("style_essence", "Casual"),
            )
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse appearance for {name}")
            return CharacterAppearance(
                age_range="30s",
                height="Average",
                build="Medium",
                skin_tone="Medium",
                hair_description="Brown hair",
                distinctive_features=[],
                style_essence="Casual contemporary",
            )

    def _generate_personality(
        self, name: str, description: str, context: Optional[str] = None
    ) -> CharacterPersonality:
        """Generate personality profile."""
        personality_prompt = f"""You are developing a character's psychology and personality.

Character: {name}
Description: {description}
{f'Story Context: {context}' if context else ''}

Generate a JSON response with EXACTLY this structure (no markdown, just raw JSON):
{{
  "archetype": "The Reluctant Hero / The Mentor / etc",
  "core_motivation": "What drives this character at their core?",
  "fears": ["fear1", "fear2", "fear3"],
  "strengths": ["strength1", "strength2"],
  "flaws": ["flaw1", "flaw2"],
  "background_snippet": "Two sentences about their past that shaped them"
}}

Make the character complex and believable with contradictions and depth."""

        response = self.llm.generate(personality_prompt, max_tokens=400)

        try:
            data = json.loads(response)
            return CharacterPersonality(
                archetype=data.get("archetype", "Everyman"),
                core_motivation=data.get("core_motivation", "Survival"),
                fears=data.get("fears", []),
                strengths=data.get("strengths", []),
                flaws=data.get("flaws", []),
                background_snippet=data.get("background_snippet", ""),
            )
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse personality for {name}")
            return CharacterPersonality(
                archetype="Protagonist",
                core_motivation="Seek truth",
                fears=["failure"],
                strengths=["determination"],
                flaws=["impatience"],
                background_snippet="",
            )

    def _generate_wardrobe(
        self,
        name: str,
        appearance: CharacterAppearance,
        description: str,
        context: Optional[str] = None,
    ) -> List[WardrobeItem]:
        """Generate wardrobe variations for different scenes/moods."""
        wardrobe_prompt = f"""You are designing a character's wardrobe for different scenarios.

Character: {name}
Style Essence: {appearance.style_essence}
Character Description: {description}
{f'Story Context: {context}' if context else ''}

Generate a JSON response with EXACTLY this structure (no markdown, just raw JSON):
{{
  "wardrobe": [
    {{
      "description": "Detailed outfit description with color and fabric",
      "color": "Primary color palette",
      "style": "Fashion style category",
      "mood": "The emotional/thematic mood this outfit conveys"
    }},
    {{
      "description": "Second outfit...",
      "color": "...",
      "style": "...",
      "mood": "..."
    }}
  ]
}}

Generate 4-5 outfit variations that show different facets of the character.
Make each distinct in mood and style while staying true to the character's essence."""

        response = self.llm.generate(wardrobe_prompt, max_tokens=600)

        wardrobe = []
        try:
            data = json.loads(response)
            for idx, item in enumerate(data.get("wardrobe", [])):
                wardrobe.append(
                    WardrobeItem(
                        scene_ids=[],  # To be filled by scene planner
                        description=item.get("description", ""),
                        color=item.get("color", ""),
                        style=item.get("style", ""),
                        mood=item.get("mood", ""),
                    )
                )
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse wardrobe for {name}")
            wardrobe.append(
                WardrobeItem(
                    scene_ids=[],
                    description="Practical everyday clothing",
                    color="neutral",
                    style="contemporary",
                    mood="practical",
                )
            )

        return wardrobe

    def _generate_voice(
        self, name: str, personality: CharacterPersonality, context: Optional[str] = None
    ) -> VoiceProfile:
        """Generate voice characteristics."""
        voice_prompt = f"""You are creating a voice profile for a character in a film.

Character: {name}
Archetype: {personality.archetype}
Core Motivation: {personality.core_motivation}
{f'Story Context: {context}' if context else ''}

Generate a JSON response with EXACTLY this structure (no markdown, just raw JSON):
{{
  "pitch": "high/medium/low",
  "pace": "slow/moderate/fast",
  "accent": "No accent / British / Southern US / etc",
  "tone": "warm, crisp, gravelly, authoritative, vulnerable, etc"
}}

The voice should reflect the character's personality and background."""

        response = self.llm.generate(voice_prompt, max_tokens=300)

        try:
            data = json.loads(response)
            return VoiceProfile(
                pitch=data.get("pitch", "medium"),
                pace=data.get("pace", "moderate"),
                accent=data.get("accent", "No accent"),
                tone=data.get("tone", "neutral"),
            )
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse voice for {name}")
            return VoiceProfile(
                pitch="medium",
                pace="moderate",
                accent="No accent",
                tone="neutral",
            )

    def _create_image_prompt(self, appearance: CharacterAppearance, personality: CharacterPersonality, name: str) -> str:
        """Create an optimized prompt for image generation models."""
        prompt = (
            f"{name}, {appearance.age_range}, {appearance.build}. "
            f"{appearance.hair_description}. {appearance.skin_tone} skin. "
            f"Distinctive features: {', '.join(appearance.distinctive_features) or 'subtle'}. "
            f"Style: {appearance.style_essence}. "
            f"Expression and body language convey: {personality.archetype}. "
            f"Professional cinematic photograph, film still, high quality."
        )
        return prompt

    def _save_characters(self, characters: Dict[str, Character], output_path: Path) -> None:
        """Save character bibles to YAML."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        characters_dict = {}
        for char_id, character in characters.items():
            characters_dict[char_id] = {
                "name": character.name,
                "role": character.role,
                "image_gen_prompt": character.image_gen_prompt,
                "appearance": {
                    "age_range": character.appearance.age_range,
                    "height": character.appearance.height,
                    "build": character.appearance.build,
                    "skin_tone": character.appearance.skin_tone,
                    "hair_description": character.appearance.hair_description,
                    "distinctive_features": character.appearance.distinctive_features,
                    "style_essence": character.appearance.style_essence,
                },
                "personality": {
                    "archetype": character.personality.archetype,
                    "core_motivation": character.personality.core_motivation,
                    "fears": character.personality.fears,
                    "strengths": character.personality.strengths,
                    "flaws": character.personality.flaws,
                    "background_snippet": character.personality.background_snippet,
                },
                "voice_profile": {
                    "pitch": character.voice_profile.pitch,
                    "pace": character.voice_profile.pace,
                    "accent": character.voice_profile.accent,
                    "tone": character.voice_profile.tone,
                },
                "wardrobe": [
                    {
                        "description": item.description,
                        "color": item.color,
                        "style": item.style,
                        "mood": item.mood,
                    }
                    for item in character.wardrobe
                ],
            }

        with open(output_path, "w") as f:
            yaml.dump(characters_dict, f, default_flow_style=False, sort_keys=False)
