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

        # Proxy configuration
        self.proxy_enabled = settings.TTS_PROXY_ENABLED
        self.proxy_url = settings.TTS_PROXY_URL if self.proxy_enabled and settings.TTS_PROXY_URL else None

        # Log proxy status
        if self.proxy_enabled and self.proxy_url:
            logger.info(f"🌐 TTS Proxy ENABLED: {self.proxy_url}")
        else:
            logger.info("🌐 TTS Proxy DISABLED: Direct connection to TTS service")

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

    async def check_tts_connectivity(self) -> Dict[str, any]:
        """
        Check connectivity to TTS service with and without proxy
        Returns status information about the connection
        """
        status = {
            'proxy_enabled': self.proxy_enabled,
            'proxy_url': self.proxy_url,
            'direct_connection': False,
            'proxy_connection': False,
            'recommended_mode': 'unknown'
        }

        test_text = "Hello"
        test_voice = "en-US-AvaMultilingualNeural"

        # Test direct connection (without proxy)
        try:
            logger.info("🔍 Testing direct connection to TTS service...")
            communicate = edge_tts.Communicate(
                text=test_text,
                voice=test_voice,
                proxy=None
            )
            # Try to get first chunk to test connectivity
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    status['direct_connection'] = True
                    logger.info("✅ Direct connection to TTS service: SUCCESS")
                    break
        except Exception as e:
            logger.warning(f"❌ Direct connection to TTS service: FAILED - {str(e)[:100]}")
            status['direct_connection'] = False

        # Test proxy connection (if proxy is configured)
        if self.proxy_enabled and self.proxy_url:
            try:
                logger.info(f"🔍 Testing proxy connection via {self.proxy_url}...")
                communicate = edge_tts.Communicate(
                    text=test_text,
                    voice=test_voice,
                    proxy=self.proxy_url
                )
                # Try to get first chunk to test connectivity
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        status['proxy_connection'] = True
                        logger.info("✅ Proxy connection to TTS service: SUCCESS")
                        break
            except Exception as e:
                logger.warning(f"❌ Proxy connection to TTS service: FAILED - {str(e)[:100]}")
                status['proxy_connection'] = False

        # Determine recommended mode
        if status['direct_connection']:
            status['recommended_mode'] = 'direct'
            logger.info("💡 Recommendation: Use direct connection (no proxy needed)")
        elif status['proxy_connection']:
            status['recommended_mode'] = 'proxy'
            logger.info("💡 Recommendation: Use proxy connection")
        else:
            status['recommended_mode'] = 'none'
            logger.error("⚠️  WARNING: Cannot reach TTS service via direct or proxy connection!")

        return status

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

    def _generate_word_timed_subtitles(
        self,
        word_timings: list,
        text: str,
        orientation: str = 'horizontal'
    ) -> str:
        """
        Generate subtitles using actual word timing data from edge-tts
        Splits text into chunks based on actual speech timing, not character count

        Args:
            word_timings: List of word timing dicts from edge-tts WordBoundary
                         Each dict has: {'text': str, 'offset': int, 'duration': int}
            text: Full text to subtitle
            orientation: Video orientation for chunk size adjustment

        Returns:
            SRT formatted subtitle string with precise word-boundary timing
        """
        if not word_timings:
            logger.warning("No word timing data available, using fallback")
            return self._generate_accurate_subtitles_fallback(text, 10.0, orientation)

        # Adjust chunk size based on video orientation
        if orientation == 'horizontal':
            # Horizontal: ~100 chars per chunk
            target_chunk_size = 100
            logger.info(f"📺 Horizontal video: Using word-timed sentence chunks (~{target_chunk_size} chars)")
        else:
            # Vertical: ~45 chars per chunk
            target_chunk_size = 45
            logger.info(f"📱 Vertical video: Using word-timed word chunks (~{target_chunk_size} chars)")

        # Calculate total audio duration
        total_duration = (word_timings[-1]['offset'] + word_timings[-1]['duration']) / 10_000_000.0

        # For horizontal videos: split at reasonable intervals to avoid showing too much text
        # For vertical videos: use smaller chunks for readability
        if orientation == 'horizontal':
            # Use fixed max duration for better readability (not too much text at once)
            # 4 seconds is comfortable reading time for ~12-15 words
            max_chunk_duration = 4.0  # Max 4 seconds per chunk
            min_chunk_duration = 2.0  # Min 2 seconds per chunk for readability

            logger.info(f"Using duration-based chunking: {total_duration:.1f}s audio, max chunk: {max_chunk_duration:.1f}s")
        else:
            # Vertical: shorter chunks for better mobile readability
            max_chunk_duration = 3.0  # Max 3 seconds per chunk
            min_chunk_duration = 1.5  # Min 1.5 seconds per chunk

        # Group words into chunks based on DURATION, not character count
        chunks = []
        current_chunk_words = []
        current_chunk_start = 0.0

        # Natural break points for better readability
        sentence_enders = {'.', '!', '?'}
        pause_words = {',', ';', ':', '-', 'and', 'but', 'or', 'so', 'yet', 'then', 'also'}

        for i, word_data in enumerate(word_timings):
            word = word_data['text']
            word_start = word_data['offset'] / 10_000_000.0
            word_end = (word_data['offset'] + word_data['duration']) / 10_000_000.0

            # Add word to current chunk
            current_chunk_words.append(word_data)

            # Calculate current chunk duration
            if current_chunk_words:
                chunk_duration = word_end - current_chunk_start
            else:
                chunk_duration = 0

            # Check if we should break here
            is_sentence_end = any(word.endswith(p) for p in sentence_enders)
            is_pause_word = word.lower().strip('.,!?;:') in pause_words

            # Look at next word timing (if exists) for natural pauses
            has_pause_after = False
            if i + 1 < len(word_timings):
                next_word_start = word_timings[i + 1]['offset'] / 10_000_000.0
                gap_to_next = next_word_start - word_end
                has_pause_after = gap_to_next > 0.15  # 150ms+ gap indicates natural pause

            # Decision: Break chunk if:
            # 1. We hit target duration AND there's a sentence end
            # 2. We hit target duration AND there's a natural pause/break word
            # 3. We exceed max duration (forced break)
            # 4. Last word (always close the chunk)
            should_break = (
                (chunk_duration >= max_chunk_duration * 0.7 and is_sentence_end) or
                (chunk_duration >= max_chunk_duration * 0.8 and (is_pause_word or has_pause_after)) or
                (chunk_duration >= max_chunk_duration * 1.1) or  # Forced break at 110% of max
                (i == len(word_timings) - 1)  # Last word
            )

            # Also ensure minimum chunk duration (don't break too early)
            if chunk_duration < min_chunk_duration and i < len(word_timings) - 1:
                should_break = False

            if should_break and len(current_chunk_words) > 0:
                chunks.append(current_chunk_words)
                current_chunk_words = []
                # Next chunk starts at next word
                if i + 1 < len(word_timings):
                    current_chunk_start = word_timings[i + 1]['offset'] / 10_000_000.0

        # If no chunks created, use all words as one chunk
        if not chunks:
            chunks = [word_timings]

        # Generate SRT using actual word timing
        srt_content = ""

        for i, chunk_words in enumerate(chunks):
            # Start time: offset of first word (convert from 100-nanosecond units to seconds)
            start_time = chunk_words[0]['offset'] / 10_000_000.0

            # End time: offset + duration of last word
            last_word = chunk_words[-1]
            end_time = (last_word['offset'] + last_word['duration']) / 10_000_000.0

            # Chunk text
            chunk_text = ' '.join([w['text'] for w in chunk_words])

            # Format times as SRT
            start_srt = self._format_srt_time(start_time)
            end_srt = self._format_srt_time(end_time)

            srt_content += f"{i + 1}\n"
            srt_content += f"{start_srt} --> {end_srt}\n"
            srt_content += f"{chunk_text}\n\n"

        logger.info(f"Generated {len(chunks)} word-timed subtitle chunks (precise to milliseconds)")
        return srt_content

    def _generate_accurate_subtitles_fallback(
        self,
        text: str,
        audio_duration: float,
        orientation: str = 'horizontal'
    ) -> str:
        """
        Fallback subtitle generation when word timing is not available
        Uses even time distribution (less accurate but better than nothing)
        """
        # Adjust chunk size based on video orientation
        if orientation == 'horizontal':
            target_chunk_size = 100
        else:
            target_chunk_size = 45

        # Split text into chunks
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0

        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1

            if current_length >= target_chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_length = 0

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        if not chunks:
            chunks = [text]

        # Generate SRT with evenly distributed timing
        srt_content = ""
        chunk_duration = audio_duration / len(chunks)

        for i, chunk in enumerate(chunks):
            start_time = i * chunk_duration
            end_time = audio_duration if i == len(chunks) - 1 else (i + 1) * chunk_duration

            start_srt = self._format_srt_time(start_time)
            end_srt = self._format_srt_time(end_time)

            srt_content += f"{i + 1}\n"
            srt_content += f"{start_srt} --> {end_srt}\n"
            srt_content += f"{chunk}\n\n"

        logger.warning(f"Used fallback timing for {len(chunks)} chunks (less accurate)")
        return srt_content

    def _format_srt_time(self, seconds: float) -> str:
        """
        Format seconds as SRT time format (HH:MM:SS,mmm) with millisecond precision
        Uses proper rounding to avoid truncation errors
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        # Use round() instead of int() to properly round milliseconds
        # This prevents -1ms errors from truncation
        millis = round((seconds % 1) * 1000)

        # Handle edge case where rounding millis to 1000
        if millis >= 1000:
            millis = 0
            secs += 1
            if secs >= 60:
                secs = 0
                minutes += 1
                if minutes >= 60:
                    minutes = 0
                    hours += 1

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
        subtitle_path: str,
        orientation: str = 'horizontal'
    ):
        """
        Generate both audio and subtitle files using edge-tts streaming
        Uses word-boundary timing data for precise subtitle synchronization
        Supports proxy with automatic fallback to direct connection
        """
        # Determine which connection method to try first and fallback
        connection_attempts = []

        if self.proxy_enabled and self.proxy_url:
            # Try proxy first, then direct as fallback
            connection_attempts = [
                ('proxy', self.proxy_url),
                ('direct', None)
            ]
            logger.info(f"🌐 Using proxy mode with fallback: {self.proxy_url}")
        else:
            # Direct connection only
            connection_attempts = [
                ('direct', None)
            ]
            logger.debug("🌐 Using direct connection mode")

        last_error = None

        for attempt_name, proxy_setting in connection_attempts:
            try:
                if attempt_name == 'proxy':
                    logger.debug(f"Attempting TTS generation via proxy: {proxy_setting}")
                else:
                    logger.debug("Attempting TTS generation via direct connection")

                # Create communication object with appropriate proxy setting
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=voice,
                    rate=rate,
                    volume=volume,
                    pitch=pitch,
                    proxy=proxy_setting
                )

                # Create subtitle maker and collect word timing data
                submaker = edge_tts.SubMaker()
                word_timings = []  # Collect word boundary data for precise timing

                # Stream audio and subtitle data
                audio_data = bytearray()

                async def stream_with_timeout():
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_data.extend(chunk["data"])
                        elif chunk["type"] == "WordBoundary":
                            # Collect word timing data
                            word_timings.append({
                                'text': chunk.get('text', ''),
                                'offset': chunk.get('offset', 0),
                                'duration': chunk.get('duration', 0)
                            })
                            submaker.feed(chunk)

                # Add timeout for streaming
                await asyncio.wait_for(stream_with_timeout(), timeout=30.0)

                # Write audio file
                with open(audio_path, "wb") as audio_file:
                    audio_file.write(audio_data)

                # Generate subtitles using word timing data for precise synchronization
                if word_timings:
                    logger.info(f"📊 Collected {len(word_timings)} word timings from edge-tts")
                    # Use word-timed subtitles for all orientations
                    subtitle_content = self._generate_word_timed_subtitles(
                        word_timings, text, orientation
                    )
                else:
                    # Fallback: use edge-tts generated subtitles or time-based estimation
                    logger.warning("No word timing data available, using fallback")
                    if orientation == 'vertical':
                        # For vertical, try edge-tts subtitles first
                        subtitle_content = submaker.get_srt()
                        if not subtitle_content or subtitle_content.strip() == "":
                            # Get audio duration for fallback
                            import subprocess
                            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', audio_path]
                            result = subprocess.run(cmd, capture_output=True, text=True)
                            audio_duration = float(result.stdout.strip()) if result.returncode == 0 else 10.0
                            subtitle_content = self._generate_accurate_subtitles_fallback(text, audio_duration, orientation)
                    else:
                        # For horizontal, get audio duration and use fallback
                        import subprocess
                        cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', audio_path]
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        audio_duration = float(result.stdout.strip()) if result.returncode == 0 else 10.0
                        subtitle_content = self._generate_accurate_subtitles_fallback(text, audio_duration, orientation)

                with open(subtitle_path, "w", encoding="utf-8") as subtitle_file:
                    subtitle_file.write(subtitle_content)

                # Success! Log which method worked
                if attempt_name == 'proxy':
                    logger.info(f"✅ Generated audio via PROXY successfully")
                else:
                    logger.info(f"✅ Generated audio via DIRECT connection successfully")

                logger.info(f"Generated audio and subtitle files with precise word-boundary timing")
                return  # Success, exit the function

            except asyncio.TimeoutError as e:
                last_error = e
                if attempt_name == 'proxy':
                    logger.warning(f"⚠️  Proxy connection timed out, trying fallback...")
                else:
                    logger.error(f"❌ Direct connection timed out")
                # Clean up partial files
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                if os.path.exists(subtitle_path):
                    os.remove(subtitle_path)
                # Continue to next attempt
                continue

            except Exception as e:
                last_error = e
                if attempt_name == 'proxy':
                    logger.warning(f"⚠️  Proxy connection failed: {str(e)[:100]}, trying fallback...")
                else:
                    logger.error(f"❌ Direct connection failed: {str(e)[:100]}")
                # Clean up partial files on error
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                if os.path.exists(subtitle_path):
                    os.remove(subtitle_path)
                # Continue to next attempt
                continue

        # If we get here, all attempts failed
        if last_error:
            if isinstance(last_error, asyncio.TimeoutError):
                raise Exception("Audio generation timed out after 30 seconds (tried all connection methods)")
            else:
                raise Exception(f"Audio generation failed after trying all connection methods: {last_error}")

    async def generate_audio(
        self,
        text: str,
        language: str,
        voice: Optional[str] = None,
        project_name: str = "default",
        segment_name: Optional[str] = None,
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
        orientation: str = 'horizontal'
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
            # Pass orientation to adjust subtitle chunking based on video format
            await self._generate_audio_and_subtitle(
                text, selected_voice, rate, volume, pitch, audio_path, subtitle_path, orientation
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
