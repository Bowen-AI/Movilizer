"""Model integration modules (diffusion, image/video/audio generation, upscaling)."""

from .diffusion import DiffusionConfig, DiffusionGenerator, NativeVideoStubPlugin, VideoPlugin
from .image_gen import ImageGenerator, ImageGenConfig
from .music_gen import MusicGenerator, MusicGenConfig
from .tts_gen import TTSGenerator, TTSGenConfig
from .upscale import UpscaleConfig, VideoUpscaler
from .video_gen import VideoGenerator, VideoGenConfig

__all__ = [
    "DiffusionConfig",
    "DiffusionGenerator",
    "VideoPlugin",
    "NativeVideoStubPlugin",
    "ImageGenConfig",
    "ImageGenerator",
    "VideoGenConfig",
    "VideoGenerator",
    "TTSGenConfig",
    "TTSGenerator",
    "MusicGenConfig",
    "MusicGenerator",
    "UpscaleConfig",
    "VideoUpscaler",
]
