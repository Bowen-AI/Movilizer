# Movilizer Real Models - API Reference

Complete API documentation for all real generation models.

## ImageGenerator

### Class: `ImageGenerator`
Real image generation using SDXL, Flux.1-dev, or PixArt-Sigma.

#### Configuration
```python
@dataclass
class ImageGenConfig:
    model_id: str = "stabilityai/stable-diffusion-xl-base-1.0"
    enable_lora: bool = False
    lora_ids: list[str] = field(default_factory=list)
    lora_weights: list[float] = field(default_factory=lambda: [1.0])
    enable_ip_adapter: bool = False
    ip_adapter_model_id: str = "h94/IP-Adapter"
    dtype_a100: str = "bfloat16"
    dtype_consumer: str = "float16"
    device: str = "cuda"
```

#### Methods

**`__init__(config: ImageGenConfig | None = None) -> None`**
Initialize generator with optional configuration.

**`load() -> bool`**
Load model to GPU. Returns True on success, False on failure.
- Automatically detects GPU type and sets appropriate dtype
- Enables memory optimizations (attention slicing, xformers)
- Loads LoRAs and IP-Adapter if configured
- Safe to call multiple times (idempotent)

**`unload() -> None`**
Unload model and free GPU memory.
- Clears CUDA cache
- Safe to call even if not loaded

**`generate(prompt: str, negative_prompt: str = "", width: int = 1024, height: int = 1024, num_inference_steps: int = 30, guidance_scale: float = 7.5, seed: int | None = None, ip_adapter_image: Image.Image | None = None, ip_adapter_scale: float = 0.7) -> Image.Image`**
Generate image from text prompt.

Parameters:
- `prompt` (str): Text description of desired image
- `negative_prompt` (str): Text describing what NOT to generate
- `width` (int): Output width in pixels (default 1024, must be multiple of 8)
- `height` (int): Output height in pixels (default 1024, must be multiple of 8)
- `num_inference_steps` (int): Denoising steps (more = better quality but slower, typical 20-50)
- `guidance_scale` (float): How strictly to follow prompt (7.5 typical, 0-20 range)
- `seed` (int|None): Random seed for reproducibility
- `ip_adapter_image` (Image.Image|None): Reference image for IP-Adapter conditioning
- `ip_adapter_scale` (float): Strength of IP-Adapter influence (0.0-1.0)

Returns: PIL Image (RGB)

Example:
```python
gen = ImageGenerator(ImageGenConfig(model_id="black-forest-labs/FLUX.1-dev"))
image = gen.generate(
    prompt="A majestic eagle soaring over mountains at sunset",
    negative_prompt="blurry, distorted, low quality",
    width=1024,
    height=768,
    num_inference_steps=30,
    guidance_scale=7.5,
    seed=42,
)
image.save("output.png")
gen.unload()
```

---

## VideoGenerator

### Class: `VideoGenerator`
Real video generation using CogVideoX, Wan2.1-T2V, or AnimateDiff.

#### Configuration
```python
@dataclass
class VideoGenConfig:
    model_id: str = "THUDM/CogVideoX-2B"
    num_frames: int = 49
    dtype_a100: str = "bfloat16"
    dtype_consumer: str = "float16"
    device: str = "cuda"
    max_model_size_gb: float = 8.0
```

#### Methods

**`__init__(config: VideoGenConfig | None = None) -> None`**
Initialize generator with automatic VRAM-based model selection.
- Detects available VRAM via GPUDiscovery
- Auto-selects smaller model if configured one doesn't fit
- Configurable max model size threshold

**`load() -> bool`**
Load video generation model to GPU.
- Auto-selects model based on VRAM if needed
- Enables sequential CPU offload for large models
- Safe to call multiple times

**`unload() -> None`**
Unload model and free GPU memory.

**`text_to_video(prompt: str, negative_prompt: str = "", num_frames: int | None = None, height: int = 512, width: int = 512, guidance_scale: float = 7.5, num_inference_steps: int = 50, seed: int | None = None) -> list[Image.Image]`**
Generate video frames from text prompt.

Parameters:
- `prompt` (str): Video description
- `negative_prompt` (str): What to avoid
- `num_frames` (int|None): Number of frames (default 49, typically 24-96)
- `height` (int): Frame height (default 512, must be multiple of 8)
- `width` (int): Frame width (default 512, must be multiple of 8)
- `guidance_scale` (float): Prompt adherence (typical 7.5)
- `num_inference_steps` (int): Generation steps (typical 50-100)
- `seed` (int|None): Random seed

Returns: List of PIL Images (one per frame)

Example:
```python
gen = VideoGenerator()  # Auto-selects based on VRAM
frames = gen.text_to_video(
    prompt="A cat walking gracefully across a sunny garden",
    num_frames=49,
    height=512,
    width=512,
    num_inference_steps=50,
    seed=123,
)
for i, frame in enumerate(frames):
    frame.save(f"frame_{i:03d}.png")
gen.unload()
```

**`image_to_video(image: Image.Image, prompt: str, num_frames: int | None = None, negative_prompt: str = "", guidance_scale: float = 7.5, num_inference_steps: int = 50, seed: int | None = None) -> list[Image.Image]`**
Generate video extending from an initial image.

Parameters:
- `image` (Image.Image): Starting frame
- `prompt` (str): Description of motion/evolution
- `num_frames` (int|None): Total frames to generate
- `negative_prompt` (str): What to avoid
- `guidance_scale` (float): Prompt adherence
- `num_inference_steps` (int): Generation steps
- `seed` (int|None): Random seed

Returns: List of PIL Images including the initial frame

Example:
```python
from PIL import Image
gen = VideoGenerator()
initial = Image.open("character_pose.png")
frames = gen.image_to_video(
    image=initial,
    prompt="The character waves and smiles at the camera",
    num_frames=24,
    guidance_scale=7.5,
)
gen.unload()
```

---

## TTSGenerator

### Class: `TTSGenerator`
Text-to-speech synthesis using Bark or XTTS-v2.

#### Configuration
```python
@dataclass
class TTSGenConfig:
    model_id: str = "suno/bark"
    device: str = "cuda"
    sample_rate: int = 24000
```

#### Methods

**`__init__(config: TTSGenConfig | None = None) -> None`**
Initialize TTS generator. Auto-detects Bark vs XTTS-v2 from model_id.

**`load() -> bool`**
Load TTS model to device.

**`unload() -> None`**
Unload model and free memory.

**`generate_speech(text: str, speaker_id: str = "en_speaker_0", language: str = "en", temperature: float = 0.75, emotion: str | None = None) -> np.ndarray`**
Generate speech from text.

Parameters:
- `text` (str): Text to synthesize
- `speaker_id` (str): Speaker voice identifier
  - Bark: "en_speaker_0" through "en_speaker_9" (English)
  - XTTS-v2: "default_speaker" (uses language setting)
- `language` (str): Language code ("en", "es", "fr", "de", "it", "pt", "pl", "zh", "ar", "cs", "ru", "nl", "tr", "ja", "ko", "hi")
- `temperature` (float): Bark only - generation randomness (0.1-1.0, default 0.75)
- `emotion` (str|None): Bark only - emotion preset (e.g., "Cheerful speaking", "Sad speaking", "Angry speaking")

Returns: Numpy float32 audio array (24000 Hz, mono)

Example (Bark):
```python
gen = TTSGenerator(TTSGenConfig(model_id="suno/bark"))
audio = gen.generate_speech(
    text="Hello! This is a cheerful message.",
    speaker_id="en_speaker_3",
    emotion="Cheerful speaking",
    temperature=0.8,
)
import soundfile as sf
sf.write("speech.wav", audio, samplerate=24000)
gen.unload()
```

Example (XTTS-v2):
```python
gen = TTSGenerator(TTSGenConfig(model_id="coqui/XTTS-v2"))
audio = gen.generate_speech(
    text="Bonjour, comment allez-vous?",
    language="fr",
)
sf.write("french_speech.wav", audio, samplerate=24000)
```

**`clone_voice(reference_audio_path: str, text: str, language: str = "en") -> np.ndarray`**
Clone voice from reference audio (XTTS-v2 only).

Parameters:
- `reference_audio_path` (str): Path to WAV/MP3 file with target voice
- `text` (str): Text to synthesize
- `language` (str): Language code

Returns: Numpy audio array with cloned voice

Example:
```python
gen = TTSGenerator(TTSGenConfig(model_id="coqui/XTTS-v2"))
cloned = gen.clone_voice(
    reference_audio_path="speaker_sample.wav",
    text="Now I'm speaking in your voice!",
    language="en",
)
sf.write("cloned.wav", cloned, samplerate=24000)
```

---

## MusicGenerator

### Class: `MusicGenerator`
Music generation using Meta's MusicGen.

#### Configuration
```python
@dataclass
class MusicGenConfig:
    model_id: str = "facebook/musicgen-small"
    device: str = "cuda"
    sample_rate: int = 32000
```

#### Methods

**`__init__(config: MusicGenConfig | None = None) -> None`**
Initialize music generator.

**`load() -> bool`**
Load MusicGen model to device.

**`unload() -> None`**
Unload model and free memory.

**`generate(prompt: str, duration_seconds: float = 30.0, max_new_tokens: int | None = None, guidance_scale: float = 3.0, num_inference_steps: int | None = None, top_k: int = 250, top_p: float = 0.0, temperature: float = 1.0, seed: int | None = None) -> np.ndarray`**
Generate music from text description.

Parameters:
- `prompt` (str): Music description (e.g., "uplifting orchestral with strings", "heavy metal guitar riff", "ambient electronic")
- `duration_seconds` (float): Target duration (default 30.0)
- `max_new_tokens` (int|None): Override duration with token count (~50 tokens per second)
- `guidance_scale` (float): Prompt adherence (typical 3.0, range 1-15)
- `num_inference_steps` (int|None): Generation steps (affects quality/speed)
- `top_k` (int): Top-K sampling (default 250)
- `top_p` (float): Nucleus sampling (default 0.0 = disabled)
- `temperature` (float): Sampling temperature (typical 1.0, range 0.1-2.0)
- `seed` (int|None): Random seed

Returns: Numpy float32 audio array (32000 Hz, stereo or mono depending on model)

Example:
```python
gen = MusicGenerator(MusicGenConfig(model_id="facebook/musicgen-medium"))
audio = gen.generate(
    prompt="Uplifting orchestral music with strings and brass, energetic tempo",
    duration_seconds=30,
    guidance_scale=3.0,
    temperature=1.0,
    seed=42,
)
import soundfile as sf
sf.write("music.wav", audio, samplerate=32000)
gen.unload()
```

**`continue_music(prompt: str, initial_audio: np.ndarray, duration_seconds: float = 30.0, overlap_seconds: float = 2.0, guidance_scale: float = 3.0, top_k: int = 250, temperature: float = 1.0, seed: int | None = None) -> np.ndarray`**
Extend/continue existing music with automatic crossfading.

Parameters:
- `prompt` (str): Description of music continuation/evolution
- `initial_audio` (np.ndarray): Existing audio to continue from
- `duration_seconds` (float): Duration of new music to generate
- `overlap_seconds` (float): Crossfade overlap for smooth transition (default 2.0)
- `guidance_scale` (float): Prompt adherence
- `top_k` (int): Top-K sampling
- `temperature` (float): Sampling temperature
- `seed` (int|None): Random seed

Returns: Extended audio array (initial + new with crossfade)

Example:
```python
gen = MusicGenerator()
# Generate initial section
audio1 = gen.generate(
    prompt="Calm ambient introduction with piano",
    duration_seconds=20,
)
# Continue with more energy
audio2 = gen.continue_music(
    prompt="Transition to faster paced with drums and bass",
    initial_audio=audio1,
    duration_seconds=20,
    overlap_seconds=2.0,
)
sf.write("full_track.wav", audio2, samplerate=32000)
```

---

## VideoUpscaler

### Class: `VideoUpscaler`
Image and video upscaling using Real-ESRGAN.

#### Configuration
```python
@dataclass
class UpscaleConfig:
    model_id: str = "RealESRGAN_x4plus"
    device: str = "cuda"
    tile_size: int = 400
```

#### Methods

**`__init__(config: UpscaleConfig | None = None) -> None`**
Initialize upscaler.

**`load() -> bool`**
Load upscaling model to device.

**`unload() -> None`**
Unload model and free memory.

**`upscale_frame(image: Image.Image, scale: int | None = None) -> Image.Image`**
Upscale a single image.

Parameters:
- `image` (Image.Image): PIL Image to upscale
- `scale` (int|None): Upscale factor (2, 3, or 4). If None, uses model's native scale.

Returns: Upscaled PIL Image

Example:
```python
upscaler = VideoUpscaler(UpscaleConfig(model_id="RealESRGAN_x4plus"))
img = Image.open("low_res.png")
hires = upscaler.upscale_frame(img, scale=4)
hires.save("high_res.png")
print(f"Original: {img.size}, Upscaled: {hires.size}")
upscaler.unload()
```

**`upscale_video(frames: list[Image.Image], scale: int | None = None, save_dir: Path | None = None) -> list[Image.Image]`**
Upscale video frames with optional saving.

Parameters:
- `frames` (list[Image.Image]): List of PIL Images
- `scale` (int|None): Upscale factor
- `save_dir` (Path|None): Optional directory to save upscaled frames

Returns: List of upscaled PIL Images

Example:
```python
from pathlib import Path
upscaler = VideoUpscaler()
frames = [Image.open(f"frame_{i}.png") for i in range(50)]
upscaled = upscaler.upscale_video(
    frames,
    scale=4,
    save_dir=Path("upscaled_frames"),
)
print(f"Upscaled {len(upscaled)} frames")
```

**`upscale_batch(image_paths: list[str | Path], output_dir: Path, scale: int | None = None) -> list[Path]`**
Upscale images from disk and save to directory.

Parameters:
- `image_paths` (list[str|Path]): List of input image paths
- `output_dir` (Path): Output directory for upscaled images
- `scale` (int|None): Upscale factor

Returns: List of output file paths

Example:
```python
upscaler = VideoUpscaler(UpscaleConfig(model_id="RealESRGAN_x2plus"))
output_paths = upscaler.upscale_batch(
    image_paths=["img1.jpg", "img2.jpg", "img3.jpg"],
    output_dir=Path("upscaled"),
    scale=2,
)
for path in output_paths:
    print(f"Saved: {path}")
```

**`estimate_upscale_time(image_size_pixels: int, scale_factor: int | None = None) -> float`**
Estimate upscaling time for an image.

Parameters:
- `image_size_pixels` (int): Total pixels (width * height)
- `scale_factor` (int|None): Scale factor

Returns: Estimated time in seconds

Example:
```python
upscaler = VideoUpscaler()
time_estimate = upscaler.estimate_upscale_time(
    image_size_pixels=1024 * 768,
    scale_factor=4,
)
print(f"Estimated time: {time_estimate:.2f}s")
```

---

## Common Patterns

### Safe Model Loading
```python
gen = ImageGenerator(config)
if gen.load():
    image = gen.generate(prompt="...")
    gen.unload()
else:
    print("Model not available, using synthetic")
```

### Batch Processing
```python
gen = ImageGenerator()
gen.load()  # Load once

for prompt in prompts:
    image = gen.generate(prompt=prompt)
    image.save(f"{prompt_id}.png")

gen.unload()  # Unload after batch
```

### Error Handling
```python
try:
    gen = VideoGenerator()
    frames = gen.text_to_video(prompt=prompt)
except Exception as e:
    logger.error(f"Generation failed: {e}")
    # Falls back to synthetic internally
finally:
    gen.unload()
```

### Memory Monitoring
```python
import torch
gen = ImageGenerator()
print(f"VRAM before load: {torch.cuda.memory_allocated() / 1e9:.1f}GB")
gen.load()
print(f"VRAM after load: {torch.cuda.memory_allocated() / 1e9:.1f}GB")
image = gen.generate(prompt="...")
gen.unload()
print(f"VRAM after unload: {torch.cuda.memory_allocated() / 1e9:.1f}GB")
```
