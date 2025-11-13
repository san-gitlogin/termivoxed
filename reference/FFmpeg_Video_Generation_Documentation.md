# FFmpeg Video Generation System - Complete Documentation

## Overview

This documentation provides a comprehensive guide to the FFmpeg commands and techniques used in two Python-based video generation systems:

1. **cl_vid_gen.py** - Vertical/Portrait format video generator with thumbnail frames
2. **cl_vid_gen_2.py** - Horizontal/Landscape format video merger

Both systems utilize FFmpeg for lossless quality video generation, proper audio syncing, subtitle burning, and background music addition.

---

## Table of Contents

1. [Core FFmpeg Utilities](#core-ffmpeg-utilities)
2. [Subtitle Processing](#subtitle-processing)
3. [Vertical Video Generation (cl_vid_gen.py)](#vertical-video-generation)
4. [Horizontal Video Generation (cl_vid_gen_2.py)](#horizontal-video-generation)
5. [Background Music Integration](#background-music-integration)
6. [Quality Control & Individual Control](#quality-control--individual-control)

---

## Core FFmpeg Utilities

### 1. Media Duration Detection

**Purpose:** Get the duration of any media file (video/audio) using ffprobe.

**Code Block:**
```python
def get_media_duration(self, file_path: str) -> Optional[float]:
    """Get media file duration using ffprobe"""
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', 
               '-of', 'csv=p=0', file_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return float(result.stdout.strip())
        return None
    except FileNotFoundError:
        logger.error("Error: ffprobe not found. Please install ffmpeg (which includes ffprobe).")
        return None
    except Exception as e:
        logger.error(f"Error getting duration: {e}")
        return None
```

**FFmpeg Command:**
```bash
ffprobe -v quiet -show_entries format=duration -of csv=p=0 <file_path>
```

**Parameters:**
- `-v quiet`: Suppress verbose output
- `-show_entries format=duration`: Only show duration from format metadata
- `-of csv=p=0`: Output as CSV without header

**Individual Control:** You can query any media file's duration independently before processing.

---

### 2. Audio Stream Detection

**Purpose:** Check if a video file contains an audio stream.

**Code Block:**
```python
def has_audio_stream(self, video_path: str) -> bool:
    """Check if a video file has an audio stream"""
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-select_streams', 'a', '-show_entries', 
               'stream=codec_type', '-of', 'csv=p=0', video_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0 and 'audio' in result.stdout
    except Exception as e:
        logger.warning(f"⚠️ Could not determine audio stream info for {video_path}: {e}")
        return False
```

**FFmpeg Command:**
```bash
ffprobe -v quiet -select_streams a -show_entries stream=codec_type -of csv=p=0 <video_path>
```

**Parameters:**
- `-select_streams a`: Select only audio streams
- `-show_entries stream=codec_type`: Show codec type of the stream

**Individual Control:** Determine audio presence before deciding on mixing strategy.

---

### 3. Video Specification Verification

**Purpose:** Verify video resolution, pixel format, and codec consistency.

**Code Block (from cl_vid_gen_2.py):**
```python
def verify_video_consistency(self, video_list: List[str]) -> bool:
    """Verify all videos have consistent resolution and format before concatenation"""
    logger.info("🔍 Verifying video consistency before concatenation...")
    
    resolutions = []
    for video_path in video_list:
        cmd = [
            'ffprobe', '-v', 'quiet', '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,pix_fmt,codec_name',
            '-of', 'csv=p=0', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            info = result.stdout.strip().split(',')
            if len(info) >= 4:
                width, height, pix_fmt, codec = info[:4]
                resolutions.append(f"{width}x{height} {pix_fmt} {codec}")
                logger.info(f"📐 {os.path.basename(video_path)}: {width}x{height} {pix_fmt} {codec}")
```

**FFmpeg Command:**
```bash
ffprobe -v quiet -select_streams v:0 -show_entries stream=width,height,pix_fmt,codec_name -of csv=p=0 <video_path>
```

**Parameters:**
- `-select_streams v:0`: Select first video stream
- `-show_entries stream=width,height,pix_fmt,codec_name`: Get video specifications

**Individual Control:** Pre-validate videos before concatenation to ensure compatibility.

---

## Subtitle Processing

### 1. SRT to ASS Conversion

**Purpose:** Convert SRT (SubRip) subtitle files to ASS (Advanced SubStation Alpha) format for advanced styling.

**Code Block:**
```python
def convert_srt_to_ass(srt_path, ass_path):
    """Convert SRT subtitle file to ASS format using ffmpeg"""
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', srt_path,
        '-y',  # Overwrite output file if exists
        ass_path
    ]
    
    try:
        logger.info(f"Converting SRT to ASS: {srt_path} -> {ass_path}")
        process = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("✅ SRT to ASS conversion completed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error("❌ Error occurred during SRT to ASS conversion:")
        logger.error(f"Return code: {e.returncode}")
        logger.error(f"Error output: {e.stderr}")
        return False
```

**FFmpeg Command:**
```bash
ffmpeg -i <srt_path> -y <ass_path>
```

**Parameters:**
- `-i <srt_path>`: Input SRT file
- `-y`: Overwrite output file if it exists
- `<ass_path>`: Output ASS file path

**How It Works:** FFmpeg automatically detects the input format (SRT) and converts it to the output format (ASS) based on file extension.

---

### 2. Custom ASS Styling

**Purpose:** Apply custom styling to ASS subtitle files for better readability and aesthetics.

**Code Block:**
```python
def create_custom_ass_style(srt_path, ass_path, style_options=None):
    """Convert SRT to ASS with custom styling"""
    default_style = {
        'fontname': 'Noto Sans Tamil',
        'fontsize': '20',
        'primarycolour': '&H00FFFFFF',  # White
        'secondarycolour': '&H000000FF',  # Red
        'outlinecolour': '&H00000000',  # Black outline
        'backcolour': '&H80000000',  # Semi-transparent black background
        'bold': '-1',
        'italic': '0',
        'underline': '0',
        'strikeout': '0',
        'scalex': '100',
        'scaley': '100',
        'spacing': '0',
        'angle': '0',
        'borderstyle': '1',
        'outline': '1',
        'shadow': '0',
        'alignment': '2',  # Bottom center
        'marginl': '10',
        'marginr': '10',
        'marginv': '10'
    }
    
    if style_options:
        default_style.update(style_options)
    
    # First convert SRT to basic ASS
    if not convert_srt_to_ass(srt_path, ass_path):
        return False
    
    # Read the generated ASS file
    try:
        with open(ass_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace the default style with custom style
        style_line = (
            f"Style: Default,{default_style['fontname']},{default_style['fontsize']},"
            f"{default_style['primarycolour']},{default_style['secondarycolour']},"
            f"{default_style['outlinecolour']},{default_style['backcolour']},"
            f"{default_style['bold']},{default_style['italic']},{default_style['underline']},"
            f"{default_style['strikeout']},{default_style['scalex']},{default_style['scaley']},"
            f"{default_style['spacing']},{default_style['angle']},{default_style['borderstyle']},"
            f"{default_style['outline']},{default_style['shadow']},{default_style['alignment']},"
            f"{default_style['marginl']},{default_style['marginr']},{default_style['marginv']},0"
        )
        
        # Find and replace the style line
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('Style: Default,'):
                lines[i] = style_line
                break
        
        # Write back the modified content
        with open(ass_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        logger.info("✅ Custom ASS styling applied successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error applying custom styling: {str(e)}")
        return False
```

**ASS Style Parameters Explained:**

| Parameter | Purpose | Values Used |
|-----------|---------|-------------|
| `fontname` | Font family | Language-specific (Noto Sans Tamil, Roboto, etc.) |
| `fontsize` | Font size in points | 17-20 (vertical), 20 (landscape) |
| `primarycolour` | Main text color | `&H00FFFFFF` (White in BGR hex) |
| `secondarycolour` | Karaoke/secondary color | `&H000000FF` (Red) |
| `outlinecolour` | Outline/border color | `&H00000000` (Black) |
| `backcolour` | Background box color | `&H80000000` (Semi-transparent black) |
| `bold` | Bold text | -1 (enabled) |
| `outline` | Outline thickness | 1 pixel |
| `alignment` | Text alignment | 2 (Bottom center) |
| `marginv` | Vertical margin | 10-90 pixels (varies by format) |

**Individual Control:** Each style parameter can be independently adjusted per language or video format.

---

### 3. Language-Specific ASS Styling

**Purpose:** Apply different fonts based on the language to ensure proper glyph rendering.

**Code Block (from cl_vid_gen.py):**
```python
def get_language_specific_ass_style(self, language: str) -> Dict[str, str]:
    """Get language-specific ASS styling options"""
    
    # Base style for all languages
    base_style = {
        'fontname': 'Roboto',  # Will be overridden below
        'fontsize': '17',
        'primarycolour': '&H00FFFFFF',  # White
        'secondarycolour': '&H000000FF',  # Red
        'outlinecolour': '&H00000000',  # Black outline
        'backcolour': '&H80000000',  # Semi-transparent black background
        'bold': '-1',
        'italic': '0',
        'underline': '0',
        'strikeout': '0',
        'scalex': '100',
        'scaley': '100',
        'spacing': '0',
        'angle': '0',
        'borderstyle': '1',
        'outline': '1',
        'shadow': '0',
        'alignment': '2',  # Bottom center
        'marginl': '10',
        'marginr': '10',
        'marginv': '90'
    }
    
    # Language-specific font settings
    language_fonts = {
        'english': 'Roboto',
        'hindi': 'Noto Sans Devanagari',
        'tamil': 'Noto Sans Tamil',
        'telugu': 'Noto Sans Telugu',
        'kannada': 'Noto Sans Kannada',
        'malayalam': 'Noto Sans Malayalam',
        'korean': 'Noto Sans KR',
        'french': 'Roboto'
    }
    
    # Set font for this language
    if language in language_fonts:
        base_style['fontname'] = language_fonts[language]
    else:
        base_style['fontname'] = 'Arial'  # Default
    
    return base_style
```

**Landscape Version (from cl_vid_gen_2.py):**
```python
def get_language_specific_ass_style(self) -> Dict[str, str]:
    """Get ASS styling options for landscape videos"""
    
    # Optimized style for landscape videos with subtitles positioned lower
    style = {
        'fontname': 'Roboto',
        'fontsize': '20',
        'primarycolour': '&H00FFFFFF',  # White
        'secondarycolour': '&H000000FF',  # Red
        'outlinecolour': '&H00000000',  # Black outline
        'backcolour': '&H80000000',  # Semi-transparent black background
        'bold': '-1',
        'italic': '0',
        'underline': '0',
        'strikeout': '0',
        'scalex': '100',
        'scaley': '100',
        'spacing': '0',
        'angle': '0',
        'borderstyle': '1',
        'outline': '1',
        'shadow': '0',
        'alignment': '2',  # Bottom center
        'marginl': '10',
        'marginr': '10',
        'marginv': '30'  # Reduced from 90 to 30 to move subtitles lower/closer to bottom
    }
    
    return style
```

**Key Differences Between Vertical and Horizontal:**
- **Vertical (Portrait):** `marginv: 90` - Subtitles positioned higher
- **Horizontal (Landscape):** `marginv: 30` - Subtitles positioned lower (closer to bottom)

**Individual Control:** Font size, margin, and font family can be adjusted independently per language and video format.

---

### 4. Programmatic ASS Creation for Titles

**Purpose:** Create ASS subtitle files programmatically for intro titles with specific timing.

**Code Block (from cl_vid_gen_2.py):**
```python
def create_intro_title_ass(ass_path: str, title_text: str, start_time: float, end_time: float) -> bool:
    """Create ASS subtitle file for intro title"""
    try:
        # Convert seconds to ASS time format (H:MM:SS.CC)
        def seconds_to_ass_time(seconds):
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours}:{minutes:02d}:{secs:05.2f}"
        
        start_ass_time = seconds_to_ass_time(start_time)
        end_ass_time = seconds_to_ass_time(end_time)
        
        # ASS content with custom styling for title
        ass_content = f"""[Script Info]
Title: Intro Title
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,AtomicAge-Regular,36,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,0,5,10,10,50,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,{start_ass_time},{end_ass_time},Default,,0,0,0,,{title_text}
"""
        
        with open(ass_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)
        
        logger.info(f"✅ Created intro title ASS: {title_text}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating intro title ASS: {str(e)}")
        return False
```

**ASS Format Breakdown:**

1. **Time Conversion:** Converts seconds (e.g., 6.5) to ASS format (0:00:06.50)
2. **Style Definition:** Uses `AtomicAge-Regular` font, size 36, center alignment (5)
3. **Dialogue Event:** Displays title text from `start_time` to `end_time`

**Individual Control:** Start time, end time, font, size, and position can all be customized independently.

---

### 5. Subtitle Path Escaping for FFmpeg

**Purpose:** Properly escape Windows paths for FFmpeg's `ass` filter.

**Code Block:**
```python
# Escape path for FFmpeg
ass_path_escaped = ass_path.replace('\\', '\\\\').replace(':', '\\:')
logger.info(f"📝 ASS ready: {ass_path}")
logger.info(f"📝 ASS escaped: {ass_path_escaped}")
```

**Why Needed:** FFmpeg's `ass` filter on Windows requires:
- Backslashes (`\`) escaped as `\\`
- Colons (`:`) escaped as `\:`

**Example:**
- Original: `C:\Users\Project\subtitles.ass`
- Escaped: `C\\:\Users\Project\subtitles.ass`

**Individual Control:** You can verify the escaped path before passing to FFmpeg.

---

## Vertical Video Generation

### 1. Thumbnail Frame Creation with PIL

**Purpose:** Create engaging thumbnail frames with text overlay using PIL (Pillow) library.

**Code Block:**
```python
def create_thumbnail_frame(self, zodiac_sign: str, engaging_text: str, date: str, duration: float = 1/30) -> Optional[str]:
    """Create advanced thumbnail frame video with engaging text overlay using the enhanced logic
    
    Args:
        zodiac_sign: Zodiac sign name
        engaging_text: Text to overlay on the thumbnail
        date: Date string in YYYY-MM-DD format
        duration: Duration of the thumbnail frame in seconds
        
    Returns:
        Path to the created thumbnail video file, or None if failed
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Template path
        template_path = self.thumbnail_templates_dir / f"{zodiac_sign.lower()}.png"
        
        if not template_path.exists():
            logger.error(f"❌ Thumbnail template not found: {template_path}")
            return None
        
        # Parse date
        formatted_date = self.parse_date(date)
        if not formatted_date:
            logger.warning(f"⚠️ Could not parse date: {date}")
        
        logger.info(f"🖼️ Creating advanced thumbnail for {zodiac_sign} with text: '{engaging_text}' and date: '{formatted_date}'")
        
        # Load template
        img = Image.open(template_path)
        draw = ImageDraw.Draw(img)
        
        # Load font with user-specified parameters
        font = None
        font_size = 100  # User specified font size
        font_name = "Impact.ttf"  # User specified font
        
        # Try to load the specified font first, then fallback to other options
        preferred_fonts = [font_name, "impact.ttf", "Impact.ttc"] + self.thumbnail_font_options
        
        for font_option in preferred_fonts:
            if font_option == "default":
                try:
                    font = ImageFont.load_default()
                    # Try to scale default font
                    font = ImageFont.load_default().font_variant(size=font_size)
                except:
                    font = ImageFont.load_default()
                logger.info(f"⚠️ Using default font (size: {font_size})")
                break
            else:
                try:
                    font = ImageFont.truetype(font_option, font_size)
                    logger.info(f"✅ Using font: {font_option} (size: {font_size})")
                    break
                except Exception:
                    continue
        
        if font is None:
            logger.warning(f"⚠️ Could not load any fonts, using PIL default")
            font = ImageFont.load_default()
        
        # Get image dimensions
        img_width, img_height = img.size
        logger.debug(f"📐 Image dimensions: {img_width}x{img_height}")
        
        # Process main text with word-by-word logic
        include_sign_name = True  # User specified --include-sign-name
        sign_name_spacing = 50   # User specified --sign-name-spacing 50
        word_by_word = True
        line_spacing = 10
        section_spacing = 30
        word_spacing_boost = 5
        
        main_lines = []
        if word_by_word:
            # Process text word by word, including sign name
            sections = self.process_text_word_by_word(engaging_text, zodiac_sign, include_sign_name)
            for i, section in enumerate(sections):
                # Add each word as a separate line
                main_lines.extend(section)
                # Add a gap between sections (except for the last section)
                if i < len(sections) - 1:
                    # Use larger spacing before sign name if it's the last section
                    if include_sign_name and i == len(sections) - 2:
                        main_lines.append(f"SIGN_NAME_GAP_{sign_name_spacing}")  # Special gap marker
                    else:
                        main_lines.append("")  # Empty string represents a normal gap
            
            logger.debug(f"📝 Processed main text into {len(main_lines)} lines: {main_lines}")
        else:
            # Original text wrapping method (fallback)
            import textwrap
            wrapped_text = textwrap.fill(engaging_text.upper(), width=25)
            main_lines = wrapped_text.split('\n')
            
            # Add sign name if requested
            if include_sign_name:
                main_lines.append(f"SIGN_NAME_GAP_{sign_name_spacing}")  # Special gap marker
                main_lines.append(zodiac_sign.upper())
        
        # Process date text if provided (always as single line, not word-by-word)
        date_lines = []
        if formatted_date:
            # Date is always displayed as a single line, regardless of word_by_word setting
            date_lines = [formatted_date]
            logger.debug(f"📅 Date line: {date_lines}")
        
        # Calculate dimensions for main text
        main_line_heights = []
        main_line_widths = []
        
        for line in main_lines:
            if line == "":  # Normal gap line
                main_line_heights.append(section_spacing)
                main_line_widths.append(0)
            elif line.startswith("SIGN_NAME_GAP_"):  # Special gap before sign name
                gap_size = int(line.split("_")[-1])
                main_line_heights.append(gap_size)
                main_line_widths.append(0)
            else:
                bbox = draw.textbbox((0, 0), line, font=font)
                main_line_widths.append(bbox[2] - bbox[0])
                main_line_heights.append(bbox[3] - bbox[1])
        
        main_text_width = max([w for w in main_line_widths if w > 0]) if any(w > 0 for w in main_line_widths) else 0
        main_text_height = sum(main_line_heights) + (len([l for l in main_lines if l != "" and not l.startswith("SIGN_NAME_GAP_")]) - 1) * (line_spacing + word_spacing_boost)
        
        # Calculate dimensions for date text
        date_text_width = 0
        date_text_height = 0
        date_line_heights = []
        date_line_widths = []
        
        if date_lines:
            for line in date_lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                date_line_widths.append(bbox[2] - bbox[0])
                date_line_heights.append(bbox[3] - bbox[1])
            
            date_text_width = max(date_line_widths) if date_line_widths else 0
            date_text_height = sum(date_line_heights) + (len(date_lines) - 1) * line_spacing
        
        logger.debug(f"📏 Main text dimensions: {main_text_width}x{main_text_height}")
        if formatted_date:
            logger.debug(f"📏 Date text dimensions: {date_text_width}x{date_text_height}")
        
        # Calculate positions
        # Main text goes in center
        main_x, main_y = self.thumbnail_positions["center"](img_width, img_height, main_text_width, main_text_height)
        
        # Date goes at bottom
        date_x = date_y = 0
        if date_lines:
            date_margin = 100  # Margin from bottom
            date_x = (img_width - date_text_width) // 2
            date_y = img_height - date_text_height - date_margin
        
        logger.debug(f"📍 Main text position: ({main_x}, {main_y})")
        if date_lines:
            logger.debug(f"📍 Date position: ({date_x}, {date_y})")
        
        # Colors and outline (user preferences)
        text_color = "white"
        outline_color = "black"
        outline_width = 3
        
        # Draw main text
        current_y = main_y
        for i, line in enumerate(main_lines):
            if line == "":  # Normal gap line
                current_y += section_spacing
                continue
            elif line.startswith("SIGN_NAME_GAP_"):  # Special gap before sign name
                gap_size = int(line.split("_")[-1])
                current_y += gap_size
                continue
            
            line_bbox = draw.textbbox((0, 0), line, font=font)
            line_width = line_bbox[2] - line_bbox[0]
            line_height = line_bbox[3] - line_bbox[1]
            
            # Center each line horizontally
            line_x = main_x + (main_text_width - line_width) // 2
            
            # Draw outline
            if outline_width > 0:
                for dx in range(-outline_width, outline_width + 1):
                    for dy in range(-outline_width, outline_width + 1):
                        if dx != 0 or dy != 0:
                            draw.text((line_x + dx, current_y + dy), line, font=font, fill=outline_color)
            
            # Draw main text
            draw.text((line_x, current_y), line, font=font, fill=text_color)
            
            current_y += line_height + line_spacing + word_spacing_boost
        
        # Draw date text at bottom
        if date_lines:
            current_y = date_y
            for line in date_lines:
                line_bbox = draw.textbbox((0, 0), line, font=font)
                line_width = line_bbox[2] - line_bbox[0]
                line_height = line_bbox[3] - line_bbox[1]
                
                # Center each line horizontally
                line_x = date_x + (date_text_width - line_width) // 2
                
                # Draw outline
                if outline_width > 0:
                    for dx in range(-outline_width, outline_width + 1):
                        for dy in range(-outline_width, outline_width + 1):
                            if dx != 0 or dy != 0:
                                draw.text((line_x + dx, current_y + dy), line, font=font, fill=outline_color)
                
                # Draw main text
                draw.text((line_x, current_y), line, font=font, fill=text_color)
                
                current_y += line_height + line_spacing
        
        # Save thumbnail image
        temp_dir = self.base_dir / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = int(time.time())
        thumbnail_img_path = temp_dir / f"thumbnail_{zodiac_sign}_{timestamp}.png"
        img.save(thumbnail_img_path)
        
        logger.info(f"✅ Created advanced thumbnail image: {thumbnail_img_path}")
        
        # Convert image to video with silent audio track
        thumbnail_video_path = temp_dir / f"thumbnail_video_{zodiac_sign}_{timestamp}.mp4"
        
        ffmpeg_cmd = [
            'ffmpeg',
            '-loop', '1',
            '-i', str(thumbnail_img_path),
            '-f', 'lavfi',
            '-i', 'anullsrc=channel_layout=mono:sample_rate=24000',  # Add silent audio
            '-t', str(duration),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-r', '30',
            '-pix_fmt', 'yuv420p',
            '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',  # Ensure even dimensions
            '-shortest',  # Stop when the shortest input ends
            '-y',
            str(thumbnail_video_path)
        ]
        
        logger.info(f"🎬 Converting advanced thumbnail to video frame ({duration}s)")
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and thumbnail_video_path.exists():
            logger.info(f"✅ Created advanced thumbnail video: {thumbnail_video_path} ({duration}s)")
            # Clean up image file
            thumbnail_img_path.unlink()
            return str(thumbnail_video_path)
        else:
            logger.error(f"❌ Failed to create thumbnail video")
            logger.error(f"FFmpeg error: {result.stderr}")
            return None
        
    except ImportError:
        logger.error("❌ PIL (Pillow) library not found. Please install it: pip install Pillow")
        return None
    except Exception as e:
        logger.error(f"❌ Error creating advanced thumbnail for {zodiac_sign}: {e}")
        return None
```

**FFmpeg Command for Converting Image to Video:**
```bash
ffmpeg -loop 1 \
  -i <thumbnail_image.png> \
  -f lavfi \
  -i anullsrc=channel_layout=mono:sample_rate=24000 \
  -t <duration> \
  -c:v libx264 \
  -c:a aac \
  -r 30 \
  -pix_fmt yuv420p \
  -vf 'scale=trunc(iw/2)*2:trunc(ih/2)*2' \
  -shortest \
  -y <output_video.mp4>
```

**Parameters:**
- `-loop 1`: Loop the input image infinitely
- `-f lavfi -i anullsrc=...`: Generate silent audio source
- `-t <duration>`: Duration of the thumbnail frame (e.g., 0.033333 seconds = 1 frame at 30fps)
- `-c:v libx264`: Use H.264 video codec
- `-c:a aac`: Use AAC audio codec
- `-r 30`: Frame rate of 30 fps
- `-pix_fmt yuv420p`: Pixel format for compatibility
- `-vf 'scale=...'`: Ensure width and height are even numbers (required for H.264)
- `-shortest`: Stop encoding when the shortest input (audio or video) ends

**Individual Control:**
- **Font:** Impact.ttf at size 100
- **Text Color:** White with black outline (3px)
- **Positioning:** Center for main text, bottom for date
- **Word-by-word display:** Each word on a separate line
- **Duration:** Customizable (default 1 frame = 0.033333s)

---

### 2. Thumbnail Overlay on Video (Preserving Background Audio)

**Purpose:** Overlay the thumbnail frame at the beginning of the video while preserving the original background music.

**Code Block:**
```python
# FIXED: Use overlay method instead of concatenation to preserve background audio
if thumbnail_path:
    logger.info("🎬 Creating video with enhanced thumbnail at beginning using OVERLAY method (preserves background audio)")
    
    # Create temporary file for overlay processing
    temp_dir = Path(self.base_dir) / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_video_path = temp_dir / f"temp_video_{zodiac_sign}_{int(time.time())}.mp4"
    
    # Convert to absolute paths for FFmpeg
    thumbnail_abs_path = os.path.abspath(thumbnail_path)
    video_abs_path = os.path.abspath(video_path)
    
    logger.info(f"📋 Enhanced Thumbnail path: {thumbnail_abs_path}")
    logger.info(f"📋 Video path: {video_abs_path}")
    
    # Get thumbnail duration for overlay timing
    thumbnail_duration = self.get_media_duration(thumbnail_abs_path)
    
    # Use overlay instead of concatenation to preserve background audio
    overlay_cmd = [
        'ffmpeg',
        '-i', video_abs_path,          # Main video with background music
        '-i', thumbnail_abs_path,      # Enhanced thumbnail frame
        '-filter_complex', 
        f'[0:v][1:v]overlay=enable=\'lte(t,{thumbnail_duration})\':format=auto[outv]',
        '-map', '[outv]',              # Use overlayed video
        '-map', '0:a',                 # Keep original background audio
        '-c:v', 'libx264',
        '-c:a', 'copy',                # Don't re-encode audio (preserves quality)
        '-preset', 'fast',
        '-y',
        str(temp_video_path)
    ]
    
    logger.info("🎬 Overlaying enhanced thumbnail with background audio preservation...")
    logger.info(f"🎬 Overlay command: {' '.join(overlay_cmd)}")
    result = subprocess.run(overlay_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        logger.error(f"❌ Overlay failed: {result.stderr}")
        return False
    else:
        logger.info("✅ Enhanced thumbnail overlay successful - background audio preserved!")
    
    # Verify overlayed video was created
    if not temp_video_path.exists() or temp_video_path.stat().st_size < 1000:
        logger.error(f"❌ Overlayed video not created or too small: {temp_video_path}")
        return False
    
    # Use the overlayed video as the main video
    video_path = str(temp_video_path)
    logger.info(f"✅ Video overlay successful with preserved background audio: {video_path}")
```

**FFmpeg Command:**
```bash
ffmpeg -i <main_video.mp4> \
  -i <thumbnail_video.mp4> \
  -filter_complex '[0:v][1:v]overlay=enable='\''lte(t,<thumbnail_duration>)'\'':format=auto[outv]' \
  -map '[outv]' \
  -map '0:a' \
  -c:v libx264 \
  -c:a copy \
  -preset fast \
  -y <output_video.mp4>
```

**Parameters:**
- `-filter_complex '[0:v][1:v]overlay=...'`: Overlay second video on first
- `enable='lte(t,<duration>)'`: Only show overlay for first N seconds
- `-map '[outv]'`: Use the overlayed video stream
- `-map '0:a'`: Keep audio from the first input (background music)
- `-c:a copy`: Don't re-encode audio (preserves quality and processing time)

**How It Works:**
1. Takes the main video with background music as input 1
2. Takes the thumbnail frame video as input 2
3. Overlays thumbnail on top of main video for the first N seconds
4. Preserves the original audio track from the main video
5. After thumbnail duration, only main video is shown

**Individual Control:** Thumbnail duration and overlay timing can be precisely controlled.

---

### 3. Video Processing with Subtitles and Audio Mixing

**Purpose:** Combine video template, TTS audio, and subtitles into a final video with both background music and narration.

**Code Block:**
```python
# Build final FFmpeg command (same as before, but now with thumbnail overlayed in video_path)
if include_subtitles and ass_path:
    # WITH SUBTITLES
    command = [
        'ffmpeg',
        '-i', video_path,                    # Input video (now includes thumbnail if provided)
        '-i', audio_path,                    # Input audio  
        '-t', str(audio_duration),           # Trim to audio duration
        '-vf', f'ass={ass_path_escaped}',    # Video filter with subtitles
        '-filter_complex', '[0:a][1:a]amix=inputs=2:duration=longest[aout]',  # Mix both audio tracks
        '-map', '0:v',                       # Map video from first input  
        '-map', '[aout]',                    # Map mixed audio output
        '-c:v', 'libx264',                   # Video codec
        '-c:a', 'aac',                       # Audio codec
        '-preset', 'medium',                 # Encoding preset
        '-crf', '23',                        # Quality
        '-y',                                # Overwrite
        output_path
    ]
    logger.info("🎬 FINAL COMMAND WITH SUBTITLES AND ENHANCED THUMBNAIL")
else:
    # WITHOUT SUBTITLES
    command = [
        'ffmpeg',
        '-i', video_path,
        '-i', audio_path,
        '-filter_complex', '[0:a][1:a]amix=inputs=2:duration=longest[aout]',  # Mix both audio tracks
        '-map', '0:v',                       # Map video from first input  
        '-map', '[aout]',                    # Map mixed audio output
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-preset', 'medium',
        '-crf', '23',
        '-t', str(audio_duration),           # Trim to audio duration
        '-y',
        output_path
    ]
    logger.info("🎬 FINAL COMMAND WITHOUT SUBTITLES BUT WITH ENHANCED THUMBNAIL")

logger.info(f"🎬 Command: {' '.join(command)}")

try:
    result = subprocess.run(command, capture_output=True, text=True)
    logger.info(f"🎬 Return code: {result.returncode}")
    
    if result.stderr:
        # Look for ASS-related output
        stderr_lines = result.stderr.split('\n')
        for line in stderr_lines:
            if 'ass' in line.lower() or 'subtitle' in line.lower():
                logger.info(f"📝 {line}")
    
    if result.returncode == 0:
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            final_duration = self.get_media_duration(output_path)
            final_size = os.path.getsize(output_path) / 1024 / 1024
            logger.info(f"✅ SUCCESS! {final_duration:.2f}s, {final_size:.1f}MB")
            
            if ass_path:
                logger.info(f"📄 ASS file kept: {ass_path}")
            
            # Clean up temporary video file if it was created
            if thumbnail_path and 'temp_video_' in video_path:
                try:
                    os.unlink(video_path)
                    logger.info("🧹 Cleaned up temporary overlayed video")
                except:
                    pass
            
            return True
        else:
            logger.error(f"❌ Output failed: {output_path}")
            return False
    else:
        logger.error("❌ FFmpeg failed!")
        logger.error(f"STDERR: {result.stderr}")
        return False
        
except Exception as e:
    logger.error(f"❌ Exception: {e}")
    return False
```

**FFmpeg Command WITH Subtitles:**
```bash
ffmpeg -i <video_with_thumbnail.mp4> \
  -i <tts_audio.wav> \
  -t <audio_duration> \
  -vf 'ass=<subtitles.ass>' \
  -filter_complex '[0:a][1:a]amix=inputs=2:duration=longest[aout]' \
  -map '0:v' \
  -map '[aout]' \
  -c:v libx264 \
  -c:a aac \
  -preset medium \
  -crf 23 \
  -y <output.mp4>
```

**FFmpeg Command WITHOUT Subtitles:**
```bash
ffmpeg -i <video_with_thumbnail.mp4> \
  -i <tts_audio.wav> \
  -filter_complex '[0:a][1:a]amix=inputs=2:duration=longest[aout]' \
  -map '0:v' \
  -map '[aout]' \
  -c:v libx264 \
  -c:a aac \
  -preset medium \
  -crf 23 \
  -t <audio_duration> \
  -y <output.mp4>
```

**Parameters:**
- `-vf 'ass=<subtitles.ass>'`: Burn subtitles into video using ASS filter
- `-filter_complex '[0:a][1:a]amix=inputs=2:duration=longest[aout]'`: Mix background music and TTS audio
  - `[0:a]`: Audio from first input (background music from video)
  - `[1:a]`: Audio from second input (TTS narration)
  - `amix=inputs=2`: Mix two audio streams
  - `duration=longest`: Output duration matches the longest input
  - `[aout]`: Label for mixed audio output
- `-map '0:v'`: Use video from first input
- `-map '[aout]'`: Use the mixed audio output
- `-c:v libx264`: Encode video with H.264 codec
- `-c:a aac`: Encode audio with AAC codec
- `-preset medium`: Encoding speed vs compression tradeoff
- `-crf 23`: Constant Rate Factor (quality) - lower = better quality (18-28 recommended)
- `-t <duration>`: Trim output to specified duration

**Individual Control:**
- **Subtitle inclusion:** Can be toggled on/off
- **Audio mixing:** Background music volume is controlled by original video file
- **Video quality:** CRF value can be adjusted (18 = high quality, 28 = lower quality)
- **Encoding speed:** Preset can be changed (fast, medium, slow, veryslow)

---

## Horizontal Video Generation

### 1. Intro Video Processing with Date Title and Fade

**Purpose:** Process the intro video by adding a date title overlay and applying a fade-out effect.

**Code Block:**
```python
def process_intro_video(self, video_date: str) -> Optional[str]:
    """Process intro video with date title and fade out effect"""
    try:
        if not self.intro_video.exists():
            logger.error(f"❌ Intro video not found: {self.intro_video}")
            return None
        
        logger.info("🎬 Processing intro video with date title and fade out")
        
        # Get intro video duration
        intro_duration = self.get_media_duration(str(self.intro_video))
        if not intro_duration:
            logger.error("❌ Could not get intro video duration")
            return None
        
        logger.info(f"📊 Intro duration: {intro_duration:.2f}s")
        
        # Format date for title
        title_text = self.format_date_for_title(video_date)
        logger.info(f"📝 Title text: {title_text}")
        
        # Create ASS file for title
        ass_file = self.temp_dir / "intro_title.ass"
        title_end_time = intro_duration - self.intro_fade_duration
        
        if not create_intro_title_ass(
            str(ass_file), 
            title_text, 
            self.intro_title_start_time, 
            title_end_time
        ):
            logger.error("❌ Failed to create intro title ASS")
            return None
        
        # Output path for processed intro
        processed_intro = self.temp_dir / "intro_processed.mp4"
        
        # Escape ASS path for FFmpeg
        ass_path_escaped = str(ass_file).replace('\\', '\\\\').replace(':', '\\:')
        
        # Build FFmpeg command for intro processing - ORIGINAL APPROACH
        command = [
            'ffmpeg',
            '-i', str(self.intro_video),
            '-vf', (
                f'scale=1920:1080:force_original_aspect_ratio=decrease,'  # 4K → 1080p
                # f'pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,'              # Add black bars if needed
                f'ass={ass_path_escaped},'                                # Add title
                f'fade=out:st={intro_duration - self.intro_fade_duration}:d={self.intro_fade_duration}'
            ),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-preset', 'medium',
            '-crf', '23',
            '-y',
            str(processed_intro)
        ]
        
        logger.info("🎬 Processing intro with title and fade out...")
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            if os.path.exists(processed_intro) and os.path.getsize(processed_intro) > 1000:
                final_duration = self.get_media_duration(str(processed_intro))
                final_size = os.path.getsize(processed_intro) / 1024 / 1024
                
                # Store duration for timestamp calculation
                self.video_durations["Intro"] = final_duration
                
                logger.info(f"✅ Intro processed successfully! {final_duration:.2f}s, {final_size:.1f}MB")
                return str(processed_intro)
            else:
                logger.error("❌ Processed intro is invalid")
                return None
        else:
            logger.error("❌ Intro processing failed!")
            logger.error(f"STDERR: {result.stderr}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error processing intro video: {e}")
        return None
```

**FFmpeg Command:**
```bash
ffmpeg -i <intro.mp4> \
  -vf 'scale=1920:1080:force_original_aspect_ratio=decrease,ass=<title.ass>,fade=out:st=<fade_start_time>:d=<fade_duration>' \
  -c:v libx264 \
  -c:a aac \
  -preset medium \
  -crf 23 \
  -y <intro_processed.mp4>
```

**Parameters:**
- `-vf 'scale=1920:1080:force_original_aspect_ratio=decrease'`: Scale 4K to 1080p while maintaining aspect ratio
- `ass=<title.ass>`: Overlay title subtitle
- `fade=out:st=<start_time>:d=<duration>`: Apply fade-out effect
  - `st=`: Start time of fade (e.g., if video is 10s and fade is 1s, st=9)
  - `d=`: Duration of fade effect (e.g., 1.0 seconds)

**Individual Control:**
- **Title start time:** Configurable (default: 6.0 seconds)
- **Fade duration:** Configurable (default: 1.0 second)
- **Scale resolution:** Can be changed to 720p, 4K, etc.

---

### 2. Individual Zodiac Video Processing

**Purpose:** Process each zodiac sign video by adding TTS audio and subtitles, mixing with background music.

**Code Block:**
```python
def process_single_video(self, 
                       zodiac_sign: str,
                       video_path: str, 
                       audio_path: str, 
                       subtitle_path: str,
                       output_path: str) -> bool:
    """Process a single zodiac video with audio and subtitles"""
    
    logger.info(f"🎬 Processing {zodiac_sign} video")
    logger.info(f"📂 Video: {video_path}")
    logger.info(f"🎵 Audio: {audio_path}")
    logger.info(f"📝 Subtitles: {subtitle_path}")
    logger.info(f"📤 Output: {output_path}")
    
    # Check files exist
    for file_path, file_type in [(video_path, "Video"), (audio_path, "Audio")]:
        if not os.path.exists(file_path):
            logger.error(f"❌ {file_type} file not found: {file_path}")
            return False
    
    # Get durations
    video_duration = self.get_media_duration(video_path)
    audio_duration = self.get_media_duration(audio_path)
    
    logger.info(f"📊 Video: {video_duration:.2f}s, Audio: {audio_duration:.2f}s")
    
    # Handle ASS conversion
    ass_path = None
    if subtitle_path and os.path.exists(subtitle_path):
        logger.info("📝 Converting SRT to ASS...")
        
        # Convert SRT to ASS with custom styling optimized for landscape
        ass_path = subtitle_path.replace('.srt', '.ass')
        style_options = self.get_language_specific_ass_style()
        
        if not create_custom_ass_style(subtitle_path, ass_path, style_options):
            logger.error("❌ ASS conversion failed")
            return False
        
        # Escape path for FFmpeg
        ass_path_escaped = ass_path.replace('\\', '\\\\').replace(':', '\\:')
        logger.info(f"📝 ASS ready: {ass_path}")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Build FFmpeg command - REVERT TO ORIGINAL STABLE APPROACH
    if ass_path:
        # WITH SUBTITLES
        command = [
            'ffmpeg',
            '-i', video_path,                    # Input video
            '-i', audio_path,                    # Input audio  
            '-t', str(audio_duration),           # Trim to audio duration
            '-vf', f'ass={ass_path_escaped}',    # Video filter with subtitles
            '-filter_complex', '[0:a][1:a]amix=inputs=2:duration=longest[aout]',  # Mix both audio tracks
            '-map', '0:v',                       # Map video from first input  
            '-map', '[aout]',                    # Map mixed audio output
            '-c:v', 'libx264',                   # Video codec
            '-c:a', 'aac',                       # Audio codec
            '-preset', 'slow',           # Better compression
            '-crf', '18',                # Higher quality (lower = better)
            '-pix_fmt', 'yuv420p',       # Ensure compatibility
            '-b:a', '128k',              # Higher audio quality
            '-y',                                # Overwrite
            output_path
        ]
        logger.info("🎬 Command WITH subtitles")
    else:
        # WITHOUT SUBTITLES
        command = [
            'ffmpeg',
            '-i', video_path,
            '-i', audio_path,
            '-filter_complex', '[0:a][1:a]amix=inputs=2:duration=longest[aout]',  # Mix both audio tracks
            '-map', '0:v',                       # Map video from first input  
            '-map', '[aout]',                    # Map mixed audio output
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-preset', 'slow',           # Better compression
            '-crf', '18',                # Higher quality (lower = better)
            '-pix_fmt', 'yuv420p',       # Ensure compatibility
            '-b:a', '128k',              # Higher audio quality
            '-t', str(audio_duration),           # Trim to audio duration
            '-y',
            output_path
        ]
        logger.info("🎬 Command WITHOUT subtitles")
    
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                final_duration = self.get_media_duration(output_path)
                final_size = os.path.getsize(output_path) / 1024 / 1024
                
                # Store duration for timestamp calculation
                self.video_durations[zodiac_sign] = final_duration
                
                logger.info(f"✅ {zodiac_sign} SUCCESS! {final_duration:.2f}s, {final_size:.1f}MB")
                return True
            else:
                logger.error(f"❌ {zodiac_sign} output failed")
                return False
        else:
            logger.error(f"❌ {zodiac_sign} FFmpeg failed!")
            logger.error(f"STDERR: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ {zodiac_sign} Exception: {e}")
        return False
```

**FFmpeg Command WITH Subtitles:**
```bash
ffmpeg -i <zodiac_video.mp4> \
  -i <tts_audio.wav> \
  -t <audio_duration> \
  -vf 'ass=<subtitles.ass>' \
  -filter_complex '[0:a][1:a]amix=inputs=2:duration=longest[aout]' \
  -map '0:v' \
  -map '[aout]' \
  -c:v libx264 \
  -c:a aac \
  -preset slow \
  -crf 18 \
  -pix_fmt yuv420p \
  -b:a 128k \
  -y <output.mp4>
```

**FFmpeg Command WITHOUT Subtitles:**
```bash
ffmpeg -i <zodiac_video.mp4> \
  -i <tts_audio.wav> \
  -filter_complex '[0:a][1:a]amix=inputs=2:duration=longest[aout]' \
  -map '0:v' \
  -map '[aout]' \
  -c:v libx264 \
  -c:a aac \
  -preset slow \
  -crf 18 \
  -pix_fmt yuv420p \
  -b:a 128k \
  -t <audio_duration> \
  -y <output.mp4>
```

**Parameters:**
- `-preset slow`: Slower encoding for better compression (quality/size tradeoff)
- `-crf 18`: Very high quality (18 is near-lossless)
- `-pix_fmt yuv420p`: Standard pixel format for maximum compatibility
- `-b:a 128k`: Audio bitrate at 128 kbps (high quality)

**Individual Control:**
- **Quality:** CRF value (18 for landscape vs 23 for vertical)
- **Encoding speed:** Preset (slow for landscape vs medium for vertical)
- **Audio quality:** 128k for landscape vs default AAC for vertical

---

### 3. Video Concatenation

**Purpose:** Combine multiple processed videos into a single continuous video.

**Code Block:**
```python
def combine_videos(self, video_list: List[str], output_path: str) -> bool:
    """Combine multiple videos into one using FFmpeg concat"""
    try:
        # Create concat file
        concat_file = self.temp_dir / "concat_list.txt"
        
        with open(concat_file, 'w') as f:
            for video_path in video_list:
                # Escape the path for concat file
                escaped_path = video_path.replace('\\', '/')
                f.write(f"file '{escaped_path}'\n")
        
        logger.info(f"📝 Created concat file with {len(video_list)} videos")
        
        # Combine videos - REVERT TO ORIGINAL STABLE APPROACH
        command = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_file),
            '-c', 'copy',  # Copy without re-encoding for speed and quality
            '-y',
            output_path
        ]
        
        logger.info("🔗 Combining videos...")
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                duration = self.get_media_duration(output_path)
                size = os.path.getsize(output_path) / 1024 / 1024
                logger.info(f"✅ Videos combined successfully! {duration:.2f}s, {size:.1f}MB")
                return True
            else:
                logger.error("❌ Combined video is invalid")
                return False
        else:
            logger.error("❌ Video combination failed!")
            logger.error(f"STDERR: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error combining videos: {e}")
        return False
```

**Concat List File Format:**
```
file '/path/to/intro.mp4'
file '/path/to/aries.mp4'
file '/path/to/taurus.mp4'
file '/path/to/gemini.mp4'
...
```

**FFmpeg Command:**
```bash
ffmpeg -f concat -safe 0 -i <concat_list.txt> -c copy -y <output.mp4>
```

**Parameters:**
- `-f concat`: Use concat demuxer
- `-safe 0`: Allow absolute file paths in concat list
- `-i <concat_list.txt>`: Input concat list file
- `-c copy`: Copy streams without re-encoding (fastest, lossless)
- `-y`: Overwrite output file

**How It Works:**
1. Creates a text file listing all videos to concatenate
2. FFmpeg reads the list and combines videos in order
3. `-c copy` ensures no quality loss (direct stream copy)

**Individual Control:**
- **Video order:** Controlled by order in concat list
- **Re-encoding:** Can switch from `-c copy` to `-c:v libx264` if needed

---

## Background Music Integration

### Purpose: Add looping background music with fade effects and proper volume mixing.

**Code Block:**
```python
def add_background_music(self, video_path: str, music_path: str, output_path: str) -> bool:
    """Add background music with fade out effects (NO FADE IN) - FIXED VERSION"""
    try:
        if not os.path.exists(music_path):
            logger.error(f"❌ Background music not found: {music_path}")
            return False
        
        # Get video and music durations
        video_duration = self.get_media_duration(video_path)
        music_duration = self.get_media_duration(music_path)
        
        if not video_duration:
            logger.error("❌ Could not get video duration")
            return False
        
        if not music_duration:
            logger.error("❌ Could not get music duration")
            return False
        
        logger.info(f"🎵 Adding background music")
        logger.info(f"🎵 Video duration: {video_duration:.2f}s")
        logger.info(f"🎵 Music duration: {music_duration:.2f}s")
        logger.info(f"🎵 Music file: {music_path}")
        
        # Fade duration (3 seconds)
        fade_duration = 3.0
        
        # Check if video has audio stream
        check_audio_cmd = [
            'ffprobe', '-v', 'quiet', '-select_streams', 'a:0', 
            '-show_entries', 'stream=index', '-of', 'csv=p=0', video_path
        ]
        audio_check = subprocess.run(check_audio_cmd, capture_output=True, text=True)
        has_audio = audio_check.returncode == 0 and audio_check.stdout.strip()
        
        logger.info(f"🎵 Video has audio stream: {has_audio}")
        
        # Calculate how many loops we need if video is longer than music
        if video_duration > music_duration:
            loops_needed = int((video_duration / music_duration) + 1)
            logger.info(f"🔄 Video longer than music, will loop {loops_needed} times")
        else:
            loops_needed = 0
            logger.info("🎵 Music is longer than or equal to video duration")
        
        # Build filter complex based on whether we need looping and mixing
        if has_audio:
            # Video has audio - mix with background music
            # BOOSTED TTS + REDUCED BACKGROUND MUSIC (-16dB instead of -18dB)
            if video_duration > music_duration:
                # Need to loop background music - NO FADE IN
                filter_complex = (
                    f"[0:a]volume=+3dB[boosted_video];"  # Boost video audio (includes TTS) by 3dB
                    f"[1:a]aloop=loop={loops_needed}:size={int(music_duration * 44100)},"
                    f"volume=-16dB,"  # CHANGED: -16dB instead of -18dB for background music
                    f"afade=t=out:st={video_duration-fade_duration}:d={fade_duration},"
                    f"atrim=duration={video_duration}[bg];"
                    f"[boosted_video][bg]amix=inputs=2:duration=first:dropout_transition=0[aout]"
                )
            else:
                # Music is long enough, no looping needed - NO FADE IN
                filter_complex = (
                    f"[0:a]volume=+3dB[boosted_video];"  # Boost video audio (includes TTS) by 3dB
                    f"[1:a]volume=-16dB,"  # CHANGED: -16dB instead of -18dB for background music
                    f"afade=t=out:st={video_duration-fade_duration}:d={fade_duration},"
                    f"atrim=duration={video_duration}[bg];"
                    f"[boosted_video][bg]amix=inputs=2:duration=first:dropout_transition=0[aout]"
                )
        else:
            # Video has no audio - use only background music
            if video_duration > music_duration:
                # Need to loop background music - NO FADE IN
                filter_complex = (
                    f"[1:a]aloop=loop={loops_needed}:size={int(music_duration * 44100)},"
                    f"volume=-16dB,"  # CHANGED: -16dB instead of -18dB
                    f"afade=t=out:st={video_duration-fade_duration}:d={fade_duration},"
                    f"atrim=duration={video_duration}[aout]"
                )
            else:
                # Music is long enough, no looping needed - NO FADE IN
                filter_complex = (
                    f"[1:a]volume=-16dB,"  # CHANGED: -16dB instead of -18dB
                    f"afade=t=out:st={video_duration-fade_duration}:d={fade_duration},"
                    f"atrim=duration={video_duration}[aout]"
                )
        
        command = [
            'ffmpeg',
            '-i', video_path,           # Input video
            '-i', music_path,           # Background music
            '-filter_complex', filter_complex,
            '-map', '0:v',              # Map video
            '-map', '[aout]',           # Map processed audio
            '-c:v', 'copy',             # Copy video without re-encoding
            '-c:a', 'aac',              # Encode audio to AAC
            '-y',
            output_path
        ]
        
        logger.info("🎵 Adding background music with improved TTS balance...")
        logger.info(f"🎵 Filter: {filter_complex}")
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                final_duration = self.get_media_duration(output_path)
                final_size = os.path.getsize(output_path) / 1024 / 1024
                logger.info(f"✅ Background music added successfully! {final_duration:.2f}s, {final_size:.1f}MB")
                return True
            else:
                logger.error("❌ Final output is invalid")
                return False
        else:
            logger.error("❌ Background music addition failed!")
            logger.error(f"STDERR: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error adding background music: {e}")
        return False
```

**FFmpeg Command (Video with Audio + Looping Background Music):**
```bash
ffmpeg -i <video_with_audio.mp4> \
  -i <background_music.mp3> \
  -filter_complex '[0:a]volume=+3dB[boosted_video];[1:a]aloop=loop=<loops>:size=<samples>,volume=-16dB,afade=t=out:st=<fade_start>:d=<fade_duration>,atrim=duration=<video_duration>[bg];[boosted_video][bg]amix=inputs=2:duration=first:dropout_transition=0[aout]' \
  -map '0:v' \
  -map '[aout]' \
  -c:v copy \
  -c:a aac \
  -y <output.mp4>
```

**FFmpeg Command (Video without Audio + Looping Background Music):**
```bash
ffmpeg -i <video_no_audio.mp4> \
  -i <background_music.mp3> \
  -filter_complex '[1:a]aloop=loop=<loops>:size=<samples>,volume=-16dB,afade=t=out:st=<fade_start>:d=<fade_duration>,atrim=duration=<video_duration>[aout]' \
  -map '0:v' \
  -map '[aout]' \
  -c:v copy \
  -c:a aac \
  -y <output.mp4>
```

**Filter Complex Breakdown:**

1. **Boost Video Audio (TTS):**
   ```
   [0:a]volume=+3dB[boosted_video]
   ```
   - Increases volume of video's audio (TTS narration) by 3dB

2. **Loop Background Music:**
   ```
   [1:a]aloop=loop=<loops>:size=<samples>
   ```
   - `aloop`: Audio loop filter
   - `loop=<N>`: Number of loops needed
   - `size=<samples>`: Loop size in samples (music_duration * 44100)

3. **Reduce Background Music Volume:**
   ```
   volume=-16dB
   ```
   - Reduces background music by 16dB to prevent overlap with TTS

4. **Fade Out Effect:**
   ```
   afade=t=out:st=<start_time>:d=<duration>
   ```
   - `t=out`: Fade out type
   - `st=<time>`: Start time (video_duration - fade_duration)
   - `d=<duration>`: Fade duration (3.0 seconds)

5. **Trim to Video Duration:**
   ```
   atrim=duration=<video_duration>[bg]
   ```
   - Trim looped music to match video length

6. **Mix Audio Streams:**
   ```
   [boosted_video][bg]amix=inputs=2:duration=first:dropout_transition=0[aout]
   ```
   - `amix`: Audio mixing filter
   - `inputs=2`: Mix two audio streams (TTS + background music)
   - `duration=first`: Use duration of first input
   - `dropout_transition=0`: No transition when an input ends

**Individual Control:**

| Parameter | Description | Control |
|-----------|-------------|---------|
| TTS Volume | Boost for narration | `+3dB` (adjustable) |
| BGM Volume | Background music level | `-16dB` (adjustable) |
| Fade Duration | Length of fade out | `3.0` seconds (adjustable) |
| Fade Start | When fade begins | `video_duration - fade_duration` |
| Loop Count | Music repetitions | Calculated automatically |
| Loop Size | Samples per loop | `music_duration * 44100` |

**Key Features:**
- **Automatic Looping:** Music loops seamlessly if video is longer
- **Volume Balance:** TTS boosted (+3dB), BGM reduced (-16dB)
- **Fade Out:** Smooth 3-second fade at the end
- **No Fade In:** Music starts immediately without fade
- **No Re-encoding Video:** `-c:v copy` preserves video quality

---

## Quality Control & Individual Control

### 1. Video Quality Parameters

**CRF (Constant Rate Factor):**
- **Range:** 0-51 (lower = better quality)
- **Vertical Videos:** CRF 23 (balanced quality/size)
- **Horizontal Videos:** CRF 18 (near-lossless quality)

**Code:**
```python
# Vertical (cl_vid_gen.py)
'-crf', '23',  # Balanced quality

# Horizontal (cl_vid_gen_2.py)
'-crf', '18',  # Higher quality
```

**Preset Options:**
- **ultrafast, superfast, veryfast, faster, fast:** Faster encoding, lower compression
- **medium:** Balanced (default)
- **slow, slower, veryslow:** Better compression, slower encoding
- **placebo:** Minimal gains, very slow

**Code:**
```python
# Vertical (cl_vid_gen.py)
'-preset', 'medium',  # Balanced speed

# Horizontal (cl_vid_gen_2.py)
'-preset', 'slow',  # Better compression
```

**Individual Control:**
```python
# Adjust quality dynamically
def set_video_quality(video_type: str) -> tuple:
    if video_type == "vertical":
        return ('23', 'medium')
    elif video_type == "horizontal":
        return ('18', 'slow')
    elif video_type == "ultra_quality":
        return ('15', 'veryslow')
    else:
        return ('23', 'medium')

crf, preset = set_video_quality("horizontal")
command.extend(['-crf', crf, '-preset', preset])
```

---

### 2. Audio Quality Parameters

**Audio Bitrate:**
- **Vertical Videos:** Default AAC (typically 128k)
- **Horizontal Videos:** Explicit 128k

**Code:**
```python
# Horizontal (cl_vid_gen_2.py)
'-b:a', '128k',  # Higher audio quality
```

**Individual Control:**
```python
# Adjust audio bitrate
def get_audio_bitrate(quality_level: str) -> str:
    bitrates = {
        'low': '64k',
        'medium': '128k',
        'high': '192k',
        'ultra': '320k'
    }
    return bitrates.get(quality_level, '128k')

audio_bitrate = get_audio_bitrate('high')
command.extend(['-b:a', audio_bitrate])
```

---

### 3. Pixel Format Control

**Purpose:** Ensure maximum compatibility across devices.

**Code:**
```python
'-pix_fmt', 'yuv420p',  # Standard pixel format
```

**Alternative Formats:**
- `yuv420p`: Standard (8-bit, most compatible)
- `yuv444p`: Higher quality (no chroma subsampling)
- `yuv420p10le`: 10-bit (HDR support)

**Individual Control:**
```python
# Choose pixel format based on requirements
def get_pixel_format(hdr_required: bool, high_quality: bool) -> str:
    if hdr_required:
        return 'yuv420p10le'
    elif high_quality:
        return 'yuv444p'
    else:
        return 'yuv420p'

pix_fmt = get_pixel_format(hdr_required=False, high_quality=False)
command.extend(['-pix_fmt', pix_fmt])
```

---

### 4. Audio Mixing Control

**Volume Adjustment:**

```python
# Boost TTS narration
'[0:a]volume=+3dB[boosted_video]'

# Reduce background music
'volume=-16dB'
```

**Individual Control:**
```python
def calculate_audio_levels(tts_boost: int, bgm_reduction: int) -> tuple:
    """
    Calculate audio levels for mixing
    
    Args:
        tts_boost: dB to boost TTS (positive number, e.g., 3)
        bgm_reduction: dB to reduce BGM (positive number, e.g., 16)
    
    Returns:
        Tuple of (tts_volume_str, bgm_volume_str)
    """
    tts_volume = f'+{tts_boost}dB'
    bgm_volume = f'-{bgm_reduction}dB'
    return (tts_volume, bgm_volume)

tts_vol, bgm_vol = calculate_audio_levels(tts_boost=3, bgm_reduction=16)

# Use in filter
filter_complex = (
    f"[0:a]volume={tts_vol}[boosted_video];"
    f"[1:a]volume={bgm_vol}[bg];"
    f"[boosted_video][bg]amix=inputs=2:duration=first[aout]"
)
```

**Amix Parameters:**
```python
'amix=inputs=2:duration=longest'  # Longest input duration
'amix=inputs=2:duration=first'    # First input duration
'amix=inputs=2:duration=shortest' # Shortest input duration
```

---

### 5. Subtitle Positioning Control

**Vertical Videos (Portrait):**
```python
'marginv': '90'  # Higher position (90 pixels from bottom)
```

**Horizontal Videos (Landscape):**
```python
'marginv': '30'  # Lower position (30 pixels from bottom)
```

**Individual Control:**
```python
def get_subtitle_margin(video_format: str, custom_margin: int = None) -> int:
    """
    Get subtitle vertical margin based on video format
    
    Args:
        video_format: 'vertical' or 'horizontal'
        custom_margin: Override default margin
    
    Returns:
        Margin in pixels
    """
    if custom_margin is not None:
        return custom_margin
    
    margins = {
        'vertical': 90,
        'horizontal': 30,
        'square': 60
    }
    return margins.get(video_format, 60)

margin = get_subtitle_margin('horizontal', custom_margin=40)
style_options['marginv'] = str(margin)
```

---

### 6. Thumbnail Control

**Duration Control:**
```python
# Default: 1 frame at 30fps
duration = 1/30  # 0.033333 seconds

# Custom durations
duration = 1.0  # 1 second
duration = 0.5  # Half second
duration = 2.0  # 2 seconds
```

**Font Control:**
```python
font_size = 100  # User specified
font_name = "Impact.ttf"  # User specified

# Try multiple fonts in fallback order
preferred_fonts = [font_name, "impact.ttf", "Impact.ttc"] + self.thumbnail_font_options
```

**Position Control:**
```python
# Available positions
self.thumbnail_positions = {
    "center": lambda w, h, tw, th: ((w - tw) // 2, (h - th) // 2),
    "top": lambda w, h, tw, th: ((w - tw) // 2, h // 4),
    "bottom": lambda w, h, tw, th: ((w - tw) // 2, 3 * h // 4 - th),
    "top-left": lambda w, h, tw, th: (w // 10, h // 10),
    "top-right": lambda w, h, tw, th: (w - tw - w // 10, h // 10),
    "bottom-left": lambda w, h, tw, th: (w // 10, h - th - h // 10),
    "bottom-right": lambda w, h, tw, th: (w - tw - w // 10, h - th - h // 10),
}

# Use different position
main_x, main_y = self.thumbnail_positions["top"](img_width, img_height, main_text_width, main_text_height)
```

**Color Control:**
```python
# Current settings
text_color = "white"
outline_color = "black"
outline_width = 3

# Available colors
self.thumbnail_colors = {
    "white": "white",
    "black": "black",
    "yellow": "#FFD700",
    "gold": "#FFD700",
    "red": "#FF0000",
    "blue": "#0066FF",
    "green": "#00AA00",
    "purple": "#8A2BE2",
    "orange": "#FF8C00",
    "pink": "#FF69B4"
}

# Use different colors
text_color = self.thumbnail_colors["yellow"]
outline_color = self.thumbnail_colors["black"]
outline_width = 5  # Thicker outline
```

---

### 7. Timestamp Tracking

**Purpose:** Track when each zodiac sign starts in the final merged video.

**Code Block:**
```python
def calculate_and_print_timestamps(self):
    """Calculate and print timestamps for each zodiac sign in the final video"""
    print("\n🕐 CALCULATING TIMESTAMPS FOR FINAL VIDEO")
    print("=" * 60)
    
    cumulative_time = 0.0
    
    # Include intro in timestamps
    all_segments = ["Intro"] + self.zodiac_signs
    
    for segment in all_segments:
        if segment in self.video_durations:
            # Store start timestamp
            self.timestamps[segment] = cumulative_time
            
            # Format timestamp
            hours = int(cumulative_time // 3600)
            minutes = int((cumulative_time % 3600) // 60)
            seconds = int(cumulative_time % 60)
            
            if hours > 0:
                timestamp = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                timestamp = f"{minutes}:{seconds:02d}"
            
            duration = self.video_durations[segment]
            print(f"🎬 {timestamp} {segment:<12}")
            
            # Add duration to cumulative time
            cumulative_time += duration
    
    # Calculate total duration
    total_hours = int(cumulative_time // 3600)
    total_minutes = int((cumulative_time % 3600) // 60)
    total_seconds = int(cumulative_time % 60)
    
    if total_hours > 0:
        total_timestamp = f"{total_hours}:{total_minutes:02d}:{total_seconds:02d}"
    else:
        total_timestamp = f"{total_minutes}:{total_seconds:02d}"
    
    print("=" * 60)
    print(f"🎯 TOTAL VIDEO DURATION: {total_timestamp}")
    print("=" * 60)
```

**Output Example:**
```
🕐 CALCULATING TIMESTAMPS FOR FINAL VIDEO
============================================================
🎬 0:00 Intro       
🎬 0:10 Aries       
🎬 0:35 Taurus      
🎬 1:00 Gemini      
🎬 1:28 Cancer      
🎬 1:55 Leo         
🎬 2:22 Virgo       
🎬 2:48 Libra       
🎬 3:15 Scorpio     
🎬 3:42 Sagittarius 
🎬 4:10 Capricorn   
🎬 4:37 Aquarius    
🎬 5:03 Pisces      
============================================================
🎯 TOTAL VIDEO DURATION: 5:30
============================================================
```

**Individual Control:** You can export these timestamps to create YouTube chapters or video markers.

---

## Summary of FFmpeg Techniques

### Core Techniques Used

1. **Media Information Extraction:** ffprobe for duration, resolution, codec info
2. **Subtitle Conversion:** SRT to ASS with custom styling
3. **Image to Video:** Converting static images to video with silent audio
4. **Video Overlay:** Overlaying thumbnail frames while preserving audio
5. **Audio Mixing:** Combining multiple audio streams (TTS + background music)
6. **Video Filtering:** Applying subtitles, scaling, fading effects
7. **Video Concatenation:** Combining multiple videos seamlessly
8. **Audio Looping:** Repeating background music to match video length
9. **Fade Effects:** Smooth fade-in/fade-out for professional transitions
10. **Stream Mapping:** Precise control over which audio/video streams to use

### Quality Levels Achieved

**Vertical Videos (cl_vid_gen.py):**
- Video: H.264, CRF 23, Medium preset
- Audio: AAC, Default quality
- Subtitles: Positioned at 90px from bottom

**Horizontal Videos (cl_vid_gen_2.py):**
- Video: H.264, CRF 18 (near-lossless), Slow preset
- Audio: AAC, 128k bitrate
- Subtitles: Positioned at 30px from bottom

### Key Differences Between Systems

| Feature | Vertical (cl_vid_gen.py) | Horizontal (cl_vid_gen_2.py) |
|---------|-------------------------|------------------------------|
| **Purpose** | Individual sign videos with thumbnails | Combined landscape video with all signs |
| **Thumbnail** | Enhanced word-by-word display at start | Date title on intro video |
| **Video Quality** | CRF 23 (medium) | CRF 18 (high) |
| **Encoding Speed** | Medium preset | Slow preset |
| **Audio Bitrate** | Default AAC | 128k explicit |
| **Subtitle Position** | 90px from bottom | 30px from bottom |
| **Background Music** | Mixed with TTS in source videos | Added after concatenation with looping |
| **Output Structure** | Separate videos per sign | Single merged video |
| **Intro Processing** | No intro | Intro with date and fade |
| **Timestamps** | Not tracked | Full timestamp tracking |

### All FFmpeg Filters Used

1. **scale:** Resize video (e.g., 4K to 1080p)
2. **ass:** Burn ASS subtitles into video
3. **fade:** Apply fade-in/fade-out effects
4. **overlay:** Overlay one video on another with timing control
5. **amix:** Mix multiple audio streams
6. **volume:** Adjust audio volume (boost/reduce)
7. **aloop:** Loop audio stream
8. **afade:** Audio fade-in/fade-out
9. **atrim:** Trim audio to specific duration
10. **anullsrc:** Generate silent audio

### Individual Parameter Control Summary

Every aspect of the video generation can be controlled independently:

- **Video Quality:** CRF value (0-51)
- **Encoding Speed:** Preset (ultrafast to veryslow)
- **Audio Quality:** Bitrate (64k to 320k)
- **Pixel Format:** yuv420p, yuv444p, yuv420p10le
- **Subtitle Font:** Language-specific fonts
- **Subtitle Size:** Font size in points
- **Subtitle Position:** Margin from bottom in pixels
- **TTS Volume:** Boost in dB
- **BGM Volume:** Reduction in dB
- **Fade Duration:** Seconds
- **Loop Count:** Calculated or manual
- **Thumbnail Duration:** Seconds or frames
- **Thumbnail Font:** Font family and size
- **Thumbnail Position:** 7 position options
- **Thumbnail Colors:** 10 color options
- **Scaling Resolution:** Any resolution (720p, 1080p, 4K)

---

## Conclusion

This documentation covers all FFmpeg commands and techniques used in both video generation systems. Each technique is explained with:

1. **Purpose:** What it does and why it's needed
2. **Code Blocks:** Actual implementation from your codebase
3. **FFmpeg Commands:** Exact command syntax with all parameters
4. **Parameter Explanations:** What each parameter does
5. **Individual Control:** How to customize each aspect

The system provides:
- **Lossless Quality:** High CRF values and careful encoding
- **Proper Audio Syncing:** Precise duration matching and trimming
- **Subtitle Burning:** ASS format with custom styling per language
- **Background Music:** Looping, volume mixing, and fade effects
- **Complete Control:** Every parameter can be independently adjusted

This serves as a single point of understanding for your entire video generation pipeline.
