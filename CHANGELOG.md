# Changelog

All notable changes to TermiVoxed will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-11-13

### Added

#### Core Features

- **Console-based video editor** with interactive TUI using Rich library
- **AI voice-over generation** powered by Microsoft Edge TTS
  - 200+ voices across 80+ languages
  - Interactive voice selection with audio preview
  - Voice caching for faster regeneration
- **Advanced subtitle system** with ASS format support
  - Full font customization via Google Fonts integration
  - Automatic font download and installation
  - Color, size, and position controls
  - Border and outline styling options
  - Shadow effects
  - Language-specific font selection
- **Video processing pipeline** using FFmpeg
  - Segment-based editing
  - Audio mixing (video audio + voice-over)
  - Automatic audio/video synchronization
  - Smart segment extension for audio fitting
  - Background music with looping and fade effects
- **Project management system**
  - JSON-based project storage
  - Save and resume projects
  - Project statistics and metadata

#### User Interface

- **Interactive voice selector** with:
  - Arrow key navigation
  - Voice preview with audio playback
  - Action menu (preview, select, go back)
  - Beautiful table display of available voices
- **Language selection** with interactive list
- **Subtitle styling dialog** with comprehensive options
- **Progress tracking** during export
- **Error handling and validation**

#### Development & Deployment

- **Cross-platform support** (Windows, macOS, Linux)
- **Automated setup scripts**:
  - `setup.sh` for Unix/Linux/macOS
  - `setup.bat` for Windows Command Prompt
  - `setup.ps1` for Windows PowerShell
- **Run scripts** for easy launching
- **Dependency checker** (`check_dependencies.py`)
- **Docker support**:
  - Dockerfile for containerization
  - docker-compose.yml for orchestration
  - .dockerignore for optimized builds
- **Python package configuration**:
  - pyproject.toml (modern packaging)
  - setup.py (backward compatibility)
  - MANIFEST.in for package data
  - Entry points: `termivoxed` and `cvd`
- **Development tools**:
  - requirements.txt for production dependencies
  - requirements-dev.txt for development
  - Black, flake8, mypy, isort configurations

#### Documentation

- Comprehensive README.md with installation guides
- CONTRIBUTING.md with contribution guidelines
- QUICK_START.md for rapid onboarding
- PROJECT_SUMMARY.md for project overview
- Reference documentation for FFmpeg and TTS patterns
- GNU AGPL v3 LICENSE for source code protection

### Features in Detail

#### Subtitle Border Controls

- Enable/disable borders and outlines
- Border style options:
  - Outline with shadow
  - Outline only
  - Opaque box background
- Adjustable border width/thickness
- Custom border colors (ASS color format)
- Shadow distance control
- Automatic background box for text visibility when borders disabled

#### Font Management

- Google Fonts API integration
- Automatic font download from Google Fonts
- Cross-platform font installation
- Font caching to avoid re-downloading
- Verification of font availability before export

#### Audio Processing

- TTS audio generation with edge-tts
- Audio caching system
- Retry logic for network failures
- Volume adjustment (TTS boost, BGM reduction)
- Audio mixing with FFmpeg filters
- Fade effects for background music

#### Video Export

- Quality presets (lossless, high, balanced)
- CRF-based encoding
- Segment extraction and processing
- Video concatenation
- Progress callbacks during export
- Automatic cleanup of temporary files

### Technical Details

#### Architecture

- Modular design with clear separation of concerns:
  - `backend/` - FFmpeg, TTS, subtitle utilities
  - `core/` - Export pipeline orchestration
  - `models/` - Data models (Project, Segment, Timeline)
  - `utils/` - Font manager, logger, voice selector
- Pydantic-based configuration management
- Async/await patterns for TTS operations
- Loguru for structured logging

#### Dependencies

- Python 3.8+ required
- FFmpeg and FFprobe required
- Key libraries:
  - textual, rich - TUI framework
  - edge-tts - Text-to-speech
  - pydantic - Data validation
  - loguru - Logging
  - inquirer - Interactive prompts
  - pygame - Audio playback
  - aiohttp - Async HTTP
  - tenacity - Retry logic

### Fixed

#### Subtitle Rendering Issues

- Fixed subtitle visibility when borders disabled
  - Previously: White text with no outline became invisible
  - Now: Uses opaque box background (borderstyle=3) for visibility
- Fixed hardcoded paths for cross-platform compatibility
  - Logger now uses Path objects instead of string concatenation
- Fixed main() entry point for package installation
  - Added sync wrapper for async_main() for console scripts

#### Voice Selection UX

- Fixed language selection to use interactive list instead of free-form text
- Fixed invalid language code validation in edit segment
- Fixed voice preview flow to stay at action menu after preview
- Fixed voice selector to display ALL voices (not just first 10)

#### Font Issues

- Fixed Google Fonts not being used in exported videos
  - Previously: System selected fonts but never installed them
  - Now: Automatic download and installation before export

### Known Issues

- Voice preview may fail for some voices due to edge-tts API availability
  - Workaround: Voice selection still works without preview
- pygame mixer may have audio playback issues on some systems
  - Workaround: Update pygame or continue without preview

### Security

- GNU AGPL v3 license applied
  - Protects against unauthorized commercial use
  - Requires derivative works to be open-source
  - Ensures attribution to original author

### Credits

- **Author**: Santhosh T
- **Development Assistance**: Claude (Anthropic)
- **Technologies**: Python, FFmpeg, Edge-TTS, Rich, Textual, Pydantic, Loguru

---

## [Unreleased]

### Planned Features

- Comprehensive test suite (pytest)
- GUI version (Textual TUI)
- Batch export functionality
- Video trimming and cutting
- Transition effects
- Audio effects (normalization, EQ)
- More subtitle formats (WebVTT, SBV)
- Theme customization
- Plugin system

---

[1.0.0]: https://github.com/santhosht/termivoxed/releases/tag/v1.0.0
