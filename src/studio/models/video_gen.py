"""Real video generation with CogVideoX, Wan2.1, AnimateDiff."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from ..utils import get_logger

logger = get_logger("models.video_gen")


@dataclass
class VideoGenConfig:
    """Configuration for video generation models."""

    model_id: str = "THUDM/CogVideoX-2B"
    num_frames: int = 49
    dtype_a100: str = "bfloat16"
    dtype_consumer: str = "float16"
    device: str = "cuda"
    max_model_size_gb: float = 8.0


class VideoGenerator:
    """Generate videos using diffusion models (CogVideoX-2B, CogVideoX-5B, Wan2.1-T2V, AnimateDiff)."""

    SUPPORTED_MODELS = {
        "cogvideox-2b": "THUDM/CogVideoX-2B",
        "cogvideox-5b": "THUDM/CogVideoX-5B",
        "wan-t2v": "Wan2.1-T2V",
        "animatediff": "guoyww/animatediff",
    }

    def __init__(self, config: VideoGenConfig | None = None) -> None:
        """Initialize VideoGenerator with optional model configuration."""
        self.config = config or VideoGenConfig()
        self.pipeline = None
        self._is_loaded = False
        self._gpu_info = None
        self._attempted_load = False

    def _get_dtype(self) -> object:
        """Determine appropriate dtype based on GPU capabilities."""
        if self._gpu_info is None:
            try:
                from ..gpu.discovery import GPUDiscovery

                discovery = GPUDiscovery()
                gpus = discovery.get_gpus()
                self._gpu_info = gpus[0] if gpus else None
            except Exception as e:
                logger.warning(f"Could not detect GPU info: {e}")
                self._gpu_info = None

        if self._gpu_info and (self._gpu_info.is_a100_40gb or self._gpu_info.is_a100_80gb):
            import torch

            return torch.bfloat16
        else:
            import torch

            return torch.float16

    def _check_available_vram(self) -> float:
        """Check available VRAM in GB."""
        try:
            import torch

            if torch.cuda.is_available():
                return torch.cuda.get_device_properties(0).total_memory / (1024**3)
        except Exception as e:
            logger.debug(f"Could not check VRAM: {e}")
        return 0.0

    def _select_model_for_vram(self) -> str:
        """Select appropriate model based on available VRAM."""
        available_vram = self._check_available_vram()
        logger.info(f"Available VRAM: {available_vram:.1f}GB")

        model_vram_requirements = {
            "THUDM/CogVideoX-2B": 6.0,
            "THUDM/CogVideoX-5B": 10.0,
            "Wan2.1-T2V": 12.0,
            "guoyww/animatediff": 4.0,
        }

        # If model is explicitly set, try to use it
        if self.config.model_id in model_vram_requirements:
            req = model_vram_requirements[self.config.model_id]
            if available_vram >= req:
                logger.info(f"Using configured model: {self.config.model_id}")
                return self.config.model_id
            else:
                logger.warning(
                    f"Configured model {self.config.model_id} requires {req}GB but only {available_vram:.1f}GB available"
                )

        # Fall back to smallest model that fits
        for model_id, required_vram in sorted(
            model_vram_requirements.items(), key=lambda x: x[1]
        ):
            if available_vram >= required_vram:
                logger.info(f"Selected model {model_id} for available VRAM")
                return model_id

        logger.warning(
            f"Insufficient VRAM ({available_vram:.1f}GB) for any video model. Will use synthetic fallback."
        )
        return self.config.model_id

    def load(self) -> bool:
        """Load the video generation model to GPU."""
        if self._is_loaded:
            return True

        if self._attempted_load:
            return False

        self._attempted_load = True

        try:
            import torch
            from diffusers import DiffusionPipeline
        except ImportError as e:
            logger.warning(f"diffusers not installed: {e}. Falling back to synthetic.")
            return False

        try:
            # Select model based on available VRAM
            model_id = self._select_model_for_vram()
            logger.info(f"Loading video generation model: {model_id}")

            dtype = self._get_dtype()

            # Load appropriate pipeline
            try:
                if "CogVideoX" in model_id:
                    from diffusers import CogVideoXPipeline

                    self.pipeline = CogVideoXPipeline.from_pretrained(
                        model_id, torch_dtype=dtype
                    )
                else:
                    # Generic fallback
                    self.pipeline = DiffusionPipeline.from_pretrained(
                        model_id, torch_dtype=dtype
                    )
            except ImportError:
                # If specific pipeline not available, use generic
                self.pipeline = DiffusionPipeline.from_pretrained(model_id, torch_dtype=dtype)

            self.pipeline = self.pipeline.to(self.config.device)

            # Enable memory optimizations
            try:
                if hasattr(self.pipeline, "enable_attention_slicing"):
                    self.pipeline.enable_attention_slicing()
                if hasattr(self.pipeline, "enable_xformers_memory_efficient_attention"):
                    self.pipeline.enable_xformers_memory_efficient_attention()
                if hasattr(self.pipeline, "enable_sequential_cpu_offload"):
                    self.pipeline.enable_sequential_cpu_offload()
            except Exception as e:
                logger.debug(f"Could not enable memory optimizations: {e}")

            self._is_loaded = True
            logger.info("Video generation model loaded successfully")
            return True

        except Exception as e:
            logger.warning(f"Failed to load video generation model: {e}")
            self._is_loaded = False
            return False

    def unload(self) -> None:
        """Unload model and free GPU memory."""
        if self.pipeline is not None:
            try:
                import torch

                self.pipeline = None
                torch.cuda.empty_cache()
                logger.info("Video generation model unloaded")
            except Exception as e:
                logger.warning(f"Error unloading model: {e}")
        self._is_loaded = False

    def text_to_video(
        self,
        prompt: str,
        negative_prompt: str = "",
        num_frames: int | None = None,
        height: int = 512,
        width: int = 512,
        guidance_scale: float = 7.5,
        num_inference_steps: int = 50,
        seed: int | None = None,
    ) -> list[Image.Image]:
        """
        Generate video frames from text prompt.

        Args:
            prompt: Text description of the video
            negative_prompt: What NOT to generate
            num_frames: Number of frames to generate
            height: Frame height in pixels
            width: Frame width in pixels
            guidance_scale: How much to follow the prompt
            num_inference_steps: Number of denoising steps
            seed: Random seed for reproducibility

        Returns:
            List of PIL Images (video frames)
        """
        if not self.load():
            logger.warning("Video generation model not available, returning synthetic frames")
            return self._generate_synthetic_frames(
                prompt,
                num_frames or self.config.num_frames,
                height,
                width,
                seed or 0,
            )

        try:
            import torch

            num_frames = num_frames or self.config.num_frames
            logger.info(
                f"Generating video: {prompt[:80]}... ({width}x{height}, {num_frames} frames, steps={num_inference_steps})"
            )

            # Set seed for reproducibility
            if seed is not None:
                generator = torch.Generator(device=self.config.device).manual_seed(seed)
            else:
                generator = None

            # Prepare pipeline inputs
            pipeline_kwargs = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "num_frames": num_frames,
                "height": height,
                "width": width,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
            }

            if generator is not None:
                pipeline_kwargs["generator"] = generator

            # Generate
            result = self.pipeline(**pipeline_kwargs)

            # Extract frames from result
            if hasattr(result, "frames"):
                frames = result.frames
            elif isinstance(result, (list, tuple)):
                frames = result
            else:
                logger.warning("Unexpected pipeline output format")
                frames = []

            # Convert to PIL Images if needed
            pil_frames = []
            for frame in frames:
                if isinstance(frame, Image.Image):
                    pil_frames.append(frame)
                elif isinstance(frame, np.ndarray):
                    pil_frames.append(Image.fromarray(frame))
                else:
                    logger.warning(f"Unexpected frame type: {type(frame)}")

            logger.info(f"Video generation completed: {len(pil_frames)} frames")
            return pil_frames

        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            return self._generate_synthetic_frames(
                prompt,
                num_frames or self.config.num_frames,
                height,
                width,
                seed or 0,
            )

    def image_to_video(
        self,
        image: Image.Image,
        prompt: str,
        num_frames: int | None = None,
        negative_prompt: str = "",
        guidance_scale: float = 7.5,
        num_inference_steps: int = 50,
        seed: int | None = None,
    ) -> list[Image.Image]:
        """
        Generate video from initial image.

        Args:
            image: Starting image
            prompt: Description of video motion/evolution
            num_frames: Number of frames to generate
            negative_prompt: What NOT to generate
            guidance_scale: How much to follow the prompt
            num_inference_steps: Number of denoising steps
            seed: Random seed for reproducibility

        Returns:
            List of PIL Images (video frames)
        """
        if not self.load():
            logger.warning("Video generation model not available, returning synthetic frames")
            return self._generate_synthetic_frames(
                prompt,
                num_frames or self.config.num_frames,
                image.height,
                image.width,
                seed or 0,
            )

        try:
            import torch

            num_frames = num_frames or self.config.num_frames
            logger.info(
                f"Generating video from image: {prompt[:80]}... ({image.width}x{image.height}, {num_frames} frames)"
            )

            # Set seed for reproducibility
            if seed is not None:
                generator = torch.Generator(device=self.config.device).manual_seed(seed)
            else:
                generator = None

            # Prepare pipeline inputs - image_to_video if supported
            pipeline_kwargs = {
                "image": image,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "num_frames": num_frames,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
            }

            if generator is not None:
                pipeline_kwargs["generator"] = generator

            # Try image_to_video if available
            if hasattr(self.pipeline, "__call__") and "image" in str(
                self.pipeline.__call__.__doc__ or ""
            ):
                result = self.pipeline(**pipeline_kwargs)
            else:
                logger.info("Pipeline does not support image-to-video, using text-to-video")
                return self.text_to_video(prompt, negative_prompt, num_frames)

            # Extract frames
            if hasattr(result, "frames"):
                frames = result.frames
            elif isinstance(result, (list, tuple)):
                frames = result
            else:
                frames = []

            # Convert to PIL Images
            pil_frames = []
            for frame in frames:
                if isinstance(frame, Image.Image):
                    pil_frames.append(frame)
                elif isinstance(frame, np.ndarray):
                    pil_frames.append(Image.fromarray(frame))

            logger.info(f"Image-to-video generation completed: {len(pil_frames)} frames")
            return pil_frames

        except Exception as e:
            logger.error(f"Image-to-video generation failed: {e}")
            return self._generate_synthetic_frames(
                prompt,
                num_frames or self.config.num_frames,
                image.height,
                image.width,
                seed or 0,
            )

    @staticmethod
    def _generate_synthetic_frames(
        prompt: str, num_frames: int, height: int, width: int, seed: int
    ) -> list[Image.Image]:
        """Generate synthetic video frames when model is unavailable."""
        import random

        random.seed(seed)
        np.random.seed(seed % (2**32 - 1))

        frames = []
        for frame_idx in range(num_frames):
            # Create frame with slight animation
            frame_seed = seed + frame_idx
            random.seed(frame_seed)
            np.random.seed(frame_seed % (2**32 - 1))

            base = np.zeros((height, width, 3), dtype=np.uint8)
            hue = abs(hash(prompt)) % 255
            base[:, :, 0] = (hue + frame_idx * 2) % 255
            base[:, :, 1] = (100 + frame_idx) % 255
            base[:, :, 2] = 180

            noise = np.random.randint(0, 35, size=(height, width, 3), dtype=np.uint8)
            arr = np.clip(base + noise, 0, 255)

            from PIL import ImageDraw

            img = Image.fromarray(arr, mode="RGB")
            draw = ImageDraw.Draw(img)
            draw.rectangle((0, 0, width, 80), fill=(0, 0, 0))
            draw.text((10, 10), f"prompt: {prompt[:50]}", fill=(200, 200, 200))
            draw.text((10, 40), f"frame={frame_idx}/{num_frames}", fill=(180, 180, 180))

            frames.append(img)

        return frames
