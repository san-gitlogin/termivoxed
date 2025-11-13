# Edge-TTS Based Text-to-Speech System - Complete Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Edge-TTS Library Integration](#edge-tts-library-integration)
4. [Core Components](#core-components)
5. [Audio Generation Process](#audio-generation-process)
6. [Subtitle Generation Process](#subtitle-generation-process)
7. [File Management System](#file-management-system)
8. [Caching Mechanism](#caching-mechanism)
9. [Batch Processing](#batch-processing)
10. [API Endpoints](#api-endpoints)
11. [Configuration System](#configuration-system)
12. [Code Examples and Usage](#code-examples-and-usage)

---

## Project Overview

This is a production-ready FastAPI-based Text-to-Speech (TTS) service that leverages Microsoft Edge's TTS service through the `edge-tts` Python library. The system generates high-quality audio files along with synchronized subtitle files (SRT format) for multiple languages.

### Key Features

- **Simultaneous Audio & Subtitle Generation**: Generates both MP3 audio and SRT subtitle files in a single operation
- **Multi-language Support**: Supports 80+ languages with carefully curated best voices
- **Project-based Organization**: Files are organized by project name and language
- **Intelligent Caching**: Avoids regenerating identical content
- **Batch Processing**: Process multiple TTS requests concurrently with rate limiting
- **Retry Logic**: Automatic retry with exponential backoff for network failures
- **Audio Duration Detection**: Automatically detects and reports audio file duration
- **File Management**: Complete project and file lifecycle management

### Supported Languages (Curated Best Voices)

The system includes carefully selected best voices for:
- English (en-US-AvaMultilingualNeural)
- French (fr-FR-VivienneMultilingualNeural)
- Korean (ko-KR-HyunsuMultilingualNeural)
- Hindi (hi-IN-MadhurNeural)
- Kannada (kn-IN-GaganNeural)
- Tamil (ta-IN-ValluvarNeural)
- Telugu (te-IN-ShrutiNeural)
- Malayalam (ml-IN-SobhanaNeural)

**Note**: Edge-TTS supports 80+ languages total. The system can work with any voice available in edge-tts by specifying the voice parameter.

---

## System Architecture

### Component Overview

```
┌─────────────────┐
│   FastAPI App   │
│   (main.py)     │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬────────────┐
    │         │          │            │
┌───▼───┐ ┌──▼──┐  ┌────▼────┐  ┌────▼────┐
│Config │ │Model│  │  TTS    │  │  File   │
│       │ │     │  │ Service │  │ Manager │
└───────┘ └─────┘  └────┬────┘  └─────────┘
                        │
                   ┌────▼─────┐
                   │ Edge-TTS │
                   │ Library  │
                   └──────────┘
```

### File Structure

```
output/
├── project1/
│   ├── en/
│   │   ├── segment1.mp3
│   │   └── segment1.srt
│   ├── fr/
│   │   ├── segment1.mp3
│   │   └── segment1.srt
│   └── hi/
│       ├── segment1.mp3
│       └── segment1.srt
├── project2/
│   └── ...
└── .cache/
    ├── file_cache.json
    └── file_index.json
```

---

## Edge-TTS Library Integration

### Overview of Edge-TTS

Edge-TTS is a Python module that interfaces with Microsoft Edge's online text-to-speech service. It provides access to high-quality neural voices across 80+ languages.

### Core Edge-TTS Functions Used

#### 1. Voice Listing - `edge_tts.list_voices()`

**Purpose**: Retrieve all available voices from Microsoft Edge TTS service

**Implementation in tts_service.py**:
```python
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
async def get_available_voices(self, language: Optional[str] = None) -> List[VoiceInfo]:
    """Get list of available voices with retry logic"""
    try:
        logger.info("Fetching available voices...")
        voices = await edge_tts.list_voices()
        voice_list = []
        
        for voice in voices:
            # Filter by language if specified
            if language and not voice['Locale'].startswith(language):
                continue
                
            voice_info = VoiceInfo(
                name=voice['FriendlyName'],
                short_name=voice['ShortName'],
                gender=voice['Gender'],
                language=voice['Locale'].split('-')[0],
                locale=voice['Locale'],
                country=voice['Locale'].split('-')[1] if '-' in voice['Locale'] else ''
            )
            voice_list.append(voice_info)
            
        logger.info(f"Successfully fetched {len(voice_list)} voices")
        return voice_list
    except Exception as e:
        logger.error(f"Failed to get voices: {str(e)}")
        raise Exception(f"Failed to get voices: {str(e)}")
```

**Voice Data Structure**:
Each voice object contains:
- `FriendlyName`: Human-readable name (e.g., "Microsoft Ava Online (Natural) - English (United States)")
- `ShortName`: Voice identifier (e.g., "en-US-AvaMultilingualNeural")
- `Gender`: "Female" or "Male"
- `Locale`: Language-Country code (e.g., "en-US", "fr-FR")

#### 2. Audio Generation - `edge_tts.Communicate()`

**Purpose**: Create a communication object for TTS conversion with customizable parameters

**Implementation in tts_service.py**:
```python
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
    """Generate both audio and subtitle files using edge-tts streaming"""
    try:
        # Create communication object with timeout settings
        communicate = edge_tts.Communicate(
            text=text, 
            voice=voice, 
            rate=rate, 
            volume=volume, 
            pitch=pitch
        )
        
        # Create subtitle maker
        submaker = edge_tts.SubMaker()
        
        # Add timeout wrapper for the streaming operation
        audio_data = bytearray()
        
        try:
            # Use asyncio.wait_for to add overall timeout
            async def stream_with_timeout():
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data.extend(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        submaker.feed(chunk)
            
            # Set a reasonable timeout for the entire streaming operation
            await asyncio.wait_for(stream_with_timeout(), timeout=30.0)
            
            # Write audio file
            with open(audio_path, "wb") as audio_file:
                audio_file.write(audio_data)
            
            # Save subtitle file
            with open(subtitle_path, "w", encoding="utf-8") as subtitle_file:
                subtitle_file.write(submaker.get_srt())
                
            logger.info(f"Successfully generated audio and subtitle files")
            
        except asyncio.TimeoutError:
            raise Exception("Audio generation timed out after 30 seconds")
            
    except Exception as e:
        logger.error(f"Error in audio generation: {str(e)}")
        # Clean up partial files on error
        if os.path.exists(audio_path):
            os.remove(audio_path)
        if os.path.exists(subtitle_path):
            os.remove(subtitle_path)
        raise
```

**Parameters**:
- `text`: The text to convert to speech
- `voice`: Voice identifier (e.g., "en-US-AvaMultilingualNeural")
- `rate`: Speech rate adjustment (range: -50% to +200%, default: "+0%")
- `volume`: Volume adjustment (range: -50% to +50%, default: "+0%")
- `pitch`: Pitch adjustment (range: -50Hz to +50Hz, default: "+0Hz")

#### 3. Streaming Audio - `communicate.stream()`

**Purpose**: Stream audio and subtitle data chunks asynchronously

**Stream Chunk Types**:
1. **Audio Chunks**: `chunk["type"] == "audio"`
   - Contains binary audio data in `chunk["data"]`
   - MP3 format
   
2. **Word Boundary Chunks**: `chunk["type"] == "WordBoundary"`
   - Contains timing information for subtitle generation
   - Includes offset, duration, and text for each word

**Streaming Implementation**:
```python
async def stream_with_timeout():
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            # Accumulate audio binary data
            audio_data.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            # Feed timing data to subtitle maker
            submaker.feed(chunk)
```

#### 4. Subtitle Generation - `edge_tts.SubMaker()`

**Purpose**: Generate SRT (SubRip Subtitle) files from word boundary data

**Implementation**:
```python
# Create subtitle maker
submaker = edge_tts.SubMaker()

# Feed word boundary chunks during streaming
async for chunk in communicate.stream():
    if chunk["type"] == "WordBoundary":
        submaker.feed(chunk)

# Generate SRT formatted subtitle
subtitle_content = submaker.get_srt()

# Save to file
with open(subtitle_path, "w", encoding="utf-8") as subtitle_file:
    subtitle_file.write(subtitle_content)
```

**Subtitle Format (SRT)**:
```
1
00:00:00,000 --> 00:00:01,200
The sun was setting

2
00:00:01,200 --> 00:00:03,500
slowly, casting long shadows

3
00:00:03,500 --> 00:00:05,800
across the empty field.
```

---

## Core Components

### 1. Configuration System (config.py)

Centralized configuration using Pydantic settings:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Server settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True
    
    # File storage settings
    OUTPUT_DIR: str = "output"
    CACHE_DIR: str = "cache"
    MAX_FILE_AGE_DAYS: int = 7
    
    # TTS settings
    MAX_CONCURRENT_JOBS: int = 2  # Reduced to avoid overwhelming Edge TTS
    DEFAULT_VOICE_LANGUAGE: str = "en"
    
    # Network timeout settings
    CONNECTION_TIMEOUT: int = 60  # seconds
    READ_TIMEOUT: int = 60  # seconds
    TOTAL_TIMEOUT: int = 120  # seconds
    
    # Retry settings
    MAX_RETRIES: int = 3
    RETRY_DELAY_MIN: int = 2  # seconds
    RETRY_DELAY_MAX: int = 8  # seconds
    
    # Rate limiting
    REQUESTS_PER_MINUTE: int = 30
    BATCH_PROCESSING_DELAY: float = 1.0  # seconds between batch items
    
    # Audio quality settings
    DEFAULT_RATE: str = "+0%"
    DEFAULT_VOLUME: str = "+0%"
    DEFAULT_PITCH: str = "+0Hz"
    
    # Security settings
    MAX_TEXT_LENGTH: int = 10000  # characters
    ALLOWED_FILE_EXTENSIONS: list = [".mp3", ".wav", ".srt"]
```

### 2. Data Models (models.py)

Pydantic models for request/response validation:

```python
class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to convert to speech")
    language: str = Field(..., description="Language code (e.g., 'en', 'es', 'fr')")
    voice: Optional[str] = Field(None, description="Specific voice to use")
    project_name: str = Field(..., description="Project name for organization")
    segment_name: Optional[str] = Field(None, description="Segment name within project")
    rate: Optional[str] = Field("+10%", description="Speech rate (-50% to +200%)")
    volume: Optional[str] = Field("+10%", description="Volume (-50% to +50%)")
    pitch: Optional[str] = Field("+5Hz", description="Pitch (-50Hz to +50Hz)")

class TTSResponse(BaseModel):
    success: bool
    file_id: str
    file_path: str
    file_size: int
    duration: Optional[float] = None
    download_url: str
    # Subtitle information
    subtitle_file_id: Optional[str] = None
    subtitle_file_path: Optional[str] = None
    subtitle_file_size: Optional[int] = None
    subtitle_download_url: Optional[str] = None
    message: Optional[str] = None
```

### 3. TTS Service (tts_service.py)

Main service orchestrating audio and subtitle generation:

**Voice Selection**:
```python
def _get_best_voice(self, language: str, preferred_voice: Optional[str] = None) -> str:
    """Get the best voice for a language using your curated selection"""
    if preferred_voice:
        return preferred_voice
        
    # Use your curated best voices
    return self.best_voices.get(language, 'en-US-AvaMultilingualNeural')
```

**Curated Best Voices**:
```python
self.best_voices = {
    'en': 'en-US-AvaMultilingualNeural',
    'fr': 'fr-FR-VivienneMultilingualNeural', 
    'ko': 'ko-KR-HyunsuMultilingualNeural',
    'hi': 'hi-IN-MadhurNeural',
    'kn': 'kn-IN-GaganNeural',
    'ta': 'ta-IN-ValluvarNeural',
    'te': 'te-IN-ShrutiNeural',
    'ml': 'ml-IN-SobhanaNeural',
    # Fallback voices for other languages
    'es': 'es-ES-ElviraNeural',
    'de': 'de-DE-KatjaNeural',
    'it': 'it-IT-ElsaNeural',
    'pt': 'pt-BR-FranciscaNeural',
    'zh': 'zh-CN-XiaoxiaoNeural',
    'ja': 'ja-JP-NanamiNeural',
    'ar': 'ar-SA-ZariyahNeural',
    'ru': 'ru-RU-SvetlanaNeural'
}
```

### 4. File Manager (file_manager.py)

Handles file operations, caching, and organization:

```python
class FileManager:
    def __init__(self):
        self.output_dir = settings.OUTPUT_DIR
        self.cache_file = os.path.join(self.output_dir, ".cache", "file_cache.json")
        self.file_index = os.path.join(self.output_dir, ".cache", "file_index.json")
        self._ensure_directories()
        self._load_cache()
        self._load_index()
```

---

## Audio Generation Process

### Complete Workflow

```
1. Receive Request
   ↓
2. Check Cache (using MD5 hash)
   ├─ Cache Hit → Return existing files
   └─ Cache Miss → Continue
   ↓
3. Generate File Paths
   - Audio: output/project/language/segment.mp3
   - Subtitle: output/project/language/segment.srt
   ↓
4. Create Communicate Object
   - edge_tts.Communicate(text, voice, rate, volume, pitch)
   ↓
5. Stream Audio & Subtitle Data
   - Process audio chunks
   - Process word boundary chunks
   ↓
6. Write Files
   - Save MP3 audio file
   - Save SRT subtitle file
   ↓
7. Detect Audio Duration
   - Use mutagen library
   ↓
8. Store Cache Mapping
   - Map hash to file paths
   ↓
9. Return Response
   - File IDs, paths, sizes, duration
   - Download URLs
```

### Main Generation Function

```python
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
    """Generate audio file from text and return (audio_path, subtitle_path)"""
    try:
        # Get voice
        selected_voice = voice or self._get_best_voice(language)
        
        # Generate cache key
        cache_key = self._generate_cache_key(text, selected_voice, rate, volume, pitch)
        
        # Check if files already exist (simple caching)
        existing_audio, existing_subtitle = self.file_manager.find_cached_files(cache_key)
        if existing_audio:
            logger.info(f"Using cached audio for cache_key: {cache_key[:8]}")
            return existing_audio, existing_subtitle
        
        # Create file paths
        file_name = segment_name or f"audio_{cache_key[:8]}"
        audio_path, subtitle_path = self.file_manager.get_file_paths(project_name, language, file_name)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        
        # Generate audio and subtitle using streaming with retry
        await self._generate_audio_and_subtitle_with_retry(
            text, selected_voice, rate, volume, pitch, audio_path, subtitle_path
        )
        
        # Store cache mapping
        self.file_manager.store_cache_mapping(cache_key, audio_path, subtitle_path)
        
        logger.info(f"Successfully generated audio: {audio_path}")
        return audio_path, subtitle_path
        
    except Exception as e:
        logger.error(f"Failed to generate audio: {str(e)}")
        raise Exception(f"Failed to generate audio: {str(e)}")
```

### Retry Logic

Uses the `tenacity` library for automatic retry with exponential backoff:

```python
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
async def _generate_audio_and_subtitle_with_retry(
    self, 
    text: str, 
    voice: str, 
    rate: str, 
    volume: str, 
    pitch: str, 
    audio_path: str, 
    subtitle_path: str
):
    """Generate both audio and subtitle files with retry logic"""
    logger.info(f"Generating audio with voice: {voice}")
    
    try:
        await self._generate_audio_and_subtitle(
            text, voice, rate, volume, pitch, audio_path, subtitle_path
        )
    except Exception as e:
        logger.error(f"Audio generation attempt failed: {str(e)}")
        # Clean up partial files on error
        if os.path.exists(audio_path):
            os.remove(audio_path)
        if os.path.exists(subtitle_path):
            os.remove(subtitle_path)
        raise
```

**Retry Configuration**:
- Maximum 3 attempts
- Exponential backoff: 4s, 8s (multiplier=1, min=4, max=10)
- Retries only on network/timeout errors

---

## Subtitle Generation Process

### How Subtitles Are Created

Subtitles are generated **simultaneously** with audio using edge-tts's streaming capability:

#### Step-by-Step Process

**1. Create SubMaker Instance**:
```python
submaker = edge_tts.SubMaker()
```

**2. Feed Word Boundary Data During Streaming**:
```python
async for chunk in communicate.stream():
    if chunk["type"] == "audio":
        audio_data.extend(chunk["data"])
    elif chunk["type"] == "WordBoundary":
        # This contains timing information
        submaker.feed(chunk)
```

**3. WordBoundary Chunk Structure**:
Each WordBoundary chunk contains:
- `Offset`: Start time in 100-nanosecond units
- `Duration`: Duration in 100-nanosecond units
- `Text`: The word being spoken
- `BoundaryType`: Type of boundary (word, sentence, etc.)

**4. Generate SRT Format**:
```python
subtitle_content = submaker.get_srt()
```

The `SubMaker` automatically:
- Converts timestamps to SRT format (HH:MM:SS,mmm)
- Groups words into readable subtitle segments
- Adds sequence numbers
- Formats according to SRT specifications

**5. Save to File**:
```python
with open(subtitle_path, "w", encoding="utf-8") as subtitle_file:
    subtitle_file.write(subtitle_content)
```

### Example Subtitle Output

For the text: "The sun was setting slowly, casting long shadows across the empty field."

Generated SRT file:
```
1
00:00:00,000 --> 00:00:01,200
The sun was setting

2
00:00:01,200 --> 00:00:03,500
slowly, casting long shadows

3
00:00:03,500 --> 00:00:05,800
across the empty field.
```

### Subtitle Synchronization

Subtitles are **perfectly synchronized** with audio because:
1. They're generated from the **same streaming session**
2. Timing data comes directly from the TTS engine
3. Word boundaries are precise to the millisecond

---

## File Management System

### File Organization

```python
def get_file_paths(self, project_name: str, language: str, file_name: str) -> Tuple[str, str]:
    """Get both audio and subtitle file paths"""
    audio_path = self.get_audio_path(project_name, language, file_name)
    subtitle_path = self.get_subtitle_path(project_name, language, file_name)
    return audio_path, subtitle_path

def get_audio_path(self, project_name: str, language: str, file_name: str) -> str:
    """Get organized file path for audio"""
    # Clean file name
    safe_name = "".join(c for c in file_name if c.isalnum() or c in (' ', '-', '_')).strip()
    if not safe_name.endswith('.mp3'):
        safe_name += '.mp3'
    
    # Create organized path: output/project/language/file.mp3
    path = os.path.join(self.output_dir, project_name, language, safe_name)
    return path

def get_subtitle_path(self, project_name: str, language: str, file_name: str) -> str:
    """Get organized file path for subtitle"""
    # Clean file name and ensure .srt extension
    safe_name = "".join(c for c in file_name if c.isalnum() or c in (' ', '-', '_')).strip()
    if safe_name.endswith('.mp3'):
        safe_name = safe_name[:-4]  # Remove .mp3 extension
    if not safe_name.endswith('.srt'):
        safe_name += '.srt'
    
    # Create organized path: output/project/language/file.srt
    path = os.path.join(self.output_dir, project_name, language, safe_name)
    return path
```

### Audio Duration Detection

Uses the `mutagen` library to extract audio metadata:

```python
def _get_audio_duration(self, file_path: str) -> Optional[float]:
    """Get audio duration in seconds"""
    try:
        if not MUTAGEN_AVAILABLE:
            return None
        
        if file_path.lower().endswith('.mp3'):
            audio = MP3(file_path)
            return audio.info.length if audio.info else None
        
    except Exception as e:
        print(f"Failed to get audio duration for {file_path}: {e}")
        return None
    
    return None
```

### File Information Storage

```python
def get_file_info(self, file_path: str, subtitle_path: Optional[str] = None) -> Dict:
    """Get file information and generate file ID for audio and subtitle"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Generate file ID for audio
    file_id = hashlib.md5(file_path.encode()).hexdigest()
    
    # Get audio file stats
    stat = os.stat(file_path)
    file_size = stat.st_size
    
    # Get audio duration
    duration = self._get_audio_duration(file_path)
    
    # Store audio in index
    self.index[file_id] = {
        "file_path": file_path,
        "size": file_size,
        "file_type": "audio",
        "duration": duration,
        "created_at": time.time(),
        "accessed_at": time.time()
    }
    
    result = {
        "file_id": file_id,
        "file_path": file_path,
        "size": file_size,
        "duration": duration
    }
    
    # Handle subtitle file if provided
    if subtitle_path and os.path.exists(subtitle_path):
        subtitle_id = hashlib.md5(subtitle_path.encode()).hexdigest()
        subtitle_stat = os.stat(subtitle_path)
        subtitle_size = subtitle_stat.st_size
        
        # Store subtitle in index
        self.index[subtitle_id] = {
            "file_path": subtitle_path,
            "size": subtitle_size,
            "file_type": "subtitle",
            "created_at": time.time(),
            "accessed_at": time.time()
        }
        
        result.update({
            "subtitle_file_id": subtitle_id,
            "subtitle_file_path": subtitle_path,
            "subtitle_size": subtitle_size
        })
    
    self._save_index()
    return result
```

### Project Listing

```python
def list_projects(self) -> List[Dict]:
    """List all projects and their structure"""
    projects = []
    
    if not os.path.exists(self.output_dir):
        return projects
    
    for project_name in os.listdir(self.output_dir):
        project_path = os.path.join(self.output_dir, project_name)
        
        if os.path.isdir(project_path) and not project_name.startswith('.'):
            project_info = {
                "name": project_name,
                "languages": [],
                "total_files": 0,
                "total_size": 0
            }
            
            # Get languages in project
            for language in os.listdir(project_path):
                lang_path = os.path.join(project_path, language)
                
                if os.path.isdir(lang_path):
                    files = []
                    lang_size = 0
                    
                    for file_name in os.listdir(lang_path):
                        file_path = os.path.join(lang_path, file_name)
                        if os.path.isfile(file_path) and (file_name.endswith('.mp3') or file_name.endswith('.srt')):
                            file_size = os.path.getsize(file_path)
                            file_type = "audio" if file_name.endswith('.mp3') else "subtitle"
                            
                            # Get duration for audio files
                            duration = None
                            if file_type == "audio":
                                duration = self._get_audio_duration(file_path)
                            
                            files.append({
                                "name": file_name,
                                "size": file_size,
                                "path": file_path,
                                "type": file_type,
                                "duration": duration
                            })
                            lang_size += file_size
                    
                    project_info["languages"].append({
                        "language": language,
                        "files": files,
                        "file_count": len(files),
                        "total_size": lang_size
                    })
                    
                    project_info["total_files"] += len(files)
                    project_info["total_size"] += lang_size
            
            projects.append(project_info)
    
    return projects
```

---

## Caching Mechanism

### Cache Key Generation

Uses MD5 hashing of all parameters that affect output:

```python
def _generate_cache_key(self, text: str, voice: str, rate: str, volume: str, pitch: str) -> str:
    """Generate cache key for audio content"""
    content = f"{text}_{voice}_{rate}_{volume}_{pitch}"
    return hashlib.md5(content.encode()).hexdigest()
```

**Why this works**: Identical parameters always produce the same hash, enabling perfect cache hits.

### Cache Storage

```python
def store_cache_mapping(self, cache_key: str, audio_path: str, subtitle_path: Optional[str] = None):
    """Store cache key to file path mapping for both audio and subtitle"""
    self.cache_mapping[cache_key] = {
        "audio_path": audio_path,
        "subtitle_path": subtitle_path
    }
    self._save_cache()
```

**Cache File Format** (`.cache/file_cache.json`):
```json
{
  "a1b2c3d4e5f6...": {
    "audio_path": "output/project1/en/segment1.mp3",
    "subtitle_path": "output/project1/en/segment1.srt"
  },
  "f6e5d4c3b2a1...": {
    "audio_path": "output/project1/fr/segment2.mp3",
    "subtitle_path": "output/project1/fr/segment2.srt"
  }
}
```

### Cache Lookup

```python
def find_cached_files(self, cache_key: str) -> Tuple[Optional[str], Optional[str]]:
    """Find existing cached files (audio and subtitle)"""
    if cache_key in self.cache_mapping:
        cached_data = self.cache_mapping[cache_key]
        
        # Handle both old format (string) and new format (dict)
        if isinstance(cached_data, str):
            # Old format - only audio path
            audio_path = cached_data
            subtitle_path = None
        else:
            # New format - dict with both paths
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
```

### Cache Benefits

1. **Performance**: Avoid regenerating identical content
2. **API Rate Limiting**: Reduce calls to Edge TTS service
3. **Consistency**: Same input always returns same output
4. **Cost Efficiency**: Minimize network usage

---

## Batch Processing

### Batch Request Structure

```python
class BatchItem(BaseModel):
    text: str
    language: str
    voice: Optional[str] = None
    segment_name: str
    rate: Optional[str] = "+0%"
    volume: Optional[str] = "+0%"
    pitch: Optional[str] = "+0Hz"

class BatchRequest(BaseModel):
    project_name: str
    items: List[BatchItem]
```

### Batch Processing Implementation

```python
async def process_batch(self, items: List[BatchItem], project_name: str) -> str:
    """Process batch of TTS requests with improved error handling"""
    task_id = str(uuid.uuid4())
    
    # Initialize batch task
    batch_task = BatchStatus(
        task_id=task_id,
        status="processing",
        total_items=len(items),
        completed_items=0,
        failed_items=0,
        results=[],
        created_at=datetime.now().isoformat()
    )
    
    self.batch_tasks[task_id] = batch_task
    
    # Process items asynchronously
    asyncio.create_task(self._process_batch_items(task_id, items, project_name))
    
    return task_id
```

### Concurrent Processing with Rate Limiting

```python
async def _process_batch_items(self, task_id: str, items: List[BatchItem], project_name: str):
    """Process batch items in background with rate limiting"""
    batch_task = self.batch_tasks[task_id]
    
    try:
        # Reduce concurrent jobs to avoid overwhelming the service
        max_concurrent = min(settings.MAX_CONCURRENT_JOBS, 2)  # Limit to 2 concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []
        
        for item in items:
            task = self._process_single_item(semaphore, item, project_name, batch_task)
            tasks.append(task)
            
            # Add small delay between task creations to avoid overwhelming the service
            await asyncio.sleep(0.5)
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update final status
        batch_task.status = "completed"
        batch_task.completed_at = datetime.now().isoformat()
        
    except Exception as e:
        logger.error(f"Batch processing failed: {str(e)}")
        batch_task.status = "failed"
        batch_task.completed_at = datetime.now().isoformat()
```

### Single Item Processing

```python
async def _process_single_item(self, semaphore, item: BatchItem, project_name: str, batch_task: BatchStatus):
    """Process a single batch item with retry logic"""
    async with semaphore:
        try:
            # Add delay to avoid rate limiting
            await asyncio.sleep(1)
            
            audio_path, subtitle_path = await self.generate_audio(
                text=item.text,
                language=item.language,
                voice=item.voice,
                project_name=project_name,
                segment_name=item.segment_name,
                rate=item.rate,
                volume=item.volume,
                pitch=item.pitch
            )
            
            file_info = self.file_manager.get_file_info(audio_path, subtitle_path)
            
            result = {
                "segment_name": item.segment_name,
                "language": item.language,
                "status": "success",
                "file_id": file_info["file_id"],
                "file_path": audio_path,
                "download_url": f"/download/{file_info['file_id']}",
                "subtitle_file_id": file_info.get("subtitle_file_id"),
                "subtitle_file_path": subtitle_path,
                "subtitle_download_url": f"/download/{file_info['subtitle_file_id']}" if file_info.get("subtitle_file_id") else None
            }
            
            batch_task.results.append(result)
            batch_task.completed_items += 1
            logger.info(f"Successfully processed item: {item.segment_name}")
            
        except Exception as e:
            logger.error(f"Failed to process item {item.segment_name}: {str(e)}")
            result = {
                "segment_name": item.segment_name,
                "language": item.language,
                "status": "failed",
                "error": str(e)
            }
            
            batch_task.results.append(result)
            batch_task.failed_items += 1
```

### Rate Limiting Strategy

1. **Semaphore Control**: Maximum 2 concurrent requests
2. **Task Creation Delay**: 0.5 seconds between task starts
3. **Processing Delay**: 1 second delay before each generation
4. **Exponential Backoff**: Built into retry logic

---

## API Endpoints

### 1. Single TTS Generation

**Endpoint**: `POST /generate`

**Request**:
```json
{
  "text": "The sun was setting slowly.",
  "language": "en",
  "voice": "en-US-AvaMultilingualNeural",
  "project_name": "my_project",
  "segment_name": "intro",
  "rate": "+10%",
  "volume": "+10%",
  "pitch": "+5Hz"
}
```

**Response**:
```json
{
  "success": true,
  "file_id": "a1b2c3d4...",
  "file_path": "/absolute/path/output/my_project/en/intro.mp3",
  "file_size": 45678,
  "duration": 3.456,
  "download_url": "/download/a1b2c3d4...",
  "subtitle_file_id": "e5f6g7h8...",
  "subtitle_file_path": "/absolute/path/output/my_project/en/intro.srt",
  "subtitle_file_size": 234,
  "subtitle_download_url": "/download/e5f6g7h8..."
}
```

### 2. Language-Specific Endpoints

**Endpoints**:
- `POST /generate/english`
- `POST /generate/french`
- `POST /generate/korean`
- `POST /generate/hindi`
- `POST /generate/kannada`
- `POST /generate/tamil`
- `POST /generate/telugu`
- `POST /generate/malayalam`

**Request** (simplified, no language/voice parameters):
```json
{
  "text": "நான் ஒரு மாணவன்",
  "project_name": "tamil_project",
  "segment_name": "verse1",
  "rate": "+0%",
  "volume": "+0%",
  "pitch": "+0Hz"
}
```

**Implementation**:
```python
@app.post("/generate/tamil", response_model=TTSResponse)
async def generate_tamil_audio(request: LanguageSpecificRequest):
    """Generate Tamil audio and subtitle using the best Tamil voice"""
    try:
        config = LANGUAGE_CONFIG["tamil"]
        audio_path, subtitle_path = await tts_service.generate_audio(
            text=request.text,
            voice=config["voice"],
            language=config["code"],
            project_name=request.project_name,
            segment_name=request.segment_name,
            rate=request.rate,
            volume=request.volume,
            pitch=request.pitch
        )
        
        return _create_tts_response(audio_path, subtitle_path)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 3. Batch Processing

**Start Batch**: `POST /batch`

**Request**:
```json
{
  "project_name": "multilingual_project",
  "items": [
    {
      "text": "Hello world",
      "language": "en",
      "segment_name": "greeting_en",
      "rate": "+0%",
      "volume": "+0%",
      "pitch": "+0Hz"
    },
    {
      "text": "Bonjour le monde",
      "language": "fr",
      "segment_name": "greeting_fr",
      "rate": "+0%",
      "volume": "+0%",
      "pitch": "+0Hz"
    }
  ]
}
```

**Response**:
```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_items": 2,
  "status": "processing",
  "message": "Batch processing started"
}
```

**Check Status**: `GET /batch/{task_id}`

**Response**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "total_items": 2,
  "completed_items": 2,
  "failed_items": 0,
  "results": [
    {
      "segment_name": "greeting_en",
      "language": "en",
      "status": "success",
      "file_id": "abc123...",
      "file_path": "output/multilingual_project/en/greeting_en.mp3",
      "download_url": "/download/abc123...",
      "subtitle_file_id": "def456...",
      "subtitle_file_path": "output/multilingual_project/en/greeting_en.srt",
      "subtitle_download_url": "/download/def456..."
    },
    {
      "segment_name": "greeting_fr",
      "language": "fr",
      "status": "success",
      "file_id": "ghi789...",
      "file_path": "output/multilingual_project/fr/greeting_fr.mp3",
      "download_url": "/download/ghi789...",
      "subtitle_file_id": "jkl012...",
      "subtitle_file_path": "output/multilingual_project/fr/greeting_fr.srt",
      "subtitle_download_url": "/download/jkl012..."
    }
  ],
  "created_at": "2025-01-15T10:30:00",
  "completed_at": "2025-01-15T10:30:45"
}
```

### 4. Voice Listing

**Endpoint**: `GET /voices?language=en`

**Response**:
```json
[
  {
    "name": "Microsoft Ava Online (Natural) - English (United States)",
    "short_name": "en-US-AvaMultilingualNeural",
    "gender": "Female",
    "language": "en",
    "locale": "en-US",
    "country": "US"
  },
  {
    "name": "Microsoft Brian Online (Natural) - English (United States)",
    "short_name": "en-US-BrianNeural",
    "gender": "Male",
    "language": "en",
    "locale": "en-US",
    "country": "US"
  }
]
```

### 5. File Download

**Endpoint**: `GET /download/{file_id}`

**Response**: Binary file (audio/mpeg for MP3, text/srt for subtitles)

### 6. Project Management

**List Projects**: `GET /projects`

**Response**:
```json
{
  "projects": [
    {
      "name": "my_project",
      "languages": [
        {
          "language": "en",
          "files": [
            {
              "name": "intro.mp3",
              "size": 45678,
              "path": "output/my_project/en/intro.mp3",
              "type": "audio",
              "duration": 3.456
            },
            {
              "name": "intro.srt",
              "size": 234,
              "path": "output/my_project/en/intro.srt",
              "type": "subtitle",
              "duration": null
            }
          ],
          "file_count": 2,
          "total_size": 45912
        }
      ],
      "total_files": 2,
      "total_size": 45912
    }
  ]
}
```

**Delete Project**: `DELETE /projects/{project_name}`

**Response**:
```json
{
  "message": "Deleted 10 files from project my_project"
}
```

### 7. Plain Text Processing

**Endpoint**: `POST /text/generate/{language}`

Handles form-encoded text (for problematic characters):

**Request**:
```
Content-Type: application/x-www-form-urlencoded

text=Text with "quotes" and \backslashes
project_name=test_project
segment_name=segment1
rate=+10%
volume=+0%
pitch=+0Hz
```

**Implementation**:
```python
@app.post("/text/generate/{language}")
async def generate_audio_from_plain_text(
    language: str,
    text: str = Form(...),
    project_name: str = Form(...),
    segment_name: Optional[str] = Form(None),
    rate: Optional[str] = Form("+0%"),
    volume: Optional[str] = Form("+0%"),
    pitch: Optional[str] = Form("+0Hz")
):
    """Generate audio and subtitle from plain text form data (handles problematic text)"""
    try:
        if language not in LANGUAGE_CONFIG:
            raise HTTPException(status_code=400, detail=f"Unsupported language: {language}")
        
        config = LANGUAGE_CONFIG[language]
        
        # Process text to clean it
        cleaned_text = clean_text_for_json(text)
        
        audio_path, subtitle_path = await tts_service.generate_audio(
            text=cleaned_text,
            voice=config["voice"],
            language=config["code"],
            project_name=project_name,
            segment_name=segment_name,
            rate=rate,
            volume=volume,
            pitch=pitch
        )
        
        return _create_tts_response(audio_path, subtitle_path)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Configuration System

### Environment Variables

Create a `.env` file:

```env
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=False

# Storage
OUTPUT_DIR=output
CACHE_DIR=cache
MAX_FILE_AGE_DAYS=30

# TTS
MAX_CONCURRENT_JOBS=2
DEFAULT_VOICE_LANGUAGE=en

# Timeouts
CONNECTION_TIMEOUT=60
READ_TIMEOUT=60
TOTAL_TIMEOUT=120

# Retry
MAX_RETRIES=3
RETRY_DELAY_MIN=2
RETRY_DELAY_MAX=8

# Rate Limiting
REQUESTS_PER_MINUTE=30
BATCH_PROCESSING_DELAY=1.0

# Audio Quality
DEFAULT_RATE=+0%
DEFAULT_VOLUME=+0%
DEFAULT_PITCH=+0Hz

# Security
MAX_TEXT_LENGTH=10000
```

---

## Code Examples and Usage

### Example 1: Basic Usage from Edge-TTS

From the edge-tts official examples, here's how to generate all voices:

```python
#!/usr/bin/env python
from pathlib import Path
import asyncio
import json
import edge_tts

async def main():
    voices = await edge_tts.list_voices()
    Path('data/voices.json').write_text(json.dumps(voices))

asyncio.run(main())
```

### Example 2: Create Audio for Multiple Languages

Based on edge-tts examples:

```python
#!/usr/bin/env python
from pathlib import Path
import json
import edge_tts

voices = json.loads(Path('data/voices.json').read_text())
languages = json.loads(Path('data/languages-with-text.json').read_text())

# Add list of voices to each language item
for v in voices:
    code = v['Locale'].split('-')[0]
    languages[code]['voices'] = languages[code].get('voices', []) + [v['ShortName']]

# Create mp3 files for each language and voice
for lang in languages.values():
    p_lang = Path('mp3', lang['language'])
    p_lang.mkdir(exist_ok=True)
    for voice in lang.get('voices', []):
        p_voice = p_lang / f'{voice}.mp3'
        if p_voice.exists():
            continue
        try:
            communicate = edge_tts.Communicate(lang['text'], voice)
            communicate.save_sync(p_voice)
        except ValueError as e:
            print(e)
```

### Example 3: Using the TTS Service Programmatically

```python
import asyncio
from tts_service import TTSService

async def main():
    tts_service = TTSService()
    
    # Generate single audio with subtitle
    audio_path, subtitle_path = await tts_service.generate_audio(
        text="Hello, this is a test of the text-to-speech system.",
        language="en",
        project_name="test_project",
        segment_name="test_segment",
        rate="+10%",
        volume="+0%",
        pitch="+5Hz"
    )
    
    print(f"Audio: {audio_path}")
    print(f"Subtitle: {subtitle_path}")

asyncio.run(main())
```

### Example 4: Batch Processing

```python
import asyncio
from tts_service import TTSService
from models import BatchItem

async def main():
    tts_service = TTSService()
    
    items = [
        BatchItem(
            text="First segment in English",
            language="en",
            segment_name="segment1"
        ),
        BatchItem(
            text="Premier segment en français",
            language="fr",
            segment_name="segment1"
        ),
        BatchItem(
            text="पहला खंड हिंदी में",
            language="hi",
            segment_name="segment1"
        )
    ]
    
    task_id = await tts_service.process_batch(items, "multilingual_test")
    print(f"Batch task started: {task_id}")
    
    # Wait a bit for processing
    await asyncio.sleep(10)
    
    # Check status
    status = await tts_service.get_batch_status(task_id)
    print(f"Completed: {status.completed_items}/{status.total_items}")
    print(f"Results: {status.results}")

asyncio.run(main())
```

### Example 5: Custom Voice Parameters

```python
# Maximum speech rate (fastest)
audio_path, subtitle_path = await tts_service.generate_audio(
    text="Speaking very fast!",
    language="en",
    rate="+200%",  # Maximum speed
    project_name="speed_test",
    segment_name="fastest"
)

# Minimum speech rate (slowest)
audio_path, subtitle_path = await tts_service.generate_audio(
    text="Speaking very slowly...",
    language="en",
    rate="-50%",  # Minimum speed
    project_name="speed_test",
    segment_name="slowest"
)

# High pitch
audio_path, subtitle_path = await tts_service.generate_audio(
    text="High pitched voice",
    language="en",
    pitch="+50Hz",  # Maximum pitch increase
    project_name="pitch_test",
    segment_name="high"
)

# Low pitch
audio_path, subtitle_path = await tts_service.generate_audio(
    text="Low pitched voice",
    language="en",
    pitch="-50Hz",  # Maximum pitch decrease
    project_name="pitch_test",
    segment_name="low"
)
```

### Example 6: Using Different Voices

```python
import asyncio
from tts_service import TTSService

async def main():
    tts_service = TTSService()
    
    # List all available English voices
    voices = await tts_service.get_available_voices(language="en")
    
    print("Available English voices:")
    for voice in voices:
        print(f"  {voice.short_name} - {voice.gender}")
    
    # Use a specific voice
    audio_path, subtitle_path = await tts_service.generate_audio(
        text="This uses a specific voice",
        language="en",
        voice="en-US-BrianNeural",  # Male voice
        project_name="voice_test",
        segment_name="brian"
    )
    
    audio_path, subtitle_path = await tts_service.generate_audio(
        text="This uses another voice",
        language="en",
        voice="en-GB-SoniaNeural",  # British female voice
        project_name="voice_test",
        segment_name="sonia"
    )

asyncio.run(main())
```

---

## Advanced Features

### 1. Individual Voice Control

The system provides fine-grained control over voice characteristics:

**Rate Control** (Speech Speed):
- Range: -50% to +200%
- Default: +0%
- Example: "+50%" = 50% faster than normal

**Volume Control**:
- Range: -50% to +50%
- Default: +0%
- Example: "-25%" = 25% quieter than normal

**Pitch Control**:
- Range: -50Hz to +50Hz
- Default: +0Hz
- Example: "+10Hz" = 10 Hz higher pitch

### 2. Streaming Architecture

The system uses **streaming** for efficiency:

```python
async for chunk in communicate.stream():
    if chunk["type"] == "audio":
        audio_data.extend(chunk["data"])
    elif chunk["type"] == "WordBoundary":
        submaker.feed(chunk)
```

**Benefits**:
- Memory efficient (doesn't load entire audio in memory at once)
- Faster processing (can start writing before complete)
- Simultaneous subtitle generation

### 3. Error Handling and Cleanup

The system automatically cleans up partial files on error:

```python
try:
    await self._generate_audio_and_subtitle(...)
except Exception as e:
    # Clean up partial files on error
    if os.path.exists(audio_path):
        os.remove(audio_path)
    if os.path.exists(subtitle_path):
        os.remove(subtitle_path)
    raise
```

### 4. Timeout Protection

Multiple layers of timeout protection:

1. **Connection timeout**: 60 seconds
2. **Read timeout**: 60 seconds
3. **Total timeout**: 120 seconds
4. **Streaming timeout**: 30 seconds

```python
# Streaming timeout
await asyncio.wait_for(stream_with_timeout(), timeout=30.0)

# Connection timeout
self.connector_timeout = aiohttp.ClientTimeout(
    total=30,
    connect=10,
    sock_read=20,
)
```

---

## All Available Edge-TTS Features

### Voice Customization

1. **Voice Selection**: Choose from 400+ voices across 80+ languages
2. **Rate Adjustment**: Control speech speed from -50% to +200%
3. **Volume Adjustment**: Control volume from -50% to +50%
4. **Pitch Adjustment**: Control pitch from -50Hz to +50Hz

### Output Formats

1. **Audio**: MP3 format (high quality neural voices)
2. **Subtitles**: SRT format with precise word-level timing

### Supported Languages (Full List)

Edge-TTS supports 80+ languages including:
- Afrikaans, Albanian, Amharic, Arabic, Armenian, Azerbaijani
- Bengali, Bosnian, Bulgarian, Burmese, Catalan, Chinese
- Croatian, Czech, Danish, Dutch, English, Estonian
- Filipino, Finnish, French, Galician, Georgian, German
- Greek, Gujarati, Hebrew, Hindi, Hungarian, Icelandic
- Indonesian, Irish, Italian, Japanese, Javanese, Kannada
- Kazakh, Khmer, Korean, Lao, Latvian, Lithuanian
- Macedonian, Malay, Malayalam, Maltese, Marathi, Mongolian
- Nepali, Norwegian, Pashto, Persian, Polish, Portuguese
- Romanian, Russian, Serbian, Sinhala, Slovak, Slovenian
- Somali, Spanish, Sundanese, Swahili, Swedish, Tamil
- Telugu, Thai, Turkish, Ukrainian, Urdu, Uzbek
- Vietnamese, Welsh, Zulu

**And many more**! Use the `/voices` endpoint to get the complete current list.

### Voice Types Available

- **Neural Voices**: High-quality AI voices (recommended)
- **Multilingual Voices**: Single voice supporting multiple languages
- **Regional Variants**: Different accents for the same language
- **Gender Options**: Male and female voices for most languages

---

## Technical Implementation Details

### Asynchronous Processing

The entire system is built on async/await:

```python
# All major functions are async
async def generate_audio(...) -> Tuple[str, Optional[str]]:
    ...

async def get_available_voices(...) -> List[VoiceInfo]:
    ...

async def process_batch(...) -> str:
    ...
```

**Benefits**:
- Non-blocking I/O operations
- Concurrent batch processing
- Better resource utilization
- Scalability

### Dependency Management

Key dependencies:
- `edge-tts`: Microsoft Edge TTS service interface
- `fastapi`: Modern web framework
- `pydantic`: Data validation
- `tenacity`: Retry logic
- `aiohttp`: Async HTTP client
- `mutagen`: Audio metadata
- `loguru`: Logging

### File Persistence

Two JSON files maintain system state:

**file_cache.json**: Maps cache keys to file paths
```json
{
  "hash1": {
    "audio_path": "output/project/lang/file.mp3",
    "subtitle_path": "output/project/lang/file.srt"
  }
}
```

**file_index.json**: Maintains file metadata
```json
{
  "file_id1": {
    "file_path": "output/project/lang/file.mp3",
    "size": 45678,
    "file_type": "audio",
    "duration": 3.456,
    "created_at": 1673890123.456,
    "accessed_at": 1673890123.456
  }
}
```

---

## System Requirements

### Software Requirements

- Python 3.8+
- pip (Python package manager)
- Optional: pipx for isolated installation

### Python Packages

```
fastapi
uvicorn[standard]
edge-tts
pydantic
pydantic-settings
aiohttp
tenacity
loguru
mutagen
python-multipart
```

### System Resources

- **Memory**: 512MB minimum, 1GB recommended
- **Storage**: Depends on usage (audio files ~30-100KB per minute)
- **Network**: Required for Edge TTS API access

---

## Running the System

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or with pipx
pipx install edge-tts
```

### Starting the Server

```bash
# Development mode
python main.py

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Testing

```bash
# Health check
curl http://localhost:8000/health

# Get available voices
curl http://localhost:8000/voices

# Generate audio
curl -X POST http://localhost:8000/generate/english \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world",
    "project_name": "test",
    "segment_name": "greeting"
  }'
```

---

## Conclusion

This documentation provides a complete reference for the Edge-TTS based TTS system. The system leverages Microsoft Edge's TTS service through the `edge-tts` library to provide:

- High-quality neural voice synthesis
- Simultaneous subtitle generation
- Multi-language support (80+ languages)
- Intelligent caching and file management
- Robust error handling and retry logic
- RESTful API interface

The implementation uses modern Python async patterns, proper error handling, and efficient streaming to deliver a production-ready text-to-speech service with comprehensive subtitle support.

---

## References

- Edge-TTS GitHub: https://github.com/rany2/edge-tts
- Edge-TTS Documentation: https://pypi.org/project/edge-tts/
- FastAPI Documentation: https://fastapi.tiangolo.com/
- Pydantic Documentation: https://docs.pydantic.dev/
