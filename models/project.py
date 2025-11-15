"""Project model - Manages project data and persistence"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from uuid import uuid4

from .video import Video
from .timeline import Timeline
from utils.logger import logger
from config import settings


class Project:
    """Manages multi-video project data and persistence"""

    def __init__(self, name: str, video_paths: Optional[List[str]] = None):
        """
        Initialize project with optional video paths

        Args:
            name: Project name
            video_paths: List of video file paths (for multi-video) or None
        """
        self.name = name
        self.videos: List[Video] = []
        self.active_video_id: Optional[str] = None
        self.created_at = datetime.now()
        self.modified_at = datetime.now()
        self.background_music_path: Optional[str] = None
        self.export_quality = "balanced"  # lossless, high, balanced
        self.include_subtitles = True

        # If video paths provided, create Video instances
        if video_paths:
            for idx, video_path in enumerate(video_paths, 1):
                self.add_video(video_path, order=idx)

    @property
    def project_dir(self) -> Path:
        """Get project directory path"""
        return Path(settings.PROJECTS_DIR) / self.name

    @property
    def project_file(self) -> Path:
        """Get project file path"""
        return self.project_dir / "project.json"

    def add_video(self, video_path: str, name: Optional[str] = None, order: Optional[int] = None) -> Video:
        """
        Add a new video to the project

        Args:
            video_path: Path to video file
            name: Optional custom name (defaults to filename)
            order: Optional order position (defaults to end)

        Returns:
            Created Video instance
        """
        if name is None:
            name = Path(video_path).stem

        if order is None:
            order = len(self.videos) + 1

        video = Video.create(name=name, video_path=video_path, order=order)
        self.videos.append(video)

        # Set as active if it's the first video
        if len(self.videos) == 1:
            self.active_video_id = video.id

        logger.info(f"Added video to project: {name} (order: {order})")
        return video

    def remove_video(self, video_id: str) -> bool:
        """
        Remove a video from the project

        Args:
            video_id: ID of video to remove

        Returns:
            True if removed, False if not found
        """
        original_count = len(self.videos)
        self.videos = [v for v in self.videos if v.id != video_id]
        removed = len(self.videos) < original_count

        if removed:
            # Reorder remaining videos
            for idx, video in enumerate(sorted(self.videos, key=lambda v: v.order), 1):
                video.order = idx

            # Update active video if needed
            if self.active_video_id == video_id:
                self.active_video_id = self.videos[0].id if self.videos else None

            logger.info(f"Removed video from project: {video_id}")

        return removed

    def get_video(self, video_id: str) -> Optional[Video]:
        """Get video by ID"""
        for video in self.videos:
            if video.id == video_id:
                return video
        return None

    def get_active_video(self) -> Optional[Video]:
        """Get currently active video"""
        if self.active_video_id:
            return self.get_video(self.active_video_id)
        return None

    def set_active_video(self, video_id: str) -> bool:
        """
        Set the active video for editing

        Args:
            video_id: ID of video to set as active

        Returns:
            True if successful, False if video not found
        """
        if self.get_video(video_id):
            self.active_video_id = video_id
            logger.info(f"Active video set to: {video_id}")
            return True
        return False

    def reorder_videos(self, video_ids_in_order: List[str]) -> bool:
        """
        Reorder videos based on provided ID list

        Args:
            video_ids_in_order: List of video IDs in desired order

        Returns:
            True if successful
        """
        # Validate all IDs exist
        if set(video_ids_in_order) != {v.id for v in self.videos}:
            logger.error("Invalid video IDs provided for reordering")
            return False

        # Create new order mapping
        for new_order, video_id in enumerate(video_ids_in_order, 1):
            video = self.get_video(video_id)
            if video:
                video.order = new_order

        # Re-sort videos list
        self.videos.sort(key=lambda v: v.order)
        logger.info("Videos reordered successfully")
        return True

    def check_video_compatibility(self) -> tuple[bool, List[str]]:
        """
        Check if all videos in project are compatible for combination

        Returns:
            Tuple of (all_compatible: bool, warnings: List[str])
        """
        if len(self.videos) <= 1:
            return True, []

        warnings = []
        reference_video = self.videos[0]

        for idx, video in enumerate(self.videos[1:], 2):
            is_compatible, reason = reference_video.is_compatible_with(video)
            if not is_compatible:
                warnings.append(f"Video {idx} ({video.name}): {reason}")

        return len(warnings) == 0, warnings

    # Backward compatibility properties
    @property
    def video_path(self) -> str:
        """Backward compatibility: Get first video's path"""
        if self.videos:
            return self.videos[0].path
        return ""

    @property
    def timeline(self) -> Optional[Timeline]:
        """Backward compatibility: Get active video's timeline"""
        active_video = self.get_active_video()
        return active_video.timeline if active_video else None

    def save(self) -> bool:
        """Save project to disk"""
        try:
            # Create project directory
            self.project_dir.mkdir(parents=True, exist_ok=True)

            # Update modified time
            self.modified_at = datetime.now()

            # Serialize project data
            project_data = {
                "name": self.name,
                "videos": [video.to_dict() for video in self.videos],
                "active_video_id": self.active_video_id,
                "created_at": self.created_at.isoformat(),
                "modified_at": self.modified_at.isoformat(),
                "background_music_path": self.background_music_path,
                "export_quality": self.export_quality,
                "include_subtitles": self.include_subtitles,
                "version": 2  # Version 2 = multi-video format
            }

            # Write to file
            with open(self.project_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2)

            logger.info(f"Project saved: {self.name} ({len(self.videos)} videos)")
            return True

        except Exception as e:
            logger.error(f"Failed to save project: {e}")
            return False

    @classmethod
    def load(cls, name: str) -> Optional['Project']:
        """Load project from disk with backward compatibility"""
        try:
            project_dir = Path(settings.PROJECTS_DIR) / name
            project_file = project_dir / "project.json"

            if not project_file.exists():
                logger.error(f"Project file not found: {project_file}")
                return None

            # Read project data
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # Check version for backward compatibility
            version = project_data.get("version", 1)

            if version == 1 or "video_path" in project_data:
                # Old format: single video
                logger.info(f"Migrating project '{name}' from v1 (single-video) to v2 (multi-video)")
                project = cls._load_v1_project(project_data)
            else:
                # New format: multi-video
                project = cls._load_v2_project(project_data)

            logger.info(f"Project loaded: {name} ({len(project.videos)} videos)")
            return project

        except Exception as e:
            logger.error(f"Failed to load project: {e}")
            return None

    @classmethod
    def _load_v1_project(cls, data: dict) -> 'Project':
        """Load old single-video project format and migrate to multi-video"""
        project = cls(data["name"])

        # Create single Video from old format
        video_path = data["video_path"]
        video = Video.create(
            name="Main Video",
            video_path=video_path,
            order=1
        )

        # Load timeline into the video
        timeline_data = data["timeline"]
        video.timeline = Timeline.from_dict(timeline_data)
        video.timeline.video_id = video.id

        # Update all segments with video_id
        for segment in video.timeline.segments:
            segment.video_id = video.id

        project.videos = [video]
        project.active_video_id = video.id

        # Load metadata
        project.created_at = datetime.fromisoformat(data["created_at"])
        project.modified_at = datetime.fromisoformat(data["modified_at"])
        project.background_music_path = data.get("background_music_path")
        project.export_quality = data.get("export_quality", "balanced")
        project.include_subtitles = data.get("include_subtitles", True)

        return project

    @classmethod
    def _load_v2_project(cls, data: dict) -> 'Project':
        """Load new multi-video project format"""
        project = cls(data["name"])

        # Load videos
        for video_data in data["videos"]:
            video = Video.from_dict(video_data)
            project.videos.append(video)

        project.active_video_id = data.get("active_video_id")

        # Load metadata
        project.created_at = datetime.fromisoformat(data["created_at"])
        project.modified_at = datetime.fromisoformat(data["modified_at"])
        project.background_music_path = data.get("background_music_path")
        project.export_quality = data.get("export_quality", "balanced")
        project.include_subtitles = data.get("include_subtitles", True)

        return project

    @classmethod
    def list_projects(cls) -> list:
        """List all available projects"""
        projects = []
        projects_dir = Path(settings.PROJECTS_DIR)

        if not projects_dir.exists():
            return projects

        for project_dir in projects_dir.iterdir():
            if project_dir.is_dir():
                project_file = project_dir / "project.json"
                if project_file.exists():
                    try:
                        with open(project_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        # Handle both v1 and v2 formats
                        version = data.get("version", 1)

                        if version == 1 or "video_path" in data:
                            # Old format
                            video_count = 1
                            segments_count = len(data["timeline"]["segments"])
                        else:
                            # New format
                            video_count = len(data["videos"])
                            segments_count = sum(
                                len(v["timeline"]["segments"])
                                for v in data["videos"]
                            )

                        projects.append({
                            "name": data["name"],
                            "video_count": video_count,
                            "created_at": data["created_at"],
                            "modified_at": data["modified_at"],
                            "segments_count": segments_count
                        })
                    except Exception as e:
                        logger.warning(f"Could not read project {project_dir.name}: {e}")

        # Sort by modified date (most recent first)
        projects.sort(key=lambda p: p["modified_at"], reverse=True)
        return projects

    def delete(self) -> bool:
        """Delete project and all associated files"""
        try:
            import shutil

            if self.project_dir.exists():
                shutil.rmtree(self.project_dir)
                logger.info(f"Project deleted: {self.name}")
                return True
            else:
                logger.warning(f"Project directory not found: {self.project_dir}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete project: {e}")
            return False

    def get_stats(self) -> dict:
        """Get project statistics"""
        total_segments = sum(len(v.timeline.segments) for v in self.videos)
        total_video_duration = sum(v.duration or 0 for v in self.videos)

        return {
            "name": self.name,
            "video_count": len(self.videos),
            "total_video_duration": total_video_duration,
            "segments_count": total_segments,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "videos": [v.get_display_info() for v in self.videos]
        }

    def __str__(self) -> str:
        """String representation"""
        return f"Project(name={self.name}, videos={len(self.videos)})"
