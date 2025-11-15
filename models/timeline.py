"""Timeline model - Manages video timeline with segments"""

import os
from typing import List, Optional
from pathlib import Path

from .segment import Segment
from backend.ffmpeg_utils import FFmpegUtils
from utils.logger import logger


class Timeline:
    """Manages video timeline with segments"""

    def __init__(self, video_path: str, video_id: Optional[str] = None):
        self.video_path = video_path
        self.video_id = video_id  # ID of the video this timeline belongs to
        self.video_duration = self._get_video_duration()
        self.video_info = self._get_video_info()
        self.segments: List[Segment] = []

    def _get_video_duration(self) -> float:
        """Get video duration using FFmpeg"""
        from utils.logger import logger

        duration = FFmpegUtils.get_media_duration(self.video_path)
        if duration is None:
            logger.error(f"Could not get duration for video: {self.video_path}")
            logger.error("Check if FFmpeg is installed and video file is accessible")
            raise ValueError(f"Could not get duration for video: {self.video_path}")
        return duration

    def _get_video_info(self) -> dict:
        """Get video information"""
        from utils.logger import logger

        info = FFmpegUtils.get_video_info(self.video_path)
        if info is None:
            logger.error(f"Could not get video info for: {self.video_path}")
            logger.error("FFmpegUtils.get_video_info() returned None")
            return {
                'width': None,  # Changed from 0 to None so checks work properly
                'height': None,
                'fps': None,
                'codec': 'unknown'
            }

        logger.debug(f"Video info retrieved: {info}")
        return info

    def add_segment(
        self,
        start: float,
        end: float,
        text: str,
        voice: str,
        language: str = "en",
        name: Optional[str] = None
    ) -> Segment:
        """Add new segment to timeline"""

        segment = Segment(
            name=name or f"Segment {len(self.segments) + 1}",
            start_time=start,
            end_time=end,
            text=text,
            voice_id=voice,
            language=language,
            video_id=self.video_id  # Associate segment with video
        )

        # Validate segment
        is_valid, error = segment.validate()
        if not is_valid:
            raise ValueError(f"Invalid segment: {error}")

        # Check if end time exceeds video duration
        if end > self.video_duration:
            raise ValueError(
                f"Segment end ({end}s) exceeds video duration ({self.video_duration}s)"
            )

        self.segments.append(segment)
        self.segments.sort(key=lambda s: s.start_time)

        duration = end - start
        logger.info(
            f"Added segment: {segment.name} | "
            f"Start: {start:.2f}s | End: {end:.2f}s | Duration: {duration:.2f}s | "
            f"ID: {segment.id[:8]}"
        )
        return segment

    def remove_segment(self, segment_id: str) -> bool:
        """Remove segment from timeline"""
        original_count = len(self.segments)
        self.segments = [s for s in self.segments if s.id != segment_id]
        removed = len(self.segments) < original_count

        if removed:
            logger.info(f"Removed segment: {segment_id}")

        return removed

    def update_segment(self, segment_id: str, **kwargs) -> bool:
        """Update segment properties"""
        segment = self.get_segment_by_id(segment_id)
        if not segment:
            return False

        # Update properties
        for key, value in kwargs.items():
            if hasattr(segment, key):
                setattr(segment, key, value)

        # Validate after update
        is_valid, error = segment.validate()
        if not is_valid:
            logger.error(f"Segment validation failed after update: {error}")
            return False

        # Re-sort if timing changed
        if 'start_time' in kwargs:
            self.segments.sort(key=lambda s: s.start_time)

        logger.info(f"Updated segment: {segment_id}")
        return True

    def get_segment_by_id(self, segment_id: str) -> Optional[Segment]:
        """Get segment by ID"""
        for segment in self.segments:
            if segment.id == segment_id:
                return segment
        return None

    def get_segment_at_time(self, timestamp: float) -> Optional[Segment]:
        """Find segment at given timestamp"""
        for segment in self.segments:
            if segment.start_time <= timestamp <= segment.end_time:
                return segment
        return None

    def check_overlaps(self) -> List[tuple[Segment, Segment]]:
        """Check for overlapping segments"""
        overlaps = []

        for i, seg1 in enumerate(self.segments):
            for seg2 in self.segments[i+1:]:
                # Check if segments overlap
                if not (seg1.end_time <= seg2.start_time or seg2.end_time <= seg1.start_time):
                    overlaps.append((seg1, seg2))

        return overlaps

    def validate_timeline(self) -> List[str]:
        """Validate entire timeline and return list of errors"""
        errors = []

        # Check all segments are valid
        for seg in self.segments:
            is_valid, error = seg.validate()
            if not is_valid:
                errors.append(f"Segment {seg.name}: {error}")

        # Check for overlaps
        overlaps = self.check_overlaps()
        if overlaps:
            for seg1, seg2 in overlaps:
                errors.append(f"Segments '{seg1.name}' and '{seg2.name}' overlap")

        # Check audio files exist for segments that should have them
        for seg in self.segments:
            if seg.audio_path and not os.path.exists(seg.audio_path):
                errors.append(f"Audio missing for segment '{seg.name}'")

        return errors

    def get_total_duration(self) -> float:
        """Get total duration of all segments"""
        if not self.segments:
            return 0.0
        return sum(seg.duration for seg in self.segments)

    def get_coverage_percentage(self) -> float:
        """Get percentage of video covered by segments"""
        if self.video_duration == 0:
            return 0.0
        return (self.get_total_duration() / self.video_duration) * 100

    def to_dict(self) -> dict:
        """Serialize timeline to dictionary"""
        return {
            "video_path": self.video_path,
            "video_id": self.video_id,
            "video_duration": self.video_duration,
            "video_info": self.video_info,
            "segments": [seg.to_dict() for seg in self.segments]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Timeline':
        """Deserialize timeline from dictionary"""
        video_id = data.get("video_id")
        timeline = cls(data["video_path"], video_id=video_id)
        timeline.video_duration = data["video_duration"]
        timeline.video_info = data.get("video_info", timeline.video_info)

        for seg_data in data["segments"]:
            segment = Segment.from_dict(seg_data)
            timeline.segments.append(segment)

        return timeline

    def __len__(self) -> int:
        """Get number of segments"""
        return len(self.segments)

    def __str__(self) -> str:
        """String representation"""
        return (
            f"Timeline(video={Path(self.video_path).name}, "
            f"duration={self.video_duration:.2f}s, "
            f"segments={len(self.segments)})"
        )
