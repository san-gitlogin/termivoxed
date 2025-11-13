"""Project model - Manages project data and persistence"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .timeline import Timeline
from utils.logger import logger
from config import settings


class Project:
    """Manages project data and persistence"""

    def __init__(self, name: str, video_path: str):
        self.name = name
        self.video_path = video_path
        self.timeline = Timeline(video_path)
        self.created_at = datetime.now()
        self.modified_at = datetime.now()
        self.background_music_path: Optional[str] = None
        self.export_quality = "balanced"  # lossless, high, balanced
        self.include_subtitles = True

    @property
    def project_dir(self) -> Path:
        """Get project directory path"""
        return Path(settings.PROJECTS_DIR) / self.name

    @property
    def project_file(self) -> Path:
        """Get project file path"""
        return self.project_dir / "project.json"

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
                "video_path": self.video_path,
                "timeline": self.timeline.to_dict(),
                "created_at": self.created_at.isoformat(),
                "modified_at": self.modified_at.isoformat(),
                "background_music_path": self.background_music_path,
                "export_quality": self.export_quality,
                "include_subtitles": self.include_subtitles
            }

            # Write to file
            with open(self.project_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2)

            logger.info(f"Project saved: {self.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to save project: {e}")
            return False

    @classmethod
    def load(cls, name: str) -> Optional['Project']:
        """Load project from disk"""
        try:
            project_dir = Path(settings.PROJECTS_DIR) / name
            project_file = project_dir / "project.json"

            if not project_file.exists():
                logger.error(f"Project file not found: {project_file}")
                return None

            # Read project data
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # Create project instance
            project = cls(project_data["name"], project_data["video_path"])

            # Load timeline
            project.timeline = Timeline.from_dict(project_data["timeline"])

            # Load metadata
            project.created_at = datetime.fromisoformat(project_data["created_at"])
            project.modified_at = datetime.fromisoformat(project_data["modified_at"])
            project.background_music_path = project_data.get("background_music_path")
            project.export_quality = project_data.get("export_quality", "balanced")
            project.include_subtitles = project_data.get("include_subtitles", True)

            logger.info(f"Project loaded: {name}")
            return project

        except Exception as e:
            logger.error(f"Failed to load project: {e}")
            return None

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

                        projects.append({
                            "name": data["name"],
                            "video_path": data["video_path"],
                            "created_at": data["created_at"],
                            "modified_at": data["modified_at"],
                            "segments_count": len(data["timeline"]["segments"])
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
        return {
            "name": self.name,
            "video_duration": self.timeline.video_duration,
            "segments_count": len(self.timeline.segments),
            "total_segment_duration": self.timeline.get_total_duration(),
            "coverage_percentage": self.timeline.get_coverage_percentage(),
            "video_info": self.timeline.video_info,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat()
        }

    def __str__(self) -> str:
        """String representation"""
        return f"Project(name={self.name}, segments={len(self.timeline.segments)})"
