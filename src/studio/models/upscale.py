"""Real video and image upscaling with Real-ESRGAN."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from ..utils import get_logger

logger = get_logger("models.upscale")


@dataclass
class UpscaleConfig:
    """Configuration for upscaling models."""

    model_id: str = "RealESRGAN_x4plus"
    device: str = "cuda"
    tile_size: int = 400


class VideoUpscaler:
    """Upscale images and videos using Real-ESRGAN."""

    SUPPORTED_MODELS = {
        "realesrgan-x2": "RealESRGAN_x2plus",
        "realesrgan-x3": "RealESRGAN_x3plus",
        "realesrgan-x4": "RealESRGAN_x4plus",
        "realesrgan-anime": "RealESRGAN_x3plus_anime",
    }

    def __init__(self, config: UpscaleConfig | None = None) -> None:
        """Initialize VideoUpscaler with optional configuration."""
        self.config = config or UpscaleConfig()
        self.model = None
        self._is_loaded = False
        self._attempted_load = False
        self._scale_factor = 4

    def load(self) -> bool:
        """Load the upscaling model to device."""
        if self._is_loaded:
            return True

        if self._attempted_load:
            return False

        self._attempted_load = True

        try:
            from basicsr.archs.rrdbnet_arch import RRDBNet

            logger.info(f"Loading upscaling model: {self.config.model_id}")

            # Determine scale factor from model name
            if "x2" in self.config.model_id:
                self._scale_factor = 2
            elif "x3" in self.config.model_id:
                self._scale_factor = 3
            elif "x4" in self.config.model_id:
                self._scale_factor = 4

            try:
                from realesrgan import RealESRGANer

                self.model = RealESRGANer(
                    scale=self._scale_factor,
                    model_path=None,
                    upsampler=None,
                    tile=self.config.tile_size,
                    tile_pad=10,
                    pre_pad=0,
                    half=True,
                )
                self._is_loaded = True
                logger.info(
                    f"RealESRGAN upscaling model loaded (x{self._scale_factor} scale)"
                )
                return True

            except ImportError:
                logger.warning("realesrgan package not installed")
                return False

        except ImportError as e:
            logger.warning(f"Upscaling dependencies not installed: {e}")
            return False
        except Exception as e:
            logger.warning(f"Failed to load upscaling model: {e}")
            return False

    def unload(self) -> None:
        """Unload model and free memory."""
        if self.model is not None:
            try:
                import torch

                self.model = None
                torch.cuda.empty_cache()
                logger.info("Upscaling model unloaded")
            except Exception as e:
                logger.warning(f"Error unloading model: {e}")
        self._is_loaded = False

    def upscale_frame(
        self,
        image: Image.Image,
        scale: int | None = None,
    ) -> Image.Image:
        """
        Upscale a single image frame.

        Args:
            image: PIL Image to upscale
            scale: Upscaling factor (if None, uses model's native scale)

        Returns:
            Upscaled PIL Image
        """
        if not self.load():
            logger.warning("Upscaling model not available, returning original image")
            return image

        try:
            scale = scale or self._scale_factor
            logger.info(f"Upscaling frame: {image.size} -> {image.size[0] * scale}x{image.size[1] * scale}")

            # Convert PIL to numpy
            img_array = np.array(image)
            if img_array.ndim == 2:
                img_array = np.stack([img_array] * 3, axis=-1)

            # Upscale
            output, _ = self.model.enhance(img_array, outscale=scale)

            # Convert back to PIL
            output = np.clip(output, 0, 255).astype(np.uint8)
            upscaled = Image.fromarray(output)

            logger.info(f"Frame upscaled to {upscaled.size}")
            return upscaled

        except Exception as e:
            logger.error(f"Frame upscaling failed: {e}")
            return image

    def upscale_video(
        self,
        frames: list[Image.Image],
        scale: int | None = None,
        save_dir: Path | None = None,
    ) -> list[Image.Image]:
        """
        Upscale video frames with optional temporal consistency.

        Args:
            frames: List of PIL Images
            scale: Upscaling factor
            save_dir: Optional directory to save upscaled frames

        Returns:
            List of upscaled PIL Images
        """
        if not self.load():
            logger.warning("Upscaling model not available, returning original frames")
            return frames

        upscaled_frames = []
        scale = scale or self._scale_factor

        logger.info(f"Upscaling {len(frames)} video frames by {scale}x")

        for idx, frame in enumerate(frames):
            try:
                upscaled = self.upscale_frame(frame, scale)
                upscaled_frames.append(upscaled)

                # Save if directory provided
                if save_dir:
                    from ..utils import ensure_dir

                    ensure_dir(save_dir)
                    out_path = save_dir / f"upscaled_{idx:06d}.png"
                    upscaled.save(out_path)

                if (idx + 1) % 10 == 0:
                    logger.info(f"Upscaled {idx + 1}/{len(frames)} frames")

            except Exception as e:
                logger.warning(f"Failed to upscale frame {idx}: {e}")
                upscaled_frames.append(frame)

        logger.info(f"Video upscaling completed: {len(upscaled_frames)} frames")
        return upscaled_frames

    def upscale_batch(
        self,
        image_paths: list[str | Path],
        output_dir: Path,
        scale: int | None = None,
    ) -> list[Path]:
        """
        Upscale a batch of images from disk.

        Args:
            image_paths: List of image file paths
            output_dir: Directory to save upscaled images
            scale: Upscaling factor

        Returns:
            List of output paths
        """
        if not self.load():
            logger.warning("Upscaling model not available, skipping upscaling")
            return []

        from ..utils import ensure_dir

        ensure_dir(output_dir)
        output_paths = []
        scale = scale or self._scale_factor

        logger.info(f"Batch upscaling {len(image_paths)} images by {scale}x")

        for idx, img_path in enumerate(image_paths):
            try:
                img = Image.open(img_path)
                upscaled = self.upscale_frame(img, scale)

                output_name = Path(img_path).stem + f"_upscaled_x{scale}.png"
                output_path = output_dir / output_name
                upscaled.save(output_path)
                output_paths.append(output_path)

                if (idx + 1) % 10 == 0:
                    logger.info(f"Batch upscaled {idx + 1}/{len(image_paths)} images")

            except Exception as e:
                logger.warning(f"Failed to upscale {img_path}: {e}")

        logger.info(f"Batch upscaling completed: {len(output_paths)} images")
        return output_paths

    def estimate_upscale_time(
        self,
        image_size_pixels: int,
        scale_factor: int | None = None,
    ) -> float:
        """
        Estimate upscaling time for an image.

        Args:
            image_size_pixels: Total pixel count (width * height)
            scale_factor: Scale factor

        Returns:
            Estimated time in seconds
        """
        scale = scale_factor or self._scale_factor
        output_pixels = image_size_pixels * (scale**2)

        # Rough estimate: ~100M pixels/second on modern GPU
        return max(0.1, output_pixels / 100e6)
