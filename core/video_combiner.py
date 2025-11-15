"""
Video Combiner - Combines multiple edited videos into a single output
"""

import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
from utils.logger import logger
from backend.ffmpeg_utils import FFmpegUtils
from models.video import Video


class VideoCombiner:
    """
    Handles combination of multiple processed videos with aspect ratio validation
    Based on the FFmpeg techniques from reference/FFmpeg_Video_Generation_Documentation.md
    """

    @staticmethod
    def check_compatibility(videos: List[Video]) -> Tuple[bool, List[str], dict]:
        """
        Check if videos are compatible for combination

        Args:
            videos: List of Video instances to check

        Returns:
            Tuple of (is_compatible, warnings, common_specs)
        """
        if len(videos) <= 1:
            return True, [], {}

        warnings = []
        reference = videos[0]

        # Check orientation compatibility
        orientations = {v.orientation for v in videos}
        if len(orientations) > 1:
            return (
                False,
                [f"INCOMPATIBLE: Cannot combine videos with different orientations: {orientations}"],
                {}
            )

        # Check aspect ratio similarity (within 5% tolerance)
        aspect_ratios = [v.aspect_ratio for v in videos if v.aspect_ratio]
        if aspect_ratios:
            min_ar = min(aspect_ratios)
            max_ar = max(aspect_ratios)
            diff = abs(max_ar - min_ar)

            if diff > 0.05:  # 5% tolerance
                warnings.append(
                    f"Different aspect ratios detected (range: {min_ar:.3f} to {max_ar:.3f}). "
                    "Videos will be scaled to match, which may cause quality loss or black bars."
                )

        # Determine common specifications
        resolutions = [(v.width, v.height) for v in videos if v.width and v.height]
        fps_values = [v.fps for v in videos if v.fps]
        codecs = {v.codec for v in videos if v.codec}

        # Find target resolution (highest)
        if resolutions:
            target_width = max(r[0] for r in resolutions)
            target_height = max(r[1] for r in resolutions)
        else:
            target_width, target_height = 1920, 1080

        # Find target FPS (highest common)
        target_fps = max(fps_values) if fps_values else 30.0

        # Check if all resolutions match
        if len(set(resolutions)) > 1:
            warnings.append(
                f"Different resolutions detected. Videos will be scaled to {target_width}x{target_height}."
            )

        # Check if all FPS match
        if len(set(fps_values)) > 1:
            warnings.append(
                f"Different frame rates detected. Videos will be converted to {target_fps} FPS."
            )

        # Check if all codecs match
        if len(codecs) > 1:
            warnings.append(
                f"Different codecs detected ({codecs}). Videos will be re-encoded."
            )

        common_specs = {
            'width': target_width,
            'height': target_height,
            'fps': target_fps,
            'orientation': reference.orientation,
            'needs_scaling': len(set(resolutions)) > 1,
            'needs_fps_conversion': len(set(fps_values)) > 1,
            'needs_reencoding': len(codecs) > 1
        }

        return True, warnings, common_specs

    @staticmethod
    def combine_videos_simple(
        video_paths: List[str],
        output_path: str,
        temp_dir: Path
    ) -> bool:
        """
        Combine videos using concat demuxer (fast, requires same specs)

        Args:
            video_paths: List of video file paths to combine
            output_path: Output file path
            temp_dir: Temporary directory for concat file

        Returns:
            True if successful
        """
        try:
            # Create concat file
            concat_file = temp_dir / "concat_list.txt"

            with open(concat_file, 'w') as f:
                for video_path in video_paths:
                    # Escape path for concat file
                    escaped_path = str(Path(video_path).absolute()).replace('\\', '/')
                    f.write(f"file '{escaped_path}'\n")

            logger.info(f"Created concat file with {len(video_paths)} videos")

            # Combine using concat demuxer
            command = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',  # Copy without re-encoding
                '-y',
                output_path
            ]

            logger.info("Combining videos (fast mode - no re-encoding)...")
            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode == 0:
                duration = FFmpegUtils.get_media_duration(output_path)
                size_mb = Path(output_path).stat().st_size / (1024 * 1024)
                logger.info(f"✅ Videos combined successfully! Duration: {duration:.2f}s, Size: {size_mb:.1f}MB")
                return True
            else:
                logger.error(f"❌ Video combination failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Error combining videos: {e}")
            return False

    @staticmethod
    def combine_videos_complex(
        video_paths: List[str],
        output_path: str,
        common_specs: dict,
        quality: str = "balanced"
    ) -> bool:
        """
        Combine videos with scaling/fps conversion (slower, handles different specs)

        Args:
            video_paths: List of video file paths to combine
            output_path: Output file path
            common_specs: Common specifications dictionary
            quality: Export quality (lossless, high, balanced)

        Returns:
            True if successful
        """
        try:
            target_width = common_specs['width']
            target_height = common_specs['height']
            target_fps = common_specs['fps']

            logger.info(f"Combining videos with normalization:")
            logger.info(f"  Target resolution: {target_width}x{target_height}")
            logger.info(f"  Target FPS: {target_fps}")

            # Build filter complex for each input
            filter_parts = []
            for idx in range(len(video_paths)):
                # Scale and set FPS for each input
                filter_parts.append(
                    f"[{idx}:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                    f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black,"
                    f"fps={target_fps},setsar=1[v{idx}]"
                )

                # Handle audio (may not exist in all videos)
                filter_parts.append(f"[{idx}:a]anull[a{idx}]")

            # Concatenate all normalized streams
            video_inputs = ''.join(f"[v{i}]" for i in range(len(video_paths)))
            audio_inputs = ''.join(f"[a{i}]" for i in range(len(video_paths)))

            filter_complex = ';'.join(filter_parts) + ';'
            filter_complex += f"{video_inputs}{audio_inputs}concat=n={len(video_paths)}:v=1:a=1[outv][outa]"

            # Quality settings
            if quality == "lossless":
                crf = "0"
                preset = "slow"
            elif quality == "high":
                crf = "18"
                preset = "slow"
            else:  # balanced
                crf = "23"
                preset = "medium"

            # Build FFmpeg command
            command = ['ffmpeg']

            # Add all input files
            for video_path in video_paths:
                command.extend(['-i', video_path])

            # Add filter complex and output settings
            command.extend([
                '-filter_complex', filter_complex,
                '-map', '[outv]',
                '-map', '[outa]',
                '-c:v', 'libx264',
                '-preset', preset,
                '-crf', crf,
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-y',
                output_path
            ])

            logger.info("Combining videos with scaling/normalization (this may take a while)...")
            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode == 0:
                duration = FFmpegUtils.get_media_duration(output_path)
                size_mb = Path(output_path).stat().st_size / (1024 * 1024)
                logger.info(f"✅ Videos combined successfully! Duration: {duration:.2f}s, Size: {size_mb:.1f}MB")
                return True
            else:
                logger.error(f"❌ Video combination failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Error combining videos: {e}")
            return False

    @classmethod
    def combine_project_videos(
        cls,
        videos: List[Video],
        processed_video_paths: List[str],
        output_path: str,
        temp_dir: Path,
        quality: str = "balanced",
        force_export: bool = False
    ) -> bool:
        """
        Combine multiple processed videos from a project

        Args:
            videos: List of Video model instances (for compatibility checking)
            processed_video_paths: List of processed video file paths (in order)
            output_path: Output file path
            temp_dir: Temporary directory
            quality: Export quality
            force_export: Force export even if videos are incompatible

        Returns:
            True if successful
        """
        # Check compatibility
        is_compatible, warnings, common_specs = cls.check_compatibility(videos)

        if not is_compatible:
            if force_export:
                logger.warning("Videos are not compatible but forcing combination:")
                for warning in warnings:
                    logger.warning(f"  • {warning}")
                # Calculate common specs even for incompatible videos
                if not common_specs:
                    # Build common specs for force export
                    resolutions = [(v.width, v.height) for v in videos if v.width and v.height]
                    fps_values = [v.fps for v in videos if v.fps]

                    if resolutions:
                        target_width = max(r[0] for r in resolutions)
                        target_height = max(r[1] for r in resolutions)
                    else:
                        target_width, target_height = 1920, 1080

                    target_fps = max(fps_values) if fps_values else 30.0

                    common_specs = {
                        'width': target_width,
                        'height': target_height,
                        'fps': target_fps,
                        'orientation': videos[0].orientation if videos else 'horizontal',
                        'needs_scaling': True,
                        'needs_fps_conversion': True,
                        'needs_reencoding': True
                    }
            else:
                logger.error("Videos are not compatible for combination:")
                for warning in warnings:
                    logger.error(f"  • {warning}")
                return False

        # Display warnings
        if warnings:
            logger.warning("Video combination warnings:")
            for warning in warnings:
                logger.warning(f"  • {warning}")

        # Decide combination strategy
        if force_export or common_specs.get('needs_scaling') or common_specs.get('needs_fps_conversion') or common_specs.get('needs_reencoding'):
            # Use complex filter for normalization
            logger.info("Using advanced combination (with normalization)")
            return cls.combine_videos_complex(processed_video_paths, output_path, common_specs, quality)
        else:
            # Use simple concat for speed
            logger.info("Using fast combination (direct concatenation)")
            success = cls.combine_videos_simple(processed_video_paths, output_path, temp_dir)

            # If simple concat fails, fall back to complex
            if not success:
                logger.warning("Fast combination failed, trying advanced method...")
                return cls.combine_videos_complex(processed_video_paths, output_path, common_specs, quality)

            return success
