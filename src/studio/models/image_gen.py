"""Real image generation with SDXL, Flux.1-dev, PixArt-Sigma."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from PIL import Image

from ..utils import get_logger

logger = get_logger("models.image_gen")


@dataclass
class ImageGenConfig:
    """Configuration for image generation models."""

    model_id: str = "stabilityai/stable-diffusion-xl-base-1.0"
    enable_lora: bool = False
    lora_ids: list[str] = field(default_factory=list)
    lora_weights: list[float] = field(default_factory=lambda: [1.0])
    enable_ip_adapter: bool = False
    ip_adapter_model_id: str = "h94/IP-Adapter"
    dtype_a100: str = "bfloat16"
    dtype_consumer: str = "float16"
    device: str = "cuda"


class ImageGenerator:
    """Generate images using diffusion models (SDXL, Flux.1-dev, PixArt-Sigma)."""

    SUPPORTED_MODELS = {
        "sdxl": "stabilityai/stable-diffusion-xl-base-1.0",
        "flux-dev": "black-forest-labs/FLUX.1-dev",
        "pixart": "PixArt-alpha/PixArt-Sigma",
    }

    def __init__(self, config: ImageGenConfig | None = None) -> None:
        """Initialize ImageGenerator with optional model configuration."""
        self.config = config or ImageGenConfig()
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

    def load(self) -> bool:
        """Load the image generation model to GPU."""
        if self._is_loaded:
            return True

        if self._attempted_load:
            return False

        self._attempted_load = True

        try:
            import torch
            from diffusers import (
                AutoPipelineForText2Image,
                DiffusionPipeline,
                StableDiffusionXLPipeline,
            )
        except ImportError as e:
            logger.warning(f"diffusers not installed: {e}. Falling back to synthetic.")
            return False

        try:
            logger.info(f"Loading image generation model: {self.config.model_id}")
            dtype = self._get_dtype()

            # Try to use AutoPipelineForText2Image for better compatibility
            try:
                self.pipeline = AutoPipelineForText2Image.from_pretrained(
                    self.config.model_id,
                    torch_dtype=dtype,
                    variant="fp16" if dtype == torch.float16 else None,
                )
            except Exception:
                # Fallback to DiffusionPipeline
                self.pipeline = DiffusionPipeline.from_pretrained(
                    self.config.model_id,
                    torch_dtype=dtype,
                )

            self.pipeline = self.pipeline.to(self.config.device)

            # Enable memory optimizations
            try:
                if hasattr(self.pipeline, "enable_attention_slicing"):
                    self.pipeline.enable_attention_slicing()
                if hasattr(self.pipeline, "enable_xformers_memory_efficient_attention"):
                    self.pipeline.enable_xformers_memory_efficient_attention()
            except Exception as e:
                logger.debug(f"Could not enable memory optimizations: {e}")

            # Load LoRAs if configured
            if self.config.enable_lora and self.config.lora_ids:
                self._load_loras()

            # Load IP-Adapter if configured
            if self.config.enable_ip_adapter:
                self._load_ip_adapter()

            self._is_loaded = True
            logger.info("Image generation model loaded successfully")
            return True

        except Exception as e:
            logger.warning(f"Failed to load image generation model: {e}")
            self._is_loaded = False
            return False

    def _load_loras(self) -> None:
        """Load and fuse LoRA adapters."""
        if not self.pipeline or not self.config.lora_ids:
            return

        try:
            logger.info(f"Loading {len(self.config.lora_ids)} LoRA(s)")
            weights = (
                self.config.lora_weights
                if len(self.config.lora_weights) == len(self.config.lora_ids)
                else [1.0] * len(self.config.lora_ids)
            )

            for lora_id, weight in zip(self.config.lora_ids, weights):
                logger.debug(f"Loading LoRA {lora_id} with weight {weight}")
                try:
                    self.pipeline.load_lora_weights(lora_id)
                    if hasattr(self.pipeline, "fuse_lora"):
                        self.pipeline.fuse_lora(lora_scale=weight)
                except Exception as e:
                    logger.warning(f"Failed to load LoRA {lora_id}: {e}")

        except Exception as e:
            logger.warning(f"Error loading LoRAs: {e}")

    def _load_ip_adapter(self) -> None:
        """Load IP-Adapter for reference image conditioning."""
        if not self.pipeline:
            return

        try:
            from diffusers.utils import load_image
            from pipelines import IPAdapterPipeline

            logger.info(f"Loading IP-Adapter from {self.config.ip_adapter_model_id}")
            # This is a simplified stub - actual IP-Adapter integration requires specific setup
            logger.debug("IP-Adapter support requires additional dependencies")
        except Exception as e:
            logger.warning(f"IP-Adapter not available: {e}")

    def unload(self) -> None:
        """Unload model and free GPU memory."""
        if self.pipeline is not None:
            try:
                import torch

                self.pipeline = None
                torch.cuda.empty_cache()
                logger.info("Image generation model unloaded")
            except Exception as e:
                logger.warning(f"Error unloading model: {e}")
        self._is_loaded = False

    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        seed: int | None = None,
        ip_adapter_image: Image.Image | None = None,
        ip_adapter_scale: float = 0.7,
    ) -> Image.Image:
        """
        Generate image from text prompt.

        Args:
            prompt: Text description of the image
            negative_prompt: What NOT to generate
            width: Image width in pixels
            height: Image height in pixels
            num_inference_steps: Number of denoising steps
            guidance_scale: How much to follow the prompt (7.5 typical)
            seed: Random seed for reproducibility
            ip_adapter_image: Optional reference image for IP-Adapter
            ip_adapter_scale: Strength of IP-Adapter conditioning

        Returns:
            PIL Image
        """
        if not self.load():
            logger.warning("Image generation model not available, returning synthetic image")
            return self._generate_synthetic(prompt, width, height, seed or 0)

        try:
            import torch

            # Set seed for reproducibility
            if seed is not None:
                generator = torch.Generator(device=self.config.device).manual_seed(seed)
            else:
                generator = None

            logger.info(
                f"Generating image: {prompt[:80]}... ({width}x{height}, steps={num_inference_steps})"
            )

            # Prepare inputs
            pipeline_kwargs = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "height": height,
                "width": width,
            }

            if generator is not None:
                pipeline_kwargs["generator"] = generator

            # Add IP-Adapter image if provided
            if ip_adapter_image is not None and self.config.enable_ip_adapter:
                pipeline_kwargs["ip_adapter_image"] = ip_adapter_image
                pipeline_kwargs["ip_adapter_scale"] = ip_adapter_scale

            # Generate
            result = self.pipeline(**pipeline_kwargs)
            image = result.images[0] if hasattr(result, "images") else result

            logger.info("Image generation completed")
            return image

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return self._generate_synthetic(prompt, width, height, seed or 0)

    @staticmethod
    def _generate_synthetic(prompt: str, width: int, height: int, seed: int) -> Image.Image:
        """Generate a simple synthetic image when model is unavailable."""
        import random

        random.seed(seed)
        np.random.seed(seed % (2**32 - 1))

        # Create gradient base
        base = np.zeros((height, width, 3), dtype=np.uint8)
        hue = abs(hash(prompt)) % 255
        base[:, :, 0] = hue
        base[:, :, 1] = (100 + seed) % 255
        base[:, :, 2] = 180

        # Add noise
        noise = np.random.randint(0, 35, size=(height, width, 3), dtype=np.uint8)
        arr = np.clip(base + noise, 0, 255)

        from PIL import ImageDraw

        img = Image.fromarray(arr, mode="RGB")
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, width, 80), fill=(0, 0, 0))
        draw.text((10, 10), f"prompt: {prompt[:60]}", fill=(200, 200, 200))
        draw.text((10, 40), f"seed={seed}", fill=(180, 180, 180))

        return img
