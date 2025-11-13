"""TTS Service - Proven edge-tts integration patterns"""

import os
import asyncio
import hashlib
import json
from pathlib import Path
from typing import Optional, Tuple, Dict
import edge_tts
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import aiohttp

from utils.logger import logger
from config import settings


class TTSService:
    """
    TTS Service using proven patterns from existing system
    Based on: TTS_System_Documentation.md
    """

    def __init__(self):
        self.cache_file = Path(settings.CACHE_DIR) / "tts_cache.json"
        self.cache_mapping = self._load_cache()

        # Best voices from existing system
        self.best_voices = {
            'en': 'en-US-AvaMultilingualNeural',
            'fr': 'fr-FR-VivienneMultilingualNeural',
            'ko': 'ko-KR-HyunsuMultilingualNeural',
            'hi': 'hi-IN-MadhurNeural',
            'kn': 'kn-IN-GaganNeural',
            'ta': 'ta-IN-ValluvarNeural',
            'te': 'te-IN-ShrutiNeural',
            'ml': 'ml-IN-SobhanaNeural',
            'es': 'es-ES-ElviraNeural',
            'de': 'de-DE-KatjaNeural',
            'it': 'it-IT-ElsaNeural',
            'pt': 'pt-BR-FranciscaNeural',
            'zh': 'zh-CN-XiaoxiaoNeural',
            'ja': 'ja-JP-NanamiNeural',
            'ar': 'ar-SA-ZariyahNeural',
            'ru': 'ru-RU-SvetlanaNeural'
        }

    def _load_cache(self) -> Dict:
        """Load cache from file"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load cache: {e}")
        return {}

    def _save_cache(self):
        """Save cache to file"""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache_mapping, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save cache: {e}")

    def _generate_cache_key(
        self,
        text: str,
        voice: str,
        rate: str,
        volume: str,
        pitch: str
    ) -> str:
        """
        PROVEN: Generate cache key using MD5 hash
        From: TTS_System_Documentation.md
        """
        content = f"{text}_{voice}_{rate}_{volume}_{pitch}"
        return hashlib.md5(content.encode()).hexdigest()

    def _generate_accurate_subtitles(self, audio_path: str, text: str) -> str:
        """
        Generate accurate subtitles based on actual audio duration
        Splits text into reasonable chunks and distributes timing evenly
        """
        import subprocess

        # Get actual audio duration
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            audio_duration = float(result.stdout.strip())
        except Exception as e:
            logger.error(f"Could not get audio duration: {e}")
            audio_duration = 10.0  # fallback

        # Split text into chunks (approximately 40-50 chars per chunk for readability)
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0

        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1  # +1 for space

            # Create chunk if it's getting long (40-60 chars is readable)
            if current_length >= 45:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_length = 0

        # Add remaining words
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        # If text is short, use single chunk
        if len(chunks) == 0:
            chunks = [text]

        # Generate SRT with evenly distributed timing
        srt_content = ""
        chunk_duration = audio_duration / len(chunks)

        for i, chunk in enumerate(chunks):
            start_time = i * chunk_duration
            end_time = min((i + 1) * chunk_duration, audio_duration)

            # Format times as SRT format (HH:MM:SS,mmm)
            start_srt = self._format_srt_time(start_time)
            end_srt = self._format_srt_time(end_time)

            srt_content += f"{i + 1}\n"
            srt_content += f"{start_srt} --> {end_srt}\n"
            srt_content += f"{chunk}\n\n"

        logger.info(f"Generated {len(chunks)} subtitle chunks for {audio_duration:.2f}s audio")
        return srt_content

    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds as SRT time format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _get_best_voice(self, language: str, preferred_voice: Optional[str] = None) -> str:
        """
        PROVEN: Get the best voice for a language
        From: TTS_System_Documentation.md
        """
        if preferred_voice:
            return preferred_voice
        return self.best_voices.get(language, 'en-US-AvaMultilingualNeural')

    def find_cached_files(self, cache_key: str) -> Tuple[Optional[str], Optional[str]]:
        """
        PROVEN: Find existing cached files
        From: TTS_System_Documentation.md
        """
        if cache_key in self.cache_mapping:
            cached_data = self.cache_mapping[cache_key]

            # Handle both old format (string) and new format (dict)
            if isinstance(cached_data, str):
                audio_path = cached_data
                subtitle_path = None
            else:
                audio_path = cached_data.get("audio_path")
                subtitle_path = cached_data.get("subtitle_path")

            # Check if files exist
            audio_exists = audio_path and os.path.exists(audio_path)
            subtitle_exists = subtitle_path and os.path.exists(subtitle_path)

            if audio_exists:
                return audio_path, subtitle_path if subtitle_exists else None
            else:
                # Remove invalid cache entry
                del self.cache_mapping[cache_key]
                self._save_cache()

        return None, None

    def store_cache_mapping(
        self,
        cache_key: str,
        audio_path: str,
        subtitle_path: Optional[str] = None
    ):
        """
        PROVEN: Store cache key to file path mapping
        From: TTS_System_Documentation.md
        """
        self.cache_mapping[cache_key] = {
            "audio_path": audio_path,
            "subtitle_path": subtitle_path
        }
        self._save_cache()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((
            aiohttp.ClientTimeout,
            aiohttp.ServerTimeoutError,
            aiohttp.ClientConnectorError,
            asyncio.TimeoutError,
            ConnectionError
        ))
    )
    async def _generate_audio_and_subtitle(
        self,
        text: str,
        voice: str,
        rate: str,
        volume: str,
        pitch: str,
        audio_path: str,
        subtitle_path: str
    ):
        """
        PROVEN: Generate both audio and subtitle files using edge-tts streaming
        From: TTS_System_Documentation.md
        """
        try:
            # Create communication object
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                volume=volume,
                pitch=pitch
            )

            # Create subtitle maker
            submaker = edge_tts.SubMaker()

            # Stream audio and subtitle data
            audio_data = bytearray()

            async def stream_with_timeout():
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data.extend(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        submaker.feed(chunk)

            # Add timeout for streaming
            await asyncio.wait_for(stream_with_timeout(), timeout=30.0)

            # Write audio file
            with open(audio_path, "wb") as audio_file:
                audio_file.write(audio_data)

            # Save subtitle file
            subtitle_content = submaker.get_srt()

            # Validate subtitle content
            if not subtitle_content or subtitle_content.strip() == "":
                logger.warning("No subtitle data generated from edge-tts - generating accurate subtitles")
                # Generate accurate subtitles based on actual audio duration
                subtitle_content = self._generate_accurate_subtitles(audio_path, text)

            with open(subtitle_path, "w", encoding="utf-8") as subtitle_file:
                subtitle_file.write(subtitle_content)

            logger.info(f"Generated audio and subtitle files")

        except asyncio.TimeoutError:
            raise Exception("Audio generation timed out after 30 seconds")
        except Exception as e:
            logger.error(f"Error in audio generation: {e}")
            # Clean up partial files on error
            if os.path.exists(audio_path):
                os.remove(audio_path)
            if os.path.exists(subtitle_path):
                os.remove(subtitle_path)
            raise

    async def generate_audio(
        self,
        text: str,
        language: str,
        voice: Optional[str] = None,
        project_name: str = "default",
        segment_name: Optional[str] = None,
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz"
    ) -> Tuple[str, Optional[str]]:
        """
        PROVEN: Generate audio file from text and return (audio_path, subtitle_path)
        From: TTS_System_Documentation.md
        """
        try:
            # Get voice
            selected_voice = voice or self._get_best_voice(language)

            # Generate cache key
            cache_key = self._generate_cache_key(text, selected_voice, rate, volume, pitch)

            # Check if files already exist (caching)
            existing_audio, existing_subtitle = self.find_cached_files(cache_key)
            if existing_audio:
                logger.info(f"Using cached audio for cache_key: {cache_key[:8]}")
                return existing_audio, existing_subtitle

            # Create file paths
            file_name = segment_name or f"audio_{cache_key[:8]}"
            project_dir = Path(settings.PROJECTS_DIR) / project_name / language
            project_dir.mkdir(parents=True, exist_ok=True)

            audio_path = str(project_dir / f"{file_name}.mp3")
            subtitle_path = str(project_dir / f"{file_name}.srt")

            # Generate audio and subtitle using streaming
            await self._generate_audio_and_subtitle(
                text, selected_voice, rate, volume, pitch, audio_path, subtitle_path
            )

            # Store cache mapping
            self.store_cache_mapping(cache_key, audio_path, subtitle_path)

            logger.info(f"Successfully generated audio: {audio_path}")
            return audio_path, subtitle_path

        except Exception as e:
            logger.error(f"Failed to generate audio: {e}")
            raise Exception(f"Failed to generate audio: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((
            aiohttp.ClientTimeout,
            aiohttp.ServerTimeoutError,
            aiohttp.ClientConnectorError,
            asyncio.TimeoutError,
            ConnectionError
        ))
    )
    async def get_available_voices(self, language: Optional[str] = None):
        """
        Get list of available voices with retry logic
        Handles different edge-tts API versions and structures
        """
        try:
            logger.info("Fetching available voices...")

            # Try different API methods (edge-tts API has changed over versions)
            try:
                # New API (edge-tts >= 6.0.0)
                from edge_tts import VoicesManager
                voices_manager = await VoicesManager.create()
                voices = voices_manager.voices
            except (ImportError, AttributeError):
                # Old API (edge-tts < 6.0.0)
                voices = await edge_tts.list_voices()

            if not voices:
                logger.warning("No voices returned from edge-tts")
                return []

            voice_list = []

            for voice in voices:
                try:
                    # Handle different voice dict structures
                    # Try multiple key names that different versions use
                    locale = voice.get('Locale') or voice.get('locale') or voice.get('Language')

                    if not locale:
                        continue

                    # Filter by language if specified
                    if language and not locale.lower().startswith(language.lower()):
                        continue

                    # Extract voice information with fallbacks
                    friendly_name = (
                        voice.get('FriendlyName') or
                        voice.get('Name') or
                        voice.get('DisplayName') or
                        voice.get('ShortName') or
                        'Unknown'
                    )

                    short_name = (
                        voice.get('ShortName') or
                        voice.get('Name') or
                        voice.get('FriendlyName') or
                        'Unknown'
                    )

                    gender = (
                        voice.get('Gender') or
                        voice.get('VoiceGender') or
                        'Unknown'
                    )

                    voice_info = {
                        'name': friendly_name,
                        'short_name': short_name,
                        'gender': gender,
                        'language': locale.split('-')[0],
                        'locale': locale
                    }
                    voice_list.append(voice_info)

                except Exception as e:
                    # Skip voices that can't be parsed
                    logger.debug(f"Skipping voice due to parsing error: {e}")
                    continue

            logger.info(f"Successfully fetched {len(voice_list)} voices")
            return voice_list

        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            raise Exception(f"Failed to get voices: {e}")
