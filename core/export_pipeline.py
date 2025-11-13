"""Export Pipeline - Orchestrates video export using proven patterns"""

import asyncio
import os
from pathlib import Path
from typing import Optional, Callable, List

from models import Project
from backend.tts_service import TTSService
from backend.ffmpeg_utils import FFmpegUtils
from backend.subtitle_utils import SubtitleUtils
from utils.logger import logger
from utils.font_manager import FontManager
from config import settings


class ExportPipeline:
    """
    Orchestrates video export using proven FFmpeg patterns
    """

    def __init__(self, project: Project):
        self.project = project
        self.tts_service = TTSService()
        self.temp_dir = Path(settings.TEMP_DIR)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def export(
        self,
        output_path: str,
        quality: str = "balanced",
        include_subtitles: bool = True,
        background_music_path: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> bool:
        """
        Export final video with voice-overs and subtitles

        Process:
        1. Generate all TTS audio (if not cached)
        2. Process each segment
        3. Combine segments
        4. Add background music (optional)

        Args:
            output_path: Path to save the final video
            quality: Quality preset (lossless, high, balanced)
            include_subtitles: Whether to burn subtitles into video
            background_music_path: Optional path to background music file
            progress_callback: Callback function(message: str, progress: int)

        Returns:
            True if export successful, False otherwise
        """

        try:
            logger.info(f"Starting export: {output_path}")

            # Step 0: Ensure all required fonts are available
            if include_subtitles:
                if progress_callback:
                    progress_callback("Checking font availability...", 0)
                self._ensure_fonts_available()

            # Step 1: Generate all TTS audio
            if progress_callback:
                progress_callback("Generating audio for segments...", 5)

            await self._generate_all_audio(progress_callback)

            # Step 2: Process each segment
            if progress_callback:
                progress_callback("Processing video segments...", 30)

            segment_videos = await self._process_segments(
                include_subtitles,
                quality,
                progress_callback
            )

            if not segment_videos:
                logger.error("No segments processed")
                return False

            # Step 3: Combine segments
            if progress_callback:
                progress_callback("Combining video segments...", 70)

            combined_path = self.temp_dir / f"combined_{self.project.name}.mp4"
            success = FFmpegUtils.concatenate_videos(segment_videos, str(combined_path))

            if not success:
                logger.error("Failed to concatenate segments")
                return False

            # Step 4: Add background music (optional)
            if background_music_path and os.path.exists(background_music_path):
                if progress_callback:
                    progress_callback("Adding background music...", 90)

                success = FFmpegUtils.add_background_music(
                    str(combined_path),
                    background_music_path,
                    output_path
                )

                if not success:
                    return False
            else:
                # Just copy combined to output
                import shutil
                shutil.copy(combined_path, output_path)

            if progress_callback:
                progress_callback("Export complete!", 100)

            # Cleanup temp files
            self._cleanup_temp_files(segment_videos, combined_path)

            logger.info(f"Export completed: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Export failed: {e}")
            if progress_callback:
                progress_callback(f"Export failed: {e}", 0)
            return False

    async def _generate_all_audio(self, progress_callback: Optional[Callable]):
        """Generate TTS audio for all segments"""
        total = len(self.project.timeline.segments)

        for i, segment in enumerate(self.project.timeline.segments):
            # Skip if already generated
            if segment.audio_path and os.path.exists(segment.audio_path):
                logger.info(f"Using cached audio for segment: {segment.name}")
                continue

            logger.info(f"Generating audio for segment: {segment.name}")

            try:
                # Generate audio using proven TTS service
                audio_path, subtitle_path = await self.tts_service.generate_audio(
                    text=segment.text,
                    language=segment.language,
                    voice=segment.voice_id,
                    project_name=self.project.name,
                    segment_name=segment.name.replace(" ", "_"),
                    rate=segment.rate,
                    volume=segment.volume,
                    pitch=segment.pitch
                )

                segment.audio_path = audio_path
                segment.subtitle_path = subtitle_path

                logger.info(f"Generated audio: {audio_path}")

            except Exception as e:
                logger.error(f"Failed to generate audio for segment {segment.name}: {e}")
                raise

            if progress_callback:
                progress = int(30 * (i + 1) / total)
                progress_callback(f"Generated audio {i+1}/{total}", progress)

    async def _process_segments(
        self,
        include_subtitles: bool,
        quality: str,
        progress_callback: Optional[Callable]
    ) -> List[str]:
        """
        Process video with voice-over segments while preserving full video

        Strategy:
        1. Split video into parts (before segment, segment, after segment, etc.)
        2. Process only segment parts with audio/subtitles
        3. Keep other parts untouched
        4. Concatenate all parts to create full output
        """
        # Get video duration
        video_duration = FFmpegUtils.get_media_duration(self.project.video_path)
        if not video_duration:
            logger.error("Could not get video duration")
            return []

        # Validate audio lengths and get user confirmation if needed
        await self._validate_audio_lengths(video_duration)

        # Sort segments by start time
        sorted_segments = sorted(self.project.timeline.segments, key=lambda s: s.start_time)

        all_parts = []
        current_time = 0.0
        total = len(sorted_segments)

        # Process each segment and gaps between them
        for i, segment in enumerate(sorted_segments):
            # Extract part BEFORE segment (if any gap exists)
            if current_time < segment.start_time:
                logger.info(f"Extracting pre-segment part: {current_time}s - {segment.start_time}s")
                part_path = self.temp_dir / f"part_before_{i}.mp4"
                success = FFmpegUtils.extract_video_segment(
                    self.project.video_path,
                    current_time,
                    segment.start_time,
                    str(part_path),
                    re_encode=True  # Re-encode for concatenation compatibility
                )
                if success:
                    all_parts.append(str(part_path))

            # Process the SEGMENT with audio and subtitles
            logger.info(f"Processing segment: {segment.name}")

            try:
                # Extract video segment
                # Note: We don't re-encode here because it will be processed with audio/subtitles
                segment_video_path = self.temp_dir / f"segment_{i}_video.mp4"
                success = FFmpegUtils.extract_video_segment(
                    self.project.video_path,
                    segment.start_time,
                    segment.end_time,
                    str(segment_video_path),
                    re_encode=False  # Will be re-encoded during process_segment_video
                )

                if not success:
                    logger.error(f"Failed to extract segment: {segment.name}")
                    continue

                # Prepare subtitle file if needed
                subtitle_path = None
                if include_subtitles and segment.subtitle_enabled and segment.subtitle_path:
                    ass_path = segment.subtitle_path.replace('.srt', '.ass')
                    style_options = self._get_subtitle_style(segment)
                    success = SubtitleUtils.create_custom_ass_style(
                        segment.subtitle_path,
                        ass_path,
                        style_options
                    )
                    if success:
                        subtitle_path = ass_path
                    else:
                        logger.warning(f"Failed to style subtitles for segment: {segment.name}")

                # Process segment with audio and subtitles
                processed_video_path = self.temp_dir / f"segment_{i}_processed.mp4"

                # Calculate segment duration
                segment_duration = segment.end_time - segment.start_time

                success = FFmpegUtils.process_segment_video(
                    str(segment_video_path),
                    segment.audio_path,
                    subtitle_path,
                    str(processed_video_path),
                    quality,
                    segment_duration  # Pass expected duration
                )

                if success:
                    all_parts.append(str(processed_video_path))
                    logger.info(f"Processed segment: {segment.name}")
                else:
                    logger.error(f"Failed to process segment: {segment.name}")

            except Exception as e:
                logger.error(f"Error processing segment {segment.name}: {e}")

            # Update current time
            current_time = segment.end_time

            if progress_callback:
                progress = 30 + int(40 * (i + 1) / total)
                progress_callback(f"Processed segment {i+1}/{total}", progress)

        # Extract part AFTER last segment (if any remaining video)
        if current_time < video_duration:
            logger.info(f"Extracting post-segment part: {current_time}s - {video_duration}s")
            part_path = self.temp_dir / f"part_after_last.mp4"
            success = FFmpegUtils.extract_video_segment(
                self.project.video_path,
                current_time,
                video_duration,
                str(part_path),
                re_encode=True  # Re-encode for concatenation compatibility
            )
            if success:
                all_parts.append(str(part_path))

        return all_parts

    async def _validate_audio_lengths(self, video_duration: float):
        """
        Validate that audio lengths are appropriate for their segments
        Automatically extend segments when possible to fit audio
        """
        sorted_segments = sorted(self.project.timeline.segments, key=lambda s: s.start_time)

        for i, segment in enumerate(sorted_segments):
            if not segment.audio_path or not os.path.exists(segment.audio_path):
                continue

            audio_duration = FFmpegUtils.get_media_duration(segment.audio_path)
            if not audio_duration:
                continue

            segment_duration = segment.end_time - segment.start_time

            # Check if audio is significantly longer than segment
            if audio_duration > segment_duration + 1.0:  # 1 second tolerance
                # Calculate how much we need to extend
                needed_duration = audio_duration
                new_end_time = segment.start_time + needed_duration

                # Check if we can extend
                can_extend = False
                max_allowed_end = video_duration

                # If not the last segment, check gap to next segment
                if i < len(sorted_segments) - 1:
                    next_segment = sorted_segments[i + 1]
                    max_allowed_end = next_segment.start_time

                # Check if extension fits
                if new_end_time <= max_allowed_end:
                    can_extend = True

                if can_extend:
                    # EXTEND THE SEGMENT AUTOMATICALLY
                    old_end = segment.end_time
                    segment.end_time = new_end_time

                    logger.warning(
                        f"Audio length mismatch in segment '{segment.name}': "
                        f"Audio={audio_duration:.1f}s, Original Segment={segment_duration:.1f}s"
                    )
                    logger.info(
                        f"✓ Auto-extended segment '{segment.name}' from "
                        f"{old_end:.1f}s to {new_end_time:.1f}s to fit audio"
                    )

                    # Save the project with updated segment
                    self.project.save()
                else:
                    # Cannot extend - audio will be truncated
                    logger.warning(
                        f"Audio length mismatch in segment '{segment.name}': "
                        f"Audio={audio_duration:.1f}s, Segment={segment_duration:.1f}s"
                    )
                    logger.warning(
                        f"⚠ Cannot extend segment - would overlap with next segment or exceed video. "
                        f"Audio will be TRUNCATED to {segment_duration:.1f}s"
                    )
                    logger.info(
                        f"  Tip: Shorten the text for segment '{segment.name}' or adjust segment times"
                    )

    def _ensure_fonts_available(self):
        """
        Ensure all fonts used in segments are available on the system
        Downloads and installs fonts from Google Fonts if needed
        """
        # Collect unique fonts used in segments
        required_fonts = set()
        for segment in self.project.timeline.segments:
            if segment.subtitle_enabled and segment.subtitle_font:
                required_fonts.add(segment.subtitle_font)

        if not required_fonts:
            logger.info("No custom fonts required for subtitles")
            return

        logger.info(f"Checking availability of {len(required_fonts)} font(s)...")

        # Ensure each font is available
        for font_name in required_fonts:
            try:
                FontManager.ensure_font_available(font_name)
            except Exception as e:
                logger.warning(f"Could not ensure font '{font_name}' is available: {e}")
                logger.warning(f"Video will use system default font instead of '{font_name}'")

    def _get_subtitle_style(self, segment) -> dict:
        """Get subtitle style options for segment"""
        # Start with default style for language
        style = SubtitleUtils.get_default_style_for_language(segment.language)

        # Override with segment-specific settings
        style['fontname'] = segment.subtitle_font
        style['fontsize'] = str(segment.subtitle_size)
        style['primarycolour'] = segment.subtitle_color
        style['marginv'] = str(segment.subtitle_position)

        # Apply border/outline settings if available
        if hasattr(segment, 'subtitle_border_enabled'):
            if segment.subtitle_border_enabled:
                style['borderstyle'] = str(segment.subtitle_border_style)
                style['outline'] = str(segment.subtitle_outline_width)
                style['outlinecolour'] = segment.subtitle_outline_color
                style['shadow'] = str(segment.subtitle_shadow)
            else:
                # No border/outline - use opaque box background for visibility
                # borderstyle=3 creates a background box without outline
                style['borderstyle'] = '3'
                style['outline'] = '0'
                style['shadow'] = '0'
                # Ensure semi-transparent background for contrast
                style['backcolour'] = '&H80000000'  # Semi-transparent black

        return style

    def _cleanup_temp_files(self, segment_videos: List[str], combined_path: Path):
        """Clean up temporary files"""
        try:
            # Clean up segment videos
            for video_path in segment_videos:
                try:
                    if os.path.exists(video_path):
                        os.unlink(video_path)
                except Exception as e:
                    logger.warning(f"Could not delete temp file {video_path}: {e}")

            # Clean up combined video
            try:
                if combined_path.exists():
                    os.unlink(combined_path)
            except Exception as e:
                logger.warning(f"Could not delete combined file: {e}")

            logger.info("Cleanup completed")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def generate_preview(
        self,
        segment_index: int,
        output_path: str
    ) -> bool:
        """Generate a preview for a single segment"""
        try:
            if segment_index < 0 or segment_index >= len(self.project.timeline.segments):
                logger.error(f"Invalid segment index: {segment_index}")
                return False

            segment = self.project.timeline.segments[segment_index]

            # Generate audio if not already done
            if not segment.audio_path or not os.path.exists(segment.audio_path):
                audio_path, subtitle_path = await self.tts_service.generate_audio(
                    text=segment.text,
                    language=segment.language,
                    voice=segment.voice_id,
                    project_name=self.project.name,
                    segment_name=f"preview_{segment.name}",
                    rate=segment.rate,
                    volume=segment.volume,
                    pitch=segment.pitch
                )
                segment.audio_path = audio_path
                segment.subtitle_path = subtitle_path

            # Extract video segment
            segment_video = self.temp_dir / f"preview_segment.mp4"
            FFmpegUtils.extract_video_segment(
                self.project.video_path,
                segment.start_time,
                segment.end_time,
                str(segment_video)
            )

            # Process with audio and subtitles
            subtitle_path = None
            if segment.subtitle_enabled and segment.subtitle_path:
                ass_path = segment.subtitle_path.replace('.srt', '.ass')
                style_options = self._get_subtitle_style(segment)
                SubtitleUtils.create_custom_ass_style(
                    segment.subtitle_path,
                    ass_path,
                    style_options
                )
                subtitle_path = ass_path

            success = FFmpegUtils.process_segment_video(
                str(segment_video),
                segment.audio_path,
                subtitle_path,
                output_path,
                "balanced"
            )

            logger.info(f"Preview generated: {output_path}")
            return success

        except Exception as e:
            logger.error(f"Failed to generate preview: {e}")
            return False
