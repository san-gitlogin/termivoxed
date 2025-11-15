# Quick Start Guide 🚀

Get started with TermiVoxed in 5 minutes!

## Step 1: Install Dependencies

### macOS

```bash
# Install FFmpeg
brew install ffmpeg

# Install Python dependencies
cd console_video_editor
./setup.sh
```

### Linux (Ubuntu/Debian)

```bash
# Install FFmpeg
sudo apt-get update
sudo apt-get install ffmpeg

# Install Python dependencies
cd console_video_editor
chmod +x setup.sh
./setup.sh
```

### Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p storage/{projects,temp,cache,output}
mkdir -p logs
```

## Step 2: Run the Editor

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate

# Run the editor
python main.py
```

## Step 3: Create Your First Project

1. **Select "Create New Project" (option 1)**

2. **Enter project details:**

   ```
   Project name: MyFirstProject
   ```

3. **Select video files using the interactive file picker:**
   - Navigate folders with arrow keys
   - Press Enter to open folders
   - Select the folder containing your videos
   - Use Space key to select/deselect videos
   - Press Enter to confirm selection

4. **Add a segment (option 1 or 2 depending on project type):**

   ```
   Segment name: Intro
   Start time (seconds): 0
   End time (seconds): 10
   Text for voice-over: Hello and welcome to this tutorial
   Language code: en
   Rate: +0%
   Volume: +0%
   Pitch: +0Hz
   ```

4. **Generate voice-over:** Answer "Yes" when prompted

5. **Export video (option 6):**
   ```
   Output file path: output.mp4
   Quality: 3 (Balanced)
   Include subtitles: Yes
   Add background music: No
   ```

## Example Workflow

### Single Video Tutorial with Multiple Segments

```bash
# 1. Start the editor
python main.py

# 2. Create project
> 1 (Create New Project)
Project name: PythonTutorial

# 3. Select video using file picker
Navigate to your video → Select with Space → Confirm with Enter

# 4. Add first segment
> 2 (Add Segment) # Menu number may vary
Segment name: Introduction
Start time: 0
End time: 15
Text: Welcome to this Python programming tutorial. Today we'll learn about functions.
Language: en

# 5. Add second segment
> 2 (Add Segment)
Segment name: Functions Explained
Start time: 20
End time: 45
Text: A function is a block of reusable code that performs a specific task.
Language: en

# 6. Generate all voice-overs
> 6 (Generate Voice-Overs)

# 7. Export video
> 7 (Export Video)
Output: python_tutorial_final.mp4
Quality: 2 (High)
Subtitles: Yes
```

### Multi-Video Project Example

```bash
# 1. Start the editor
python main.py

# 2. Create multi-video project
> 1 (Create New Project)
Project name: VideoSeries

# 3. Select multiple videos using file picker
Navigate to folder → Use Space to select video1.mp4, video2.mp4, video3.mp4 → Confirm

# 4. Work on first video (automatically active)
> 6 (Add Segment) # For multi-video projects, segment options are offset
Add segments to video1.mp4...

# 5. Switch to second video
> 1 (Select Active Video)
Select: 2 (video2.mp4)

# 6. Add segments to second video
> 6 (Add Segment)
Add segments to video2.mp4...

# 7. Generate voice-overs for all videos
> 10 (Generate Voice-Overs)

# 8. Export combined video
> 11 (Export Video)
Select: 3 (Export combined video)
Output: video_series_combined.mp4
Quality: 3 (Balanced)
Subtitles: Yes
```

### Multilingual Video

```bash
# Add English segment
> 1 (Add Segment)
Text: Hello and welcome
Language: en

# Add Hindi segment
> 1 (Add Segment)
Text: नमस्ते और स्वागत है
Language: hi

# Add Tamil segment
> 1 (Add Segment)
Text: வணக்கம் மற்றும் வரவேற்பு
Language: ta

# Generate and export
> 5 (Generate Voice-Overs)
> 6 (Export Video)
```

## Tips for Best Results

1. **Segment Length:** Keep segments under 30 seconds for best TTS results
2. **Text Length:** Aim for 100-500 characters per segment
3. **Voice Parameters:** Start with defaults (+0% rate/volume/pitch)
4. **Quality:** Use "Balanced" for testing, "High" for final export
5. **Subtitles:** Enable for better accessibility
6. **Caching:** Reuse text when possible - audio is cached automatically

## Common Commands

### While in Project Menu

#### Single-Video Projects:
- **1** - Add More Videos
- **2** - Add new segment
- **3** - List all segments
- **4** - Edit existing segment
- **5** - Delete segment
- **6** - Generate voice-overs for all segments
- **7** - Export final video
- **8** - Configure project settings
- **9** - Save project
- **10** - Return to main menu

#### Multi-Video Projects:
**Video Management:**
- **1** - Select Active Video
- **2** - Add More Videos
- **3** - Remove Video
- **4** - Reorder Videos
- **5** - Show All Videos

**Segment Management:** (numbers 6-10)
- **6** - Add new segment to active video
- **7** - List segments of active video
- **8** - Edit existing segment
- **9** - Delete segment
- **10** - Generate voice-overs for all segments

**Export:** (numbers 11-14)
- **11** - Export video (with 3 options for multi-video)
- **12** - Configure project settings
- **13** - Save project
- **14** - Return to main menu

### Keyboard Shortcuts

- **Ctrl+C** - Cancel current operation
- **Ctrl+D** - Exit application
- **Enter** - Confirm with default value

## Voice Parameters Guide

### Rate (Speed)

- `+50%` - Much faster (excited, energetic)
- `+20%` - Faster (quick explanation)
- `+0%` - Normal (default)
- `-20%` - Slower (careful explanation)
- `-50%` - Much slower (emphasis)

### Volume

- `+20%` - Louder
- `+0%` - Normal (default)
- `-20%` - Quieter

### Pitch

- `+10Hz` - Higher pitch (younger voice)
- `+0Hz` - Normal (default)
- `-10Hz` - Lower pitch (deeper voice)

## Troubleshooting

### "Video file not found"

- Use absolute path: `/Users/username/Videos/video.mp4`
- Or relative from project directory: `../videos/video.mp4`

### "FFmpeg not found"

```bash
# Verify FFmpeg installation
ffmpeg -version

# If not installed:
# macOS: brew install ffmpeg
# Linux: sudo apt-get install ffmpeg
```

### "Edge-TTS connection error"

- Check internet connection
- TTS service requires internet access
- Wait a moment and try again (automatic retry)

### "Export failed"

- Check disk space
- Verify all segments have audio generated
- Try lower quality preset ("Balanced" instead of "Lossless")

## Next Steps

1. **Explore languages:** Try different languages (hi, ta, fr, es, etc.)
2. **Customize voices:** Experiment with rate, volume, and pitch
3. **Add background music:** Enhance your video with music
4. **Save projects:** Resume work later with project save/load
5. **Batch processing:** Process multiple videos efficiently

## Need Help?

- Check `logs/console_editor.log` for detailed error messages
- Read the full README.md for advanced features
- Verify all prerequisites are installed
- Test with a short video first

---

**You're all set! Start creating amazing videos with AI voice-overs! 🎬🎙️**
