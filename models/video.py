"""
Video Model - Represents a single video in a multi-video project
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict
from uuid import uuid4
from pathlib import Path

from models.timeline import Timeline


@dataclass
class Video:
    """
    Represents a single video with its own timeline and segments.
    Part of a multi-video project architecture.
    """

    id: str
    name: str
    path: str
    timeline: Timeline
    order: int
    created_at: datetime = field(default_factory=datetime.now)

    # Video metadata (cached from timeline.video_info)
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    codec: Optional[str] = None
    aspect_ratio: Optional[float] = None  # width/height
    orientation: Optional[str] = None  # 'horizontal', 'vertical', or 'square'

    def __post_init__(self):
        """Initialize video metadata from timeline after creation"""
        from utils.logger import logger

        if self.timeline is not None:
            self.duration = self.timeline.video_duration
            logger.debug(f"Video.__post_init__ - Set duration: {self.duration}")

            if self.timeline.video_info is not None:
                self.width = self.timeline.video_info.get('width')
                self.height = self.timeline.video_info.get('height')
                self.fps = self.timeline.video_info.get('fps')
                self.codec = self.timeline.video_info.get('codec')

                logger.debug(f"Video.__post_init__ - Set dimensions: {self.width}x{self.height}")

                # Calculate aspect ratio and orientation
                if self.width and self.height:
                    self.aspect_ratio = round(self.width / self.height, 3)

                    # Determine orientation
                    if self.aspect_ratio > 1.1:
                        self.orientation = 'horizontal'  # Landscape
                    elif self.aspect_ratio < 0.9:
                        self.orientation = 'vertical'  # Portrait
                    else:
                        self.orientation = 'square'

                    logger.debug(f"Video.__post_init__ - Calculated orientation: {self.orientation} (AR: {self.aspect_ratio})")
                else:
                    logger.warning(f"Video {self.name}: Could not determine dimensions - width={self.width}, height={self.height}")
            else:
                logger.warning(f"Video {self.name}: No video_info available from timeline")
        else:
            logger.warning(f"Video {self.name}: No timeline available")

    @classmethod
    def create(cls, name: str, video_path: str, order: int = 1) -> 'Video':
        """
        Factory method to create a new Video instance

        Args:
            name: User-friendly name for the video
            video_path: Absolute path to the video file
            order: Order in the project (for export sequencing)

        Returns:
            Video instance with initialized timeline
        """
        from utils.logger import logger

        video_id = str(uuid4())

        try:
            timeline = Timeline(video_path, video_id=video_id)

            # Log video metadata for debugging
            logger.info(f"Video created: {name}")
            logger.debug(f"  Duration: {timeline.video_duration}")
            logger.debug(f"  Video info: {timeline.video_info}")

        except Exception as e:
            logger.error(f"Error creating timeline for {name}: {e}")
            raise

        return cls(
            id=video_id,
            name=name,
            path=video_path,
            timeline=timeline,
            order=order
        )

    def get_display_info(self) -> Dict:
        """Get formatted display information for UI"""
        duration_str = "N/A"
        if self.duration:
            minutes = int(self.duration // 60)
            seconds = int(self.duration % 60)
            duration_str = f"{minutes:02d}:{seconds:02d}"

        resolution_str = "N/A"
        if self.width and self.height:
            resolution_str = f"{self.width}x{self.height}"

        orientation_icon = {
            'horizontal': '🖥',
            'vertical': '📱',
            'square': '⬜'
        }.get(self.orientation, '❓')

        return {
            'name': self.name,
            'duration': duration_str,
            'resolution': resolution_str,
            'orientation': self.orientation or 'unknown',
            'orientation_icon': orientation_icon,
            'aspect_ratio': self.aspect_ratio,
            'segments': len(self.timeline.segments),
            'codec': self.codec or 'unknown'
        }

    def is_compatible_with(self, other: 'Video') -> tuple[bool, str]:
        """
        Check if this video can be combined with another video

        Args:
            other: Another Video instance to check compatibility with

        Returns:
            Tuple of (is_compatible: bool, reason: str)
        """
        # Check if orientation matches
        if self.orientation != other.orientation:
            return (
                False,
                f"Incompatible orientations: '{self.orientation}' vs '{other.orientation}'. "
                f"Cannot combine {self.orientation} video with {other.orientation} video."
            )

        # Check if aspect ratios are similar (within 5% tolerance)
        if self.aspect_ratio and other.aspect_ratio:
            aspect_diff = abs(self.aspect_ratio - other.aspect_ratio)
            aspect_tolerance = 0.05  # 5% tolerance

            if aspect_diff > aspect_tolerance:
                return (
                    False,
                    f"Different aspect ratios: {self.aspect_ratio:.3f} vs {other.aspect_ratio:.3f}. "
                    f"Videos will have quality loss or black bars when combined."
                )

        # Videos are compatible
        return (True, "Videos are compatible for combination")

    def validate_path(self) -> bool:
        """Check if video file still exists at the specified path"""
        return Path(self.path).exists()

    def to_dict(self) -> dict:
        """Serialize Video to dictionary for JSON storage"""
        return {
            'id': self.id,
            'name': self.name,
            'path': self.path,
            'timeline': self.timeline.to_dict(),
            'order': self.order,
            'created_at': self.created_at.isoformat(),
            'duration': self.duration,
            'width': self.width,
            'height': self.height,
            'fps': self.fps,
            'codec': self.codec,
            'aspect_ratio': self.aspect_ratio,
            'orientation': self.orientation
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Video':
        """Deserialize Video from dictionary"""
        timeline = Timeline.from_dict(data['timeline'])

        return cls(
            id=data['id'],
            name=data['name'],
            path=data['path'],
            timeline=timeline,
            order=data['order'],
            created_at=datetime.fromisoformat(data['created_at']),
            duration=data.get('duration'),
            width=data.get('width'),
            height=data.get('height'),
            fps=data.get('fps'),
            codec=data.get('codec'),
            aspect_ratio=data.get('aspect_ratio'),
            orientation=data.get('orientation')
        )

    def __repr__(self) -> str:
        return f"Video(name='{self.name}', path='{self.path}', order={self.order}, segments={len(self.timeline.segments)})"
