"""Configuration management using Pydantic settings"""

from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Storage paths
    STORAGE_DIR: str = "storage"
    PROJECTS_DIR: str = "storage/projects"
    TEMP_DIR: str = "storage/temp"
    CACHE_DIR: str = "storage/cache"
    OUTPUT_DIR: str = "storage/output"
    FONTS_DIR: str = "storage/fonts"

    # FFmpeg settings
    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"

    # TTS settings
    TTS_CACHE_ENABLED: bool = True
    MAX_CONCURRENT_TTS: int = 2
    TTS_PROXY_ENABLED: bool = False
    TTS_PROXY_URL: Optional[str] = None

    # Export settings
    DEFAULT_VIDEO_CODEC: str = "libx264"
    DEFAULT_AUDIO_CODEC: str = "aac"
    DEFAULT_CRF: int = 23
    DEFAULT_PRESET: str = "medium"

    # Quality presets
    LOSSLESS_CRF: int = 0
    HIGH_CRF: int = 18
    BALANCED_CRF: int = 23

    # Audio mixing
    # Based on proven reference implementation (cl_vid_gen_2.py)
    # TTS boost: +3dB ensures voice-over is clear and audible
    # BGM reduction: -16dB creates 19dB difference favoring speech over background music
    TTS_VOLUME_BOOST: int = 3
    BGM_VOLUME_REDUCTION: int = 16
    FADE_DURATION: float = 3.0

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True

    def create_directories(self):
        """Create necessary directories"""
        for dir_path in [
            self.STORAGE_DIR,
            self.PROJECTS_DIR,
            self.TEMP_DIR,
            self.CACHE_DIR,
            self.OUTPUT_DIR,
            self.FONTS_DIR
        ]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
settings.create_directories()
