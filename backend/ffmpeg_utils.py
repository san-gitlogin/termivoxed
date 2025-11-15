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
        import json

        try:
            # Use JSON output for reliable field parsing
            cmd = [
                settings.FFPROBE_PATH,
                '-v', 'quiet',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height,pix_fmt,codec_name,r_frame_rate',
                '-of', 'json',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                data = json.loads(result.stdout)

                if 'streams' in data and len(data['streams']) > 0:
                    stream = data['streams'][0]

                    width = stream.get('width', 0)
                    height = stream.get('height', 0)
                    pix_fmt = stream.get('pix_fmt', 'yuv420p')
                    codec = stream.get('codec_name', 'unknown')
                    fps_str = stream.get('r_frame_rate', '30/1')

                    # Parse FPS
                    try:
                        if '/' in fps_str:
                            num, den = fps_str.split('/')
                            fps_val = float(num) / float(den) if float(den) != 0 else 30.0
                        else:
                            fps_val = float(fps_str)
                    except (ValueError, ZeroDivisionError):
                        fps_val = 30.0

                    logger.debug(f"Video info: {width}x{height}, {codec}, {pix_fmt}, {fps_val:.2f}fps")

                    return {
                        'width': width,
                        'height': height,
                        'pix_fmt': pix_fmt,
                        'codec': codec,
                        'fps': round(fps_val, 2)
                    }

            logger.warning(f"FFprobe returned no stream data for: {video_path}")
            return None

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse FFprobe JSON output: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None

    @staticmethod
    def add_silent_audio_track(video_path: str, output_path: str) -> bool:
        """
        Add a silent audio track to a video that has no audio

        This is useful for videos without audio streams to ensure compatibility
        when adding TTS voiceovers or background music later in the pipeline.

        Args:
            video_path: Path to input video (without audio)
            output_path: Path to output video (with silent audio)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if video already has audio
            if FFmpegUtils.has_audio_stream(video_path):
                logger.info(f"Video already has audio, no need to add silent track")
                return False

            # Get video duration to match silent audio length
            duration = FFmpegUtils.get_media_duration(video_path)
            if not duration:
                logger.error("Could not get video duration")
                return False

            logger.info(f"Adding silent audio track to video ({duration:.1f}s)")

            # Use anullsrc to generate silent audio matching video duration
            # Copy video stream, encode silent audio
            cmd = [
                settings.FFMPEG_PATH,
                '-i', video_path,
                '-f', 'lavfi',
                '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
                '-t', str(duration),
                '-c:v', 'copy',  # Copy video stream (fast, no re-encoding)
                '-c:a', settings.DEFAULT_AUDIO_CODEC,  # Encode silent audio
                '-shortest',  # Match video duration
                '-y',
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"✅ Silent audio track added successfully")

                # Verify output has audio
                if FFmpegUtils.has_audio_stream(output_path):
                    logger.info("✅ Output verified to have audio stream")
                    return True
                else:
                    logger.error("❌ Failed to add audio stream")
                    return False
            else:
                logger.error(f"Failed to add silent audio: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error adding silent audio track: {e}")
            return False

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
                # Check if video has audio to ensure consistent stream structure
                has_audio = FFmpegUtils.has_audio_stream(video_path)

                if has_audio:
                    # Video has audio - re-encode normally
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
                    # Video has no audio - add silent audio track for concatenation compatibility
                    # This ensures all parts have matching streams when concatenating
                    cmd = [
                        settings.FFMPEG_PATH,
                        '-ss', str(start_time),
                        '-i', video_path,
                        '-f', 'lavfi',
                        '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
                        '-t', str(duration),
                        '-c:v', settings.DEFAULT_VIDEO_CODEC,
                        '-c:a', settings.DEFAULT_AUDIO_CODEC,
                        '-preset', settings.DEFAULT_PRESET,
                        '-crf', str(settings.DEFAULT_CRF),
                        '-pix_fmt', 'yuv420p',
                        '-shortest',  # Match shortest input (video duration)
                        '-y',
                        output_path
                    ]
                    logger.info(f"Extracting and re-encoding segment with silent audio: {start_time:.1f}s - {end_time:.1f}s")
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
        output_path: str,
        tts_boost: Optional[float] = None,
        bgm_reduction: Optional[float] = None,
        fade_duration: Optional[float] = None
    ) -> bool:
        """
        PROVEN: Add looping background music with fade effects
        From: FFmpeg_Video_Generation_Documentation.md

        Args:
            video_path: Path to input video
            music_path: Path to background music
            output_path: Path to output video
            tts_boost: TTS volume boost in dB (default from settings)
            bgm_reduction: BGM volume reduction in dB (default from settings)
            fade_duration: Fade out duration in seconds (default from settings)
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

            # Use provided values or defaults from settings
            if fade_duration is None:
                fade_duration = settings.FADE_DURATION
            if tts_boost is None:
                tts_boost = settings.TTS_VOLUME_BOOST
            if bgm_reduction is None:
                bgm_reduction = settings.BGM_VOLUME_REDUCTION

            # Check if video has audio with detailed debugging
            has_audio = FFmpegUtils.has_audio_stream(video_path)

            # Additional debug: Get detailed stream info
            try:
                probe_cmd = [
                    settings.FFPROBE_PATH,
                    '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_streams',
                    video_path
                ]
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                if probe_result.returncode == 0:
                    import json
                    probe_data = json.loads(probe_result.stdout)
                    audio_streams = [s for s in probe_data.get('streams', []) if s.get('codec_type') == 'audio']
                    logger.info(f"🔍 Video stream analysis:")
                    logger.info(f"   - Audio streams detected: {len(audio_streams)}")
                    if audio_streams:
                        for i, stream in enumerate(audio_streams):
                            logger.info(f"   - Stream {i}: {stream.get('codec_name', 'unknown')} @ {stream.get('sample_rate', 'unknown')}Hz")
            except Exception as e:
                logger.warning(f"Could not get detailed stream info: {e}")

            logger.info(f"🎚️ Volume adjustments: TTS +{tts_boost}dB, BGM -{bgm_reduction}dB")

            # Calculate loops needed
            if video_duration > music_duration:
                loops_needed = int((video_duration / music_duration) + 1)
            else:
                loops_needed = 0

            logger.info(f"🔄 Background music loops needed: {loops_needed}")

            # Build filter based on whether video has audio
            if has_audio:
                # Video has audio - mix it with background music
                # Based on proven reference implementation (cl_vid_gen_2.py lines 859-878)
                # +3dB TTS boost, -16dB BGM reduction = 19dB difference favoring speech
                # duration=first means output duration matches first input (video)
                # dropout_transition=0 prevents sudden transitions
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
                logger.info("🎵 Mixing video audio (TTS) with background music")
                logger.info(f"   TTS boost: +{tts_boost}dB | BGM reduction: -{bgm_reduction}dB")
                logger.info(f"   This creates a {tts_boost + bgm_reduction}dB difference favoring TTS")
                logger.info(f"   Using duration=first to match video duration (reference: cl_vid_gen.py:901)")
            else:
                # Video has no audio - just add background music
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
                logger.info("🎵 Adding background music (video has no audio)")

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
            logger.info(f"🎛️ Filter complex: {filter_complex}")
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and os.path.exists(output_path):
                size = os.path.getsize(output_path) / 1024 / 1024
                logger.info(f"✅ Background music added successfully: {size:.1f}MB")

                # Verify output has audio
                output_has_audio = FFmpegUtils.has_audio_stream(output_path)
                if output_has_audio:
                    logger.info("✅ Output video verified to have audio stream")
                else:
                    logger.error("⚠️ WARNING: Output video has no audio stream!")

                # Get detailed audio info
                try:
                    probe_cmd = [
                        settings.FFPROBE_PATH,
                        '-v', 'quiet',
                        '-print_format', 'json',
                        '-show_streams',
                        '-select_streams', 'a',
                        output_path
                    ]
                    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                    if probe_result.returncode == 0:
                        import json
                        probe_data = json.loads(probe_result.stdout)
                        audio_streams = probe_data.get('streams', [])
                        if audio_streams:
                            for i, stream in enumerate(audio_streams):
                                codec = stream.get('codec_name', 'unknown')
                                sample_rate = stream.get('sample_rate', 'unknown')
                                channels = stream.get('channels', 'unknown')
                                logger.info(f"   Output audio stream {i}: {codec} @ {sample_rate}Hz, {channels} channels")
                        else:
                            logger.warning("   No audio streams found in output")
                except Exception as e:
                    logger.warning(f"Could not probe output audio: {e}")

                return True
            else:
                logger.error(f"❌ Failed to add background music")
                logger.error(f"FFmpeg stderr: {result.stderr}")

                # Log the input file info for debugging
                logger.error(f"Input video path: {video_path}")
                logger.error(f"Input video had audio: {has_audio}")
                logger.error(f"Music path: {music_path}")

                return False

        except Exception as e:
            logger.error(f"Error adding background music: {e}")
            return False
