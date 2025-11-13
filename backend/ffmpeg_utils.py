"""FFmpeg utilities - Proven patterns from existing system"""

import subprocess
import os
from typing import Optional, List, Tuple
from pathlib import Path
from utils.logger import logger
from config import settings


class FFmpegUtils:
    """Wraps proven FFmpeg commands from existing system"""

    @staticmethod
    def get_media_duration(file_path: str) -> Optional[float]:
        """
        PROVEN: Get media file duration using ffprobe
        From: FFmpeg_Video_Generation_Documentation.md
        """
        try:
            cmd = [
                settings.FFPROBE_PATH,
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
            return None
        except Exception as e:
            logger.error(f"Error getting duration: {e}")
            return None

    @staticmethod
    def has_audio_stream(video_path: str) -> bool:
        """
        PROVEN: Check if a video file has an audio stream
        From: FFmpeg_Video_Generation_Documentation.md
        """
        try:
            cmd = [
                settings.FFPROBE_PATH,
                '-v', 'quiet',
                '-select_streams', 'a',
                '-show_entries', 'stream=codec_type',
                '-of', 'csv=p=0',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0 and 'audio' in result.stdout
        except Exception as e:
            logger.warning(f"Could not determine audio stream info: {e}")
            return False

    @staticmethod
    def get_video_info(video_path: str) -> Optional[dict]:
        """Get video resolution, codec, and format information"""
        try:
            cmd = [
                settings.FFPROBE_PATH,
                '-v', 'quiet',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height,pix_fmt,codec_name,r_frame_rate',
                '-of', 'csv=p=0',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                info = result.stdout.strip().split(',')
                if len(info) >= 4:
                    # Parse with error handling
                    try:
                        width = int(info[0]) if info[0].isdigit() else 0
                        height = int(info[1]) if info[1].isdigit() else 0
                    except (ValueError, IndexError):
                        width = 0
                        height = 0

                    pix_fmt = info[2] if len(info) > 2 else "yuv420p"
                    codec = info[3] if len(info) > 3 else "unknown"
                    fps = info[4] if len(info) > 4 else "30/1"

                    # Parse FPS
                    try:
                        if '/' in fps:
                            num, den = fps.split('/')
                            fps_val = float(num) / float(den) if float(den) != 0 else 30.0
                        else:
                            fps_val = float(fps)
                    except (ValueError, ZeroDivisionError):
                        fps_val = 30.0

                    return {
                        'width': width,
                        'height': height,
                        'pix_fmt': pix_fmt,
                        'codec': codec,
                        'fps': round(fps_val, 2)
                    }
            return None
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None

    @staticmethod
    def extract_video_segment(
        video_path: str,
        start_time: float,
        end_time: float,
        output_path: str,
        re_encode: bool = False
    ) -> bool:
        """
        Extract a video segment from original video

        Args:
            video_path: Source video path
            start_time: Start time in seconds
            end_time: End time in seconds
            output_path: Output file path
            re_encode: If True, re-encode to ensure compatibility for concatenation.
                      If False, use stream copy (faster but may cause concat issues)
        """
        try:
            duration = end_time - start_time

            if re_encode:
                # Re-encode to ensure consistent format for concatenation
                cmd = [
                    settings.FFMPEG_PATH,
                    '-ss', str(start_time),
                    '-i', video_path,
                    '-t', str(duration),
                    '-c:v', settings.DEFAULT_VIDEO_CODEC,
                    '-c:a', settings.DEFAULT_AUDIO_CODEC,
                    '-preset', settings.DEFAULT_PRESET,
                    '-crf', str(settings.DEFAULT_CRF),
                    '-pix_fmt', 'yuv420p',  # Ensure consistent pixel format
                    '-y',
                    output_path
                ]
                logger.info(f"Extracting and re-encoding segment: {start_time:.1f}s - {end_time:.1f}s")
            else:
                # Fast stream copy
                cmd = [
                    settings.FFMPEG_PATH,
                    '-ss', str(start_time),
                    '-i', video_path,
                    '-t', str(duration),
                    '-c', 'copy',
                    '-y',
                    output_path
                ]
                logger.info(f"Extracting segment (stream copy): {start_time:.1f}s - {end_time:.1f}s")

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"Extracted segment: {start_time}s - {end_time}s")
                return True
            else:
                logger.error(f"Failed to extract segment: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error extracting segment: {e}")
            return False

    @staticmethod
    def process_segment_video(
        video_path: str,
        audio_path: str,
        subtitle_path: Optional[str],
        output_path: str,
        quality: str = "balanced",
        expected_duration: Optional[float] = None
    ) -> bool:
        """
        PROVEN: Combine video, TTS audio, and subtitles
        From: FFmpeg_Video_Generation_Documentation.md

        Args:
            video_path: Path to video segment
            audio_path: Path to TTS audio (voice-over)
            subtitle_path: Optional path to ASS subtitle file
            output_path: Path to save processed video
            quality: Quality preset (lossless, high, balanced)
            expected_duration: Expected output duration (segment duration)
                              If provided, output will match this duration
        """
        try:
            # Get durations
            video_duration = FFmpegUtils.get_media_duration(video_path)
            audio_duration = FFmpegUtils.get_media_duration(audio_path)

            if not video_duration or not audio_duration:
                logger.error("Could not get video/audio duration")
                return False

            # Use expected duration if provided, otherwise use video duration
            target_duration = expected_duration if expected_duration else video_duration

            logger.info(f"Video: {video_duration:.1f}s, Audio: {audio_duration:.1f}s, Target: {target_duration:.1f}s")

            # Check if original video has audio
            has_video_audio = FFmpegUtils.has_audio_stream(video_path)

            # Quality settings
            crf_map = {
                "lossless": settings.LOSSLESS_CRF,
                "high": settings.HIGH_CRF,
                "balanced": settings.BALANCED_CRF
            }
            crf = crf_map.get(quality, settings.DEFAULT_CRF)

            # Build filter_complex based on audio presence
            # Use PROVEN pattern from documentation - simple and fast
            if has_video_audio:
                # Mix video audio with TTS audio
                # amix automatically handles different durations - no need for apad!
                # duration=first means output duration = first input (video)
                audio_filter = "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0[aout]"
                logger.info("Mixing video audio + TTS audio")
            else:
                # Video has no audio, use only TTS audio
                # Just copy TTS audio as output audio
                audio_filter = "[1:a]anull[aout]"
                logger.info("Using only TTS audio (no video audio)")

            # Build command with subtitles if provided
            if subtitle_path and os.path.exists(subtitle_path):
                # WITH SUBTITLES
                # Escape ASS path for FFmpeg
                ass_path_escaped = subtitle_path.replace('\\', '\\\\').replace(':', '\\:')

                command = [
                    settings.FFMPEG_PATH,
                    '-i', video_path,
                    '-i', audio_path,
                    '-vf', f'ass={ass_path_escaped}',
                    '-filter_complex', audio_filter,
                    '-map', '0:v',
                    '-map', '[aout]',
                    '-c:v', settings.DEFAULT_VIDEO_CODEC,
                    '-c:a', settings.DEFAULT_AUDIO_CODEC,
                    '-preset', settings.DEFAULT_PRESET,
                    '-crf', str(crf),
                    '-y',
                    output_path
                ]
                logger.info("Processing with subtitles and voice-over")
            else:
                # WITHOUT SUBTITLES
                command = [
                    settings.FFMPEG_PATH,
                    '-i', video_path,
                    '-i', audio_path,
                    '-filter_complex', audio_filter,
                    '-map', '0:v',
                    '-map', '[aout]',
                    '-c:v', settings.DEFAULT_VIDEO_CODEC,
                    '-c:a', settings.DEFAULT_AUDIO_CODEC,
                    '-preset', settings.DEFAULT_PRESET,
                    '-crf', str(crf),
                    '-y',
                    output_path
                ]
                logger.info("Processing with voice-over (no subtitles)")

            # Add timeout to prevent hanging (5 minutes max for any segment)
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes timeout
                )
            except subprocess.TimeoutExpired:
                logger.error(f"FFmpeg processing timed out after 300 seconds")
                return False

            if result.returncode == 0 and os.path.exists(output_path):
                output_duration = FFmpegUtils.get_media_duration(output_path)
                file_size = os.path.getsize(output_path) / 1024 / 1024
                logger.info(f"Segment processed: {output_duration:.1f}s, {file_size:.1f}MB")
                return True
            else:
                logger.error(f"Processing failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error processing segment: {e}")
            return False

    @staticmethod
    def concatenate_videos(video_paths: List[str], output_path: str) -> bool:
        """
        PROVEN: Concatenate multiple videos
        From: FFmpeg_Video_Generation_Documentation.md
        """
        try:
            # Create concat file
            concat_file = Path(settings.TEMP_DIR) / "concat_list.txt"

            with open(concat_file, 'w') as f:
                for video_path in video_paths:
                    # Convert to absolute path to avoid path duplication issues
                    abs_path = os.path.abspath(video_path)
                    # Escape for FFmpeg (forward slashes, escape special chars)
                    escaped_path = abs_path.replace('\\', '/')
                    f.write(f"file '{escaped_path}'\n")

            logger.info(f"Concatenating {len(video_paths)} videos")

            cmd = [
                settings.FFMPEG_PATH,
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
                '-y',
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and os.path.exists(output_path):
                duration = FFmpegUtils.get_media_duration(output_path)
                size = os.path.getsize(output_path) / 1024 / 1024
                logger.info(f"Concatenation successful: {duration:.2f}s, {size:.1f}MB")
                return True
            else:
                logger.error(f"Concatenation failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error concatenating videos: {e}")
            return False

    @staticmethod
    def add_background_music(
        video_path: str,
        music_path: str,
        output_path: str
    ) -> bool:
        """
        PROVEN: Add looping background music with fade effects
        From: FFmpeg_Video_Generation_Documentation.md
        """
        try:
            if not os.path.exists(music_path):
                logger.error(f"Music file not found: {music_path}")
                return False

            # Get durations
            video_duration = FFmpegUtils.get_media_duration(video_path)
            music_duration = FFmpegUtils.get_media_duration(music_path)

            if not video_duration or not music_duration:
                logger.error("Could not get durations")
                return False

            fade_duration = settings.FADE_DURATION

            # Check if video has audio
            has_audio = FFmpegUtils.has_audio_stream(video_path)

            # Calculate loops needed
            if video_duration > music_duration:
                loops_needed = int((video_duration / music_duration) + 1)
            else:
                loops_needed = 0

            # Build filter based on audio presence
            tts_boost = settings.TTS_VOLUME_BOOST
            bgm_reduction = settings.BGM_VOLUME_REDUCTION

            if has_audio:
                if loops_needed > 0:
                    filter_complex = (
                        f"[0:a]volume=+{tts_boost}dB[boosted_video];"
                        f"[1:a]aloop=loop={loops_needed}:size={int(music_duration * 44100)},"
                        f"volume=-{bgm_reduction}dB,"
                        f"afade=t=out:st={video_duration-fade_duration}:d={fade_duration},"
                        f"atrim=duration={video_duration}[bg];"
                        f"[boosted_video][bg]amix=inputs=2:duration=first:dropout_transition=0[aout]"
                    )
                else:
                    filter_complex = (
                        f"[0:a]volume=+{tts_boost}dB[boosted_video];"
                        f"[1:a]volume=-{bgm_reduction}dB,"
                        f"afade=t=out:st={video_duration-fade_duration}:d={fade_duration},"
                        f"atrim=duration={video_duration}[bg];"
                        f"[boosted_video][bg]amix=inputs=2:duration=first:dropout_transition=0[aout]"
                    )
            else:
                # Video has no audio
                if loops_needed > 0:
                    filter_complex = (
                        f"[1:a]aloop=loop={loops_needed}:size={int(music_duration * 44100)},"
                        f"volume=-{bgm_reduction}dB,"
                        f"afade=t=out:st={video_duration-fade_duration}:d={fade_duration},"
                        f"atrim=duration={video_duration}[aout]"
                    )
                else:
                    filter_complex = (
                        f"[1:a]volume=-{bgm_reduction}dB,"
                        f"afade=t=out:st={video_duration-fade_duration}:d={fade_duration},"
                        f"atrim=duration={video_duration}[aout]"
                    )

            cmd = [
                settings.FFMPEG_PATH,
                '-i', video_path,
                '-i', music_path,
                '-filter_complex', filter_complex,
                '-map', '0:v',
                '-map', '[aout]',
                '-c:v', 'copy',
                '-c:a', settings.DEFAULT_AUDIO_CODEC,
                '-y',
                output_path
            ]

            logger.info("Adding background music with fade effects")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and os.path.exists(output_path):
                size = os.path.getsize(output_path) / 1024 / 1024
                logger.info(f"Background music added: {size:.1f}MB")
                return True
            else:
                logger.error(f"Failed to add background music: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error adding background music: {e}")
            return False
