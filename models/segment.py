"""Segment model - Represents a timeline segment with voice-over"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from uuid import uuid4


@dataclass
class Segment:
    """Timeline segment with voice-over and subtitle configuration"""

    # Identity
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""

    # Timing
    start_time: float = 0.0  # seconds
    end_time: float = 0.0    # seconds

    # Content
    text: str = ""
    language: str = "en"

    # Voice settings
    voice_id: str = ""
    rate: str = "+0%"
    volume: str = "+0%"
    pitch: str = "+0Hz"

    # Generated files
    audio_path: Optional[str] = None
    subtitle_path: Optional[str] = None

    # Subtitle styling
    subtitle_enabled: bool = True
    subtitle_font: str = "Roboto"
    subtitle_size: int = 20
    subtitle_color: str = "&H00FFFFFF"  # White (primary color)
    subtitle_position: int = 30  # pixels from bottom

    # Subtitle border/outline styling
    subtitle_border_enabled: bool = True
    subtitle_border_style: int = 1  # 1=outline+box, 3=opaque box
    subtitle_outline_width: float = 2.0  # Border/outline thickness
    subtitle_outline_color: str = "&H00000000"  # Black outline
    subtitle_shadow: float = 0.0  # Shadow distance (0=no shadow)
    subtitle_shadow_color: str = "&H80000000"  # Semi-transparent black shadow

    # Sync settings
    sync_mode: str = "auto"  # auto, manual

    @property
    def duration(self) -> float:
        """Get segment duration in seconds"""
        return self.end_time - self.start_time

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate segment

        Returns:
            (is_valid, error_message)
        """
        if self.end_time <= self.start_time:
            return False, "End time must be greater than start time"

        if not self.text.strip():
            return False, "Text cannot be empty"

        if self.start_time < 0:
            return False, "Start time cannot be negative"

        if not self.language:
            return False, "Language must be specified"

        return True, None

    def to_dict(self) -> dict:
        """Convert segment to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Segment':
        """Create segment from dictionary"""
        return cls(**data)

    def __str__(self) -> str:
        """String representation"""
        return f"Segment({self.name}: {self.start_time:.2f}s - {self.end_time:.2f}s, '{self.text[:30]}...')"
