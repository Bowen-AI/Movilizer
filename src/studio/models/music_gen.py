"""Real music generation with MusicGen."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from ..utils import get_logger

logger = get_logger("models.music_gen")


@dataclass
class MusicGenConfig:
    """Configuration for music generation models."""

    model_id: str = "facebook/musicgen-small"
    device: str = "cuda"
    sample_rate: int = 32000


class MusicGenerator:
    """Generate music from text using Meta's MusicGen."""

    SUPPORTED_MODELS = {
        "musicgen-small": "facebook/musicgen-small",
        "musicgen-medium": "facebook/musicgen-medium",
        "musicgen-large": "facebook/musicgen-large",
    }

    def __init__(self, config: MusicGenConfig | None = None) -> None:
        """Initialize MusicGenerator with optional model configuration."""
        self.config = config or MusicGenConfig()
        self.model = None
        self.processor = None
        self._is_loaded = False
        self._attempted_load = False

    def load(self) -> bool:
        """Load the music generation model to device."""
        if self._is_loaded:
            return True

        if self._attempted_load:
            return False

        self._attempted_load = True

        try:
            from transformers import AutoProcessor, MusicgenForConditionalGeneration

            logger.info(f"Loading MusicGen model: {self.config.model_id}")

            self.processor = AutoProcessor.from_pretrained(self.config.model_id)
            self.model = MusicgenForConditionalGeneration.from_pretrained(
                self.config.model_id
            )
            self.model = self.model.to(self.config.device)

            # Optimize memory
            try:
                if hasattr(self.model, "enable_cpu_offload"):
                    self.model.enable_cpu_offload()
            except Exception:
                pass

            self._is_loaded = True
            logger.info("MusicGen model loaded successfully")
            return True

        except ImportError as e:
            logger.warning(f"MusicGen dependencies not installed: {e}")
            return False
        except Exception as e:
            logger.warning(f"Failed to load MusicGen model: {e}")
            return False

    def unload(self) -> None:
        """Unload model and free memory."""
        if self.model is not None or self.processor is not None:
            try:
                import torch

                self.model = None
                self.processor = None
                torch.cuda.empty_cache()
                logger.info("MusicGen model unloaded")
            except Exception as e:
                logger.warning(f"Error unloading model: {e}")
        self._is_loaded = False

    def generate(
        self,
        prompt: str,
        duration_seconds: float = 30.0,
        max_new_tokens: int | None = None,
        guidance_scale: float = 3.0,
        num_inference_steps: int | None = None,
        top_k: int = 250,
        top_p: float = 0.0,
        temperature: float = 1.0,
        seed: int | None = None,
    ) -> np.ndarray:
        """
        Generate music from text prompt.

        Args:
            prompt: Description of the music to generate
            duration_seconds: Target duration in seconds
            max_new_tokens: Maximum tokens to generate (overrides duration)
            guidance_scale: Strength of guidance (higher = more adherent to prompt)
            num_inference_steps: Number of generation steps
            top_k: Sampling parameter
            top_p: Nucleus sampling parameter
            temperature: Sampling temperature
            seed: Random seed for reproducibility

        Returns:
            Numpy audio array (stereo, 32kHz or model-specific rate)
        """
        if not self.load():
            logger.warning("MusicGen model not available, returning synthetic audio")
            return self._generate_synthetic_audio(prompt, duration_seconds)

        try:
            import torch

            logger.info(f"Generating music: {prompt[:80]}... ({duration_seconds:.1f}s)")

            # Calculate tokens from duration if not specified
            if max_new_tokens is None:
                max_new_tokens = int((duration_seconds / 30.0) * 1500)

            # Set seed for reproducibility
            if seed is not None:
                torch.manual_seed(seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed(seed)

            # Tokenize input
            inputs = self.processor(
                text=[prompt],
                padding=True,
                return_tensors="pt",
            )

            # Generate
            audio_values = self.model.generate(
                inputs["input_ids"].to(self.config.device),
                attention_mask=inputs.get("attention_mask", None),
                do_sample=True,
                top_k=top_k,
                top_p=top_p,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
                guidance_scale=guidance_scale,
            )

            # Convert to numpy
            audio = audio_values.cpu().numpy()
            if audio.ndim == 3:
                audio = audio[0]  # Remove batch dimension

            # Normalize
            audio = audio.astype(np.float32)
            max_val = np.max(np.abs(audio))
            if max_val > 1.0:
                audio = audio / max_val

            logger.info(f"Music generation completed: {audio.shape} @ {self.config.sample_rate}Hz")
            return audio

        except Exception as e:
            logger.error(f"Music generation failed: {e}")
            return self._generate_synthetic_audio(prompt, duration_seconds)

    def continue_music(
        self,
        prompt: str,
        initial_audio: np.ndarray,
        duration_seconds: float = 30.0,
        overlap_seconds: float = 2.0,
        guidance_scale: float = 3.0,
        top_k: int = 250,
        temperature: float = 1.0,
        seed: int | None = None,
    ) -> np.ndarray:
        """
        Continue/extend existing music based on a prompt.

        Args:
            prompt: Description of how the music should continue/evolve
            initial_audio: Existing audio to continue from
            duration_seconds: Duration of new audio to generate
            overlap_seconds: Overlap period for blending
            guidance_scale: Strength of guidance
            top_k: Sampling parameter
            temperature: Sampling temperature
            seed: Random seed

        Returns:
            Numpy audio array (extended music)
        """
        if not self.load():
            logger.warning("MusicGen model not available, returning original audio")
            return initial_audio

        try:
            import torch

            logger.info(f"Continuing music: {prompt[:80]}...")

            # For now, generate new audio and concatenate with overlap
            # A more sophisticated approach would condition on the initial audio
            new_audio = self.generate(
                prompt=prompt,
                duration_seconds=duration_seconds,
                guidance_scale=guidance_scale,
                top_k=top_k,
                temperature=temperature,
                seed=seed,
            )

            # Simple concatenation with crossfade overlap
            overlap_samples = int(overlap_seconds * self.config.sample_rate)
            if overlap_samples > 0 and len(initial_audio) > overlap_samples:
                # Linear crossfade
                fade_out = np.linspace(1.0, 0.0, overlap_samples)
                fade_in = np.linspace(0.0, 1.0, overlap_samples)

                overlap_region = (
                    initial_audio[-overlap_samples:] * fade_out
                    + new_audio[:overlap_samples] * fade_in
                )
                result = np.concatenate(
                    [initial_audio[:-overlap_samples], overlap_region, new_audio[overlap_samples:]]
                )
            else:
                result = np.concatenate([initial_audio, new_audio])

            logger.info(
                f"Music continuation completed: {len(result) / self.config.sample_rate:.2f}s"
            )
            return result.astype(np.float32)

        except Exception as e:
            logger.error(f"Music continuation failed: {e}")
            return initial_audio

    @staticmethod
    def _generate_synthetic_audio(prompt: str, duration_seconds: float) -> np.ndarray:
        """Generate simple synthetic audio when model is unavailable."""
        import random

        sample_rate = 32000
        num_samples = int(duration_seconds * sample_rate)

        # Synthetic music: combination of sine waves
        seed = hash(prompt) & 0x7FFFFFFF
        random.seed(seed)
        np.random.seed(seed % (2**32 - 1))

        t = np.linspace(0, duration_seconds, num_samples)

        # Base frequencies from prompt
        base_freq = 200 + (len(prompt) % 50) * 10
        overtones = [base_freq, base_freq * 1.5, base_freq * 2.0]

        # Build chord
        audio = np.zeros(num_samples)
        for freq in overtones:
            audio += 0.3 * np.sin(2 * np.pi * freq * t)

        # Add gentle noise
        audio += 0.05 * np.random.randn(num_samples)

        # Normalize
        audio = audio / (np.max(np.abs(audio)) + 1e-6)

        # Apply envelope
        envelope = np.linspace(0, 1, num_samples // 10)
        audio[: len(envelope)] *= envelope
        envelope = np.linspace(1, 0, num_samples // 10)
        audio[-len(envelope) :] *= envelope

        return audio.astype(np.float32)
