# Story Generation Engine - Usage Guide

The Story Generation Engine transforms text and image prompts into complete, Hollywood-quality screenplays with detailed character bibles, scene planning, dialog, and storyboards optimized for video generation.

## Quick Start

```python
from src.studio.story import ScreenplayWriter

# Generate a complete screenplay
writer = ScreenplayWriter()
screenplay = writer.generate(
    text_prompt="A rogue AI must save humanity from corporate greed",
    image_references=["path/to/reference1.jpg", "path/to/reference2.jpg"],
    output_path="screenplay.yaml"
)

print(f"Generated: {screenplay.title}")
print(f"Logline: {screenplay.logline}")
print(f"Duration: {screenplay.duration_minutes} minutes")
```

## Complete Workflow

### 1. Generate Screenplay (ScreenplayWriter)

The `ScreenplayWriter` class creates complete screenplays through a 5-step process:

1. **Concept Generation** - High-concept pitch, logline, genre, themes
2. **Three-Act Outline** - Major plot points and story structure
3. **Scene Breakdown** - Individual scenes with beats and action
4. **Dialog Generation** - Character dialog that reveals personality
5. **Polish** - Final refinement and structure

```python
from src.studio.story import ScreenplayWriter

writer = ScreenplayWriter()

screenplay = writer.generate(
    text_prompt="A detective hunts a serial killer through neon-lit streets",
    image_references=[
        "reference_cyberpunk_city.jpg",
        "reference_detective_vibe.jpg"
    ],
    output_path="projects/my_film/screenplay.yaml"
)

# Access screenplay structure
for act in screenplay.acts:
    print(f"\n{act.title}")
    for scene in act.scenes:
        print(f"  {scene.scene_number}. {scene.title}")
        for beat in scene.beats:
            print(f"    - {beat.description}")
```

**Screenplay Structure:**
- `title`: Movie title
- `logline`: One-sentence pitch
- `genre`: Primary genre
- `themes`: Story themes
- `acts`: List of three acts
  - Each act contains scenes
  - Each scene has beats (smallest story units)
  - Each beat has duration

### 2. Design Characters (CharacterDesigner)

Creates detailed character bibles with appearance, personality, wardrobe, and voice profiles optimized for image generation.

```python
from src.studio.story import CharacterDesigner

designer = CharacterDesigner()

characters = designer.generate(
    character_descriptions={
        "Morgan Stone": "Hardened female detective in her 40s, haunted by past cases",
        "The Architect": "Mysterious killer with a twisted philosophy",
        "Chief Hayes": "Burnt-out police captain under political pressure"
    },
    reference_images={
        "Morgan Stone": ["morgan_reference.jpg"],
    },
    screenplay_context="Neo-noir thriller set in future megacity",
    output_path="projects/my_film/characters.yaml"
)

# Access character data
for char_id, character in characters.items():
    print(f"\n{character.name}")
    print(f"  Image Prompt: {character.image_gen_prompt}")
    print(f"  Appearance: {character.appearance.style_essence}")
    print(f"  Voice: {character.voice_profile.tone} ({character.voice_profile.pitch})")
    print(f"  Wardrobe Options: {len(character.wardrobe)}")
```

**Character Structure:**
- `appearance`: Physical description optimized for image generation
- `personality`: Psychology, motivations, fears, strengths, flaws
- `wardrobe`: Multiple outfit variations for different scenes
- `voice_profile`: Voice characteristics for TTS
- `image_gen_prompt`: Ready-to-use prompt for image generators

### 3. Plan Scenes (ScenePlanner)

Breaks screenplay scenes into detailed shots with camera directions, lighting, and generation parameters.

```python
from src.studio.story import ScenePlanner

planner = ScenePlanner()

# Extract all scenes from screenplay
all_scenes = [
    scene
    for act in screenplay.acts
    for scene in act.scenes
]

shots = planner.generate(
    screenplay=screenplay,
    characters_bible=characters,
    project_path="projects/my_film",
    output_dir="projects/my_film/scripts/scenes"
)

# Access shot data
for scene_id, scene_shots in shots.items():
    print(f"\n{scene_id}:")
    for shot in scene_shots:
        print(f"  {shot.shot_id}: {shot.duration}s, {shot.camera}")
        print(f"    Prompt: {shot.prompt}")
```

**Shot Structure:**
- `shot_id`: Unique identifier
- `duration`: Screen time in seconds
- `fps`: Frame rate (usually 24)
- `resolution`: Output resolution
- `camera`: Camera type and movement
- `lens`: Focal length
- `lighting`: Lighting description
- `prompt`: Positive prompt for generation
- `negative_prompt`: What to avoid
- `generation`: Generation config with method, seed, steps, guidance
- `references`: Reference images for generation
- `actors`: Characters in shot

### 4. Write Dialog (DialogWriter)

Generates natural, character-consistent dialog that reveals personality and advances plot.

```python
from src.studio.story import DialogWriter

writer = DialogWriter()

all_scenes = [scene for act in screenplay.acts for scene in act.scenes]

dialogs = writer.generate(
    scenes=all_scenes,
    characters_bible=characters,
    screenplay_context="Neo-noir thriller",
    output_dir="projects/my_film/scripts/dialogs"
)

# Access dialog
for scene_id, lines in dialogs.items():
    print(f"\n{scene_id}:")
    for line in lines:
        print(f"  {line.speaker} ({line.start_sec}s-{line.end_sec}s):")
        print(f"    \"{line.text}\"")
        if line.subtext:
            print(f"    [subtext: {line.subtext}]")
```

**Dialog Structure:**
- `line_id`: Unique line identifier
- `speaker`: Character name
- `start_sec`, `end_sec`: Timing in seconds
- `text`: The actual dialog
- `subtext`: What's really meant
- `emotion`: Emotional state during line

### 5. Create Storyboards (Storyboarder)

Translates shot descriptions into optimized prompts for video generation models with model-specific prompt engineering.

```python
from src.studio.story import Storyboarder

storyboarder = Storyboarder()

storyboards = storyboarder.generate(
    scenes_with_shots=shots,
    screenplay_title=screenplay.title,
    output_dir="projects/my_film/scripts/scenes"
)

# Access optimized prompts
for shot_id, storyboard in storyboards.items():
    print(f"\n{shot_id}: {storyboard.shot_description}")
    for opt in storyboard.optimizations:
        print(f"\n  {opt.model}:")
        print(f"    Positive: {opt.positive_prompt[:100]}...")
        print(f"    Camera: {opt.camera_movement}")
        print(f"    Frames: {opt.frame_count}")
```

**Storyboard Structure:**
- `shot_description`: Human-readable shot description
- `optimizations`: List of model-specific optimizations
  - CogVideoX: Optimized for smooth motion and cinematic shots
  - SDXL: Optimized for photorealistic detail
- `lighting_notes`: Technical lighting guidance
- `movement_notes`: Camera and actor movement guidance

## LLM Backend Configuration

The Story Generation Engine supports multiple LLM backends:

### vllm (Best Performance)
```python
from src.studio.story.writer import LLMBackend

# Auto-detects and uses vllm if available
backend = LLMBackend()
```

Model: `meta-llama/Llama-2-7b-hf`
- Requires: `pip install vllm`
- GPU with 8GB+ VRAM recommended

### Transformers (Fallback)
If vllm unavailable, uses:

Model: `distilgpt2`
- Requires: `pip install transformers torch`
- Slower but works on CPU

### Mock Backend (Testing)
For testing without a GPU:

```python
from src.studio.story import ScreenplayWriter

# Automatically falls back to mock if models unavailable
writer = ScreenplayWriter()  # Uses mock with demo responses
```

## Output Formats

All modules output YAML files compatible with the existing Movilizer project structure.

### screenplay.yaml
```yaml
title: "Neon Shadows"
logline: "A rogue AI operative must stop a corporate conspiracy..."
genre: "Sci-Fi Thriller"
themes:
  - identity
  - corporate greed
acts:
  - act_number: 1
    title: "Setup"
    scenes:
      - scene_id: "s1"
        title: "Opening"
        setting: "Neon-lit corridor"
        characters:
          - Detective Morgan
        beats:
          - beat_id: "b1"
            description: "Morgan exits the shadows"
            duration_seconds: 30
```

### characters.yaml
```yaml
detective_morgan:
  name: "Detective Morgan"
  role: "Protagonist"
  image_gen_prompt: "Detective Morgan, 40s, dark eyes..."
  appearance:
    age_range: "40s"
    height: "5'9\""
    style_essence: "Professional noir aesthetic"
  personality:
    archetype: "The Reluctant Hero"
    core_motivation: "Seek truth and justice"
    fears:
      - failure
      - becoming the monster
    strengths:
      - determination
      - detective instinct
```

### scene_001_opening.yaml
```yaml
scene_name: "scene_001_opening"
scene_title: "Opening Chase"
vibe_overrides:
  prompt: "rainy downtown night chase"
shots:
  - shot_id: "shot_001"
    duration: 4.0
    camera: "wide establishing crane"
    prompt: "Detective exits and scans the street"
    generation:
      method: "keyframes_to_video"
      seed: 4101
      num_inference_steps: 34
      guidance_scale: 6.5
    storyboard:
      optimizations:
        - model: "cogvideox"
          positive_prompt: "Cinematic video: Detective exits..."
          camera_movement: "smooth crane up"
```

### scene_001_opening_dialog.yaml
```yaml
scene: "scene_001_opening"
sample_rate: 24000
speakers:
  narrator:
    voice_profile: "projects/my_film/assets/audio/voices/narrator/profile.yaml"
lines:
  - line_id: "l1"
    speaker: "narrator"
    start_sec: 0.5
    end_sec: 2.6
    text: "In this city, everyone runs from something."
```

## Advanced Usage

### Custom LLM Backend

```python
class CustomLLM:
    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        # Your implementation
        return response

from src.studio.story import ScreenplayWriter
writer = ScreenplayWriter(llm_backend=custom_llm)
```

### Refining Generated Content

```python
# Refine dialog for better consistency
refined_dialogs = writer.refine_dialog(
    dialog_lines=initial_dialog,
    scene=scene,
    characters_bible=characters,
    screenplay_context="Neo-noir thriller"
)
```

### Batch Processing

```python
from pathlib import Path

# Generate multiple screenplays
prompts = [
    "A detective hunts a killer",
    "A heist in a future city",
    "A romance against all odds"
]

for i, prompt in enumerate(prompts):
    writer = ScreenplayWriter()
    screenplay = writer.generate(
        text_prompt=prompt,
        output_path=f"screenplay_{i+1}.yaml"
    )
```

## Performance Tips

1. **GPU Acceleration**: Use vllm with a CUDA-capable GPU for 3-5x faster generation
2. **Batch Processing**: Generate multiple screenplays in parallel using multiprocessing
3. **Caching**: Reuse character bibles and outlines across projects
4. **Model Size**: Use smaller models (distilgpt2) for rapid iteration, larger models (Llama-2-7b) for quality

## Troubleshooting

**Issue: "vllm not available"**
- Solution: `pip install vllm` or use transformers fallback

**Issue: "out of memory"**
- Solution: Use smaller model or GPU with more VRAM

**Issue: JSON parsing errors**
- Solution: These are logged as warnings; fallback defaults are used

**Issue: Slow generation**
- Solution: Use mock backend for rapid testing

## API Reference

### ScreenplayWriter
- `generate()` - Create complete screenplay
- `_generate_concept()` - Generate high-concept pitch
- `_generate_outline()` - Create three-act structure
- `_generate_scenes()` - Break into scenes with beats
- `_generate_dialog()` - Add character dialog
- `_polish_screenplay()` - Final structure and output

### CharacterDesigner
- `generate()` - Create character bibles
- `_design_character()` - Design single character
- `_generate_appearance()` - Physical appearance
- `_generate_personality()` - Psychology and personality
- `_generate_wardrobe()` - Outfit variations
- `_generate_voice()` - Voice characteristics

### ScenePlanner
- `generate()` - Plan all scenes
- `_plan_scene()` - Detailed shot planning
- `_structure_shot()` - Format shot data

### DialogWriter
- `generate()` - Generate dialog for scenes
- `refine_dialog()` - Improve dialog consistency
- `_write_dialog_for_scene()` - Write single scene dialog

### Storyboarder
- `generate()` - Create storyboards with optimizations
- `_optimize_for_cogvideox()` - CogVideoX-specific prompts
- `_optimize_for_sdxl()` - SDXL-specific prompts
- `_analyze_lighting()` - Lighting analysis
- `_analyze_movement()` - Movement analysis

## Examples

See the integration test in this module for complete working examples of all classes.

