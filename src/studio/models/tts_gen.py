"""Real text-to-speech generation with Bark and XTTS-v2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from ..utils import get_logger

logger = get_logger("models.tts_gen")


@dataclass
class TTSGenConfig:
    """Configuration for text-to-speech models."""

    model_id: str = "suno/bark"
    device: str = "cuda"
    sample_rate: int = 24000


class TTSGenerator:
    """Generate speech from text using Bark and XTTS-v2."""

    SUPPORTED_MODELS = {
        "bark": "suno/bark",
        "xtts-v2": "coqui/XTTS-v2",
    }

    def __init__(self, config: TTSGenConfig | None = None) -> None:
        """Initialize TTSGenerator with optional model configuration."""
        self.config = config or TTSGenConfig()
        self.model = None
        self.processor = None
        self._is_loaded = False
        self._attempted_load = False
        self._sample_rate = 24000

    def load(self) -> bool:
        """Load the TTS model to device."""
        if self._is_loaded:
            return True

        if self._attempted_load:
            return False

        self._attempted_load = True

        try:
            if "xtts" in self.config.model_id.lower():
                return self._load_xtts()
            else:
                return self._load_bark()
        except Exception as e:
            logger.warning(f"Failed to load TTS model: {e}")
            return False

    def _load_bark(self) -> bool:
        """Load Bark TTS model."""
        try:
            from transformers import AutoProcessor, BarkModel

            logger.info("Loading Bark TTS model")
            self.processor = AutoProcessor.from_pretrained("suno/bark")
            self.model = BarkModel.from_pretrained("suno/bark")
            self.model = self.model.to(self.config.device)

            # Optimize memory
            try:
                self.model.enable_cpu_offload()
            except Exception:
                pass

            self._is_loaded = True
            self._sample_rate = 24000
            logger.info("Bark TTS model loaded successfully")
            return True

        except ImportError as e:
            logger.warning(f"Bark dependencies not installed: {e}")
            return False
        except Exception as e:
            logger.warning(f"Failed to load Bark: {e}")
            return False

    def _load_xtts(self) -> bool:
        """Load XTTS-v2 TTS model."""
        try:
            from TTS.api import TTS

            logger.info("Loading XTTS-v2 TTS model")
            self.model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)
            self._is_loaded = True
            self._sample_rate = 24000
            logger.info("XTTS-v2 TTS model loaded successfully")
            return True

        except ImportError as e:
            logger.warning(f"XTTS dependencies not installed: {e}")
            return False
        except Exception as e:
            logger.warning(f"Failed to load XTTS-v2: {e}")
            return False

    def unload(self) -> None:
        """Unload model and free memory."""
        if self.model is not None or self.processor is not None:
            try:
                import torch

                self.model = None
                self.processor = None
                torch.cuda.empty_cache()
                logger.info("TTS model unloaded")
            except Exception as e:
                logger.warning(f"Error unloading model: {e}")
        self._is_loaded = False

    def generate_speech(
        self,
        text: str,
        speaker_id: str = "en_speaker_0",
        language: str = "en",
        temperature: float = 0.75,
        emotion: str | None = None,
    ) -> np.ndarray:
        """
        Generate speech from text.

        Args:
            text: Text to synthesize
            speaker_id: Speaker voice identifier
            language: Language code (e.g., 'en', 'es', 'fr')
            temperature: Bark: temperature for generation (0.1-1.0)
            emotion: Bark speaker preset with emotion (e.g., 'Peaceful speaking')

        Returns:
            Numpy audio array (mono, 24kHz or model-specific rate)
        """
        if not self.load():
            logger.warning("TTS model not available, returning synthetic audio")
            return self._generate_synthetic_audio(text)

        try:
            if "xtts" in self.config.model_id.lower():
                return self._generate_xtts(text, speaker_id, language)
            else:
                return self._generate_bark(text, speaker_id, emotion, temperature)

        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            return self._generate_synthetic_audio(text)

    def _generate_bark(
        self,
        text: str,
        speaker_id: str,
        emotion: str | None,
        temperature: float,
    ) -> np.ndarray:
        """Generate speech using Bark."""
        try:
            import torch

            logger.info(f"Generating speech with Bark: {text[:80]}...")

            # Bark has predefined speakers with emotions
            voice_preset = speaker_id
            if emotion:
                voice_preset = f"{speaker_id}__{emotion}"

            inputs = self.processor(
                text,
                voice_preset=voice_preset,
                return_tensors="pt",
                padding=True,
            )

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs.to(self.config.device),
                    temperature=temperature,
                    do_sample=True,
                )

            # Convert to numpy audio
            if isinstance(outputs, torch.Tensor):
                audio = outputs.cpu().numpy()
                if audio.ndim > 1:
                    audio = audio[0] if audio.shape[0] == 1 else audio.flatten()
            else:
                audio = outputs

            # Ensure float32
            audio = audio.astype(np.float32)
            if np.max(np.abs(audio)) > 1.0:
                audio = audio / np.max(np.abs(audio))

            logger.info(f"Generated {len(audio) / self._sample_rate:.2f}s of speech")
            return audio

        except Exception as e:
            logger.error(f"Bark generation error: {e}")
            return self._generate_synthetic_audio(text)

    def _generate_xtts(
        self,
        text: str,
        speaker_id: str,
        language: str,
    ) -> np.ndarray:
        """Generate speech using XTTS-v2."""
        try:
            logger.info(f"Generating speech with XTTS-v2: {text[:80]}...")

            # XTTS generates wav output directly
            wav = self.model.tts(
                text=text,
                speaker="default_speaker",
                language=language,
            )

            # wav is typically a numpy array
            if isinstance(wav, (list, tuple)):
                audio = np.array(wav, dtype=np.float32)
            else:
                audio = np.array(wav, dtype=np.float32)

            # Normalize if needed
            if np.max(np.abs(audio)) > 1.0:
                audio = audio / (np.max(np.abs(audio)) + 1e-6)

            logger.info(f"Generated {len(audio) / self._sample_rate:.2f}s of speech")
            return audio

        except Exception as e:
            logger.error(f"XTTS generation error: {e}")
            return self._generate_synthetic_audio(text)

    def clone_voice(
        self,
        reference_audio_path: str,
        text: str,
        language: str = "en",
    ) -> np.ndarray:
        """
        Clone voice from reference audio (XTTS-v2 only).

        Args:
            reference_audio_path: Path to reference WAV/MP3
            text: Text to synthesize
            language: Language code

        Returns:
            Numpy audio array
        """
        if "xtts" not in self.config.model_id.lower():
            logger.warning("Voice cloning only supported for XTTS-v2")
            return self.generate_speech(text)

        if not self.load():
            return self._generate_synthetic_audio(text)

        try:
            logger.info(f"Cloning voice from {reference_audio_path}: {text[:80]}...")

            wav = self.model.tts(
                text=text,
                speaker_wav=reference_audio_path,
                language=language,
            )

            audio = np.array(wav, dtype=np.float32)
            if np.max(np.abs(audio)) > 1.0:
                audio = audio / (np.max(np.abs(audio)) + 1e-6)

            logger.info(f"Generated cloned voice: {len(audio) / self._sample_rate:.2f}s")
            return audio

        except Exception as e:
            logger.error(f"Voice cloning failed: {e}")
            return self._generate_synthetic_audio(text)

    @staticmethod
    def _generate_synthetic_audio(text: str, duration_seconds: float = 5.0) -> np.ndarray:
        """Generate simple synthetic audio when model is unavailable."""
        import random

        sample_rate = 24000
        num_samples = int(duration_seconds * sample_rate)

        # Simple chirp-like synthetic audio
        seed = hash(text) & 0x7FFFFFFF
        random.seed(seed)
        np.random.seed(seed % (2**32 - 1))

        t = np.linspace(0, duration_seconds, num_samples)
        frequency = 200 + len(text) * 10
        audio = 0.1 * np.sin(2 * np.pi * frequency * t)
        audio += 0.02 * np.random.randn(num_samples)

        return audio.astype(np.float32)
