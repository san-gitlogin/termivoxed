#!/usr/bin/env python3
"""
Console Video Editor - Main Entry Point
A powerful terminal-based video editor for adding AI voice-overs and subtitles
"""

import asyncio
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, FloatPrompt, IntPrompt
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich import print as rprint

from models import Project
from core import ExportPipeline
from backend.tts_service import TTSService
from utils.logger import logger, suppress_console_logs

console = Console()


class ConsoleEditor:
    """Main console editor application"""

    def __init__(self):
        self.project: Project = None
        self.tts_service = TTSService()
        self._voice_cache = {}  # Cache for available voices per language

    def show_banner(self):
        """Display application banner"""
        banner = """
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║     🎬 CONSOLE VIDEO EDITOR 🎬                       ║
║                                                       ║
║     AI Voice-Over & Subtitle Integration             ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
        """
        console.print(Panel(banner, style="bold blue"))

    def show_main_menu(self):
        """Display main menu and get user choice"""
        console.print("\n[bold cyan]Main Menu[/bold cyan]")
        console.print("1. Create New Project")
        console.print("2. Open Existing Project")
        console.print("3. List All Projects")
        console.print("4. Exit")

        choice = Prompt.ask("\nSelect option", choices=["1", "2", "3", "4"], default="1")
        return choice

    async def create_new_project(self):
        """Create a new project"""
        console.print("\n[bold green]Create New Project[/bold green]")

        try:
            # Get project name
            project_name = Prompt.ask("Project name")

            # Get video file path
            video_path = Prompt.ask("Video file path (absolute path)")
        except KeyboardInterrupt:
            console.print("\n[yellow]Project creation cancelled[/yellow]")
            return

        if not Path(video_path).exists():
            console.print(f"[red]Error: Video file not found: {video_path}[/red]")
            return

        try:
            # Create project
            self.project = Project(project_name, video_path)

            # Display video info
            info = self.project.timeline.video_info
            console.print(f"\n[green]✓ Video loaded successfully[/green]")
            console.print(f"  Duration: {self.project.timeline.video_duration:.2f}s")
            console.print(f"  Resolution: {info['width']}x{info['height']}")
            console.print(f"  FPS: {info['fps']}")
            console.print(f"  Codec: {info['codec']}")

            # Save project
            self.project.save()
            console.print(f"[green]✓ Project created: {project_name}[/green]")

            await self.project_menu()

        except Exception as e:
            console.print(f"[red]Error creating project: {e}[/red]")
            logger.error(f"Error creating project: {e}")

    async def open_existing_project(self):
        """Open an existing project"""
        console.print("\n[bold green]Open Project[/bold green]")

        # List available projects
        projects = Project.list_projects()

        if not projects:
            console.print("[yellow]No projects found[/yellow]")
            return

        # Display projects
        table = Table(title="Available Projects")
        table.add_column("No.", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Video", style="white")
        table.add_column("Segments", style="yellow")
        table.add_column("Modified", style="magenta")

        for i, proj in enumerate(projects, 1):
            table.add_row(
                str(i),
                proj["name"],
                Path(proj["video_path"]).name,
                str(proj["segments_count"]),
                proj["modified_at"][:19]
            )

        console.print(table)

        # Select project
        choice = IntPrompt.ask(
            "Select project number (0 to cancel)",
            default=1
        )

        if choice == 0 or choice > len(projects):
            return

        # Load project
        project_name = projects[choice - 1]["name"]

        try:
            self.project = Project.load(project_name)

            if self.project:
                console.print(f"[green]✓ Project loaded: {project_name}[/green]")
                await self.project_menu()
            else:
                console.print(f"[red]Failed to load project[/red]")

        except Exception as e:
            console.print(f"[red]Error loading project: {e}[/red]")
            logger.error(f"Error loading project: {e}")

    def list_projects(self):
        """List all projects"""
        console.print("\n[bold green]All Projects[/bold green]")

        projects = Project.list_projects()

        if not projects:
            console.print("[yellow]No projects found[/yellow]")
            return

        table = Table()
        table.add_column("Name", style="green")
        table.add_column("Video", style="white")
        table.add_column("Segments", style="yellow")
        table.add_column("Created", style="cyan")
        table.add_column("Modified", style="magenta")

        for proj in projects:
            table.add_row(
                proj["name"],
                Path(proj["video_path"]).name,
                str(proj["segments_count"]),
                proj["created_at"][:19],
                proj["modified_at"][:19]
            )

        console.print(table)

    async def project_menu(self):
        """Project-specific menu"""
        while True:
            console.print(f"\n[bold cyan]Project: {self.project.name}[/bold cyan]")
            console.print(f"Video: {Path(self.project.video_path).name} (Duration: {self.project.timeline.video_duration:.2f}s)")
            console.print(f"Segments: {len(self.project.timeline.segments)}")

            # Show quick segment overview
            if self.project.timeline.segments:
                total_coverage = sum(seg.duration for seg in self.project.timeline.segments)
                console.print(f"[dim]Total segment coverage: {total_coverage:.2f}s ({(total_coverage/self.project.timeline.video_duration*100):.1f}%)[/dim]")

            console.print("\n1. Add Segment")
            console.print("2. List Segments")
            console.print("3. Edit Segment")
            console.print("4. Delete Segment")
            console.print("5. Generate Voice-Overs")
            console.print("6. Export Video")
            console.print("7. Project Settings")
            console.print("8. Save Project")
            console.print("9. Back to Main Menu")

            choice = Prompt.ask("Select option", choices=[str(i) for i in range(1, 10)])

            if choice == "1":
                await self.add_segment()
            elif choice == "2":
                self.list_segments()
            elif choice == "3":
                await self.edit_segment()
            elif choice == "4":
                self.delete_segment()
            elif choice == "5":
                await self.generate_voiceovers()
            elif choice == "6":
                await self.export_video()
            elif choice == "7":
                self.project_settings()
            elif choice == "8":
                self.project.save()
                console.print("[green]✓ Project saved[/green]")
            elif choice == "9":
                self.project.save()
                break

    async def _select_voice_for_language(self, language: str) -> str:
        """
        Show interactive voice selection with preview for given language
        Uses the new VoiceSelector utility for enhanced UX
        """
        from utils.voice_selector import select_voice_interactive

        voice = await select_voice_interactive(
            self.tts_service,
            language,
            current_voice=None
        )

        # If user cancelled, use default
        if voice is None:
            voice = self.tts_service.best_voices.get(language, "en-US-AvaMultilingualNeural")
            console.print(f"[dim]Using default voice: {voice}[/dim]")

        return voice

    def _get_subtitle_styling_options(self, current_font: str = None) -> dict:
        """
        Get subtitle styling options from user
        Returns dict with font, size, color, position
        """
        from utils.google_fonts import get_font_from_input_with_install
        from backend.subtitle_utils import SubtitleUtils

        console.print("\n[bold cyan]Subtitle Styling Options[/bold cyan]")
        console.print("[dim]Press Enter to use defaults[/dim]\n")

        # Font selection
        console.print("[yellow]Font Options:[/yellow]")
        console.print("  1. Use default font for language")
        console.print("  2. Enter Google Fonts URL or font name")

        use_custom_font = Confirm.ask("Use custom font?", default=False)

        if use_custom_font:
            console.print("\n[cyan]Enter Google Font URL or font name:[/cyan]")
            console.print("[dim]Example: https://fonts.googleapis.com/css2?family=Roboto:wght@400[/dim]")
            console.print("[dim]Or just: Roboto[/dim]\n")

            font_input = input("Font: ").strip()

            if font_input:
                font = get_font_from_input_with_install(font_input, current_font or "Roboto")
                console.print(f"[green]✓ Using font: {font}[/green]")
            else:
                font = current_font or "Roboto"
        else:
            font = current_font or "Roboto"

        # Size
        size = IntPrompt.ask("Font size", default=20)

        # Color selection
        console.print("\n[yellow]Text Color:[/yellow]")
        console.print("  1. White (default)")
        console.print("  2. Yellow")
        console.print("  3. Cyan")
        console.print("  4. Custom hex (e.g., &H00FF00FF for magenta)")

        color_choice = IntPrompt.ask("Select color", default=1, choices=["1", "2", "3", "4"])

        color_map = {
            1: "&H00FFFFFF",  # White
            2: "&H0000FFFF",  # Yellow
            3: "&H00FFFF00",  # Cyan
        }

        if color_choice == 4:
            color = Prompt.ask("Enter color code", default="&H00FFFFFF")
        else:
            color = color_map[color_choice]

        # Position
        position = IntPrompt.ask("Position from bottom (pixels)", default=30)

        # Border/Outline configuration
        console.print("\n[yellow]Border/Outline Options:[/yellow]")
        border_enabled = Confirm.ask("Enable border/outline?", default=True)

        if border_enabled:
            # Border style
            console.print("\n[cyan]Border Style:[/cyan]")
            console.print("  1. Outline with shadow (default)")
            console.print("  2. Outline only (no shadow)")
            console.print("  3. Opaque box background")
            border_style_choice = IntPrompt.ask("Select style", default=1, choices=["1", "2", "3"])

            border_style = 1 if border_style_choice in [1, 2] else 3

            # Outline width
            from rich.prompt import FloatPrompt
            outline_width = FloatPrompt.ask("Outline/border width (pixels)", default=2.0)

            # Outline color
            console.print("\n[cyan]Outline/Border Color:[/cyan]")
            console.print("  1. Black (default)")
            console.print("  2. White")
            console.print("  3. Dark gray")
            console.print("  4. Custom hex")
            outline_color_choice = IntPrompt.ask("Select outline color", default=1, choices=["1", "2", "3", "4"])

            outline_color_map = {
                1: "&H00000000",  # Black
                2: "&H00FFFFFF",  # White
                3: "&H00404040",  # Dark gray
            }

            if outline_color_choice == 4:
                outline_color = Prompt.ask("Enter color code (ASS format)", default="&H00000000")
            else:
                outline_color = outline_color_map[outline_color_choice]

            # Shadow
            if border_style_choice == 1:  # Outline with shadow
                shadow = FloatPrompt.ask("Shadow distance (pixels, 0=no shadow)", default=1.0)
            else:
                shadow = 0.0

        else:
            # No border
            border_style = 1
            outline_width = 0.0
            outline_color = "&H00000000"
            shadow = 0.0

        return {
            'font': font,
            'size': size,
            'color': color,
            'position': position,
            'border_enabled': border_enabled,
            'border_style': border_style,
            'outline_width': outline_width,
            'outline_color': outline_color,
            'shadow': shadow
        }

    async def add_segment(self):
        """Add a new segment to timeline"""
        console.print("\n[bold green]Add Segment[/bold green]")

        try:
            # Get segment details
            name = Prompt.ask("Segment name", default=f"Segment {len(self.project.timeline.segments) + 1}")

            # Get segment timing with immediate validation
            while True:
                start_time = FloatPrompt.ask("Start time (seconds)", default=0.0)
                end_time = FloatPrompt.ask("End time (seconds)")

                # Immediate validation
                validation_result = self._validate_segment_timing(start_time, end_time)
                if validation_result['valid']:
                    break

                # Handle validation errors
                console.print(f"[red]✗ {validation_result['error']}[/red]")

                if validation_result['type'] == 'exceeds_video':
                    console.print(f"[yellow]Video duration: {self.project.timeline.video_duration:.2f}s[/yellow]")
                    console.print(f"[yellow]Your segment: {start_time:.2f}s - {end_time:.2f}s[/yellow]")
                    if not Confirm.ask("Try again with different times?", default=True):
                        console.print("[yellow]Segment creation cancelled[/yellow]")
                        return

                elif validation_result['type'] == 'overlaps':
                    console.print(f"[yellow]Overlapping segments:[/yellow]")
                    for seg in validation_result['overlapping_segments']:
                        console.print(f"  • {seg.name}: {seg.start_time:.2f}s - {seg.end_time:.2f}s")

                    # Provide options to handle overlap
                    handled = await self._handle_segment_overlap(
                        start_time, end_time, validation_result['overlapping_segments']
                    )
                    if handled == 'retry':
                        continue
                    elif handled == 'cancel':
                        console.print("[yellow]Segment creation cancelled[/yellow]")
                        return
                    else:
                        # Overlap was resolved by removing/editing segments
                        break

                elif validation_result['type'] == 'invalid_times':
                    if not Confirm.ask("Try again with different times?", default=True):
                        console.print("[yellow]Segment creation cancelled[/yellow]")
                        return

            text = Prompt.ask("Text for voice-over")

            # Language selection with interactive list
            import inquirer
            from inquirer import themes

            language_choices = [
                ('English (en)', 'en'),
                ('Hindi (hi)', 'hi'),
                ('Tamil (ta)', 'ta'),
                ('Telugu (te)', 'te'),
                ('Kannada (kn)', 'kn'),
                ('Malayalam (ml)', 'ml'),
                ('French (fr)', 'fr'),
                ('Spanish (es)', 'es'),
                ('German (de)', 'de'),
                ('Korean (ko)', 'ko'),
                ('Japanese (ja)', 'ja'),
                ('Chinese (zh)', 'zh'),
                ('Arabic (ar)', 'ar'),
                ('Russian (ru)', 'ru'),
                ('Portuguese (pt)', 'pt'),
                ('Italian (it)', 'it'),
            ]

            questions = [
                inquirer.List(
                    'language',
                    message='Select language',
                    choices=language_choices,
                    default='en',
                    carousel=True
                )
            ]

            answer = inquirer.prompt(questions, theme=themes.GreenPassion())
            if not answer:
                console.print("[yellow]Segment creation cancelled[/yellow]")
                return

            language = answer['language']
            console.print(f"[green]✓ Selected language: {language}[/green]")

            # Voice selection (now always uses interactive selector)
            voice = await self._select_voice_for_language(language)

            # Optional parameters
            rate = Prompt.ask("Rate (e.g., +10%, -10%)", default="+0%")
            volume = Prompt.ask("Volume (e.g., +10%, -10%)", default="+0%")
            pitch = Prompt.ask("Pitch (e.g., +5Hz, -5Hz)", default="+0Hz")

            # Subtitle styling
            if Confirm.ask("Configure subtitle styling?", default=False):
                styling = self._get_subtitle_styling_options()
            else:
                from backend.subtitle_utils import SubtitleUtils
                # Use language-specific default font with default border
                styling = {
                    'font': SubtitleUtils.get_language_specific_font(language),
                    'size': 20,
                    'color': "&H00FFFFFF",
                    'position': 30,
                    'border_enabled': True,
                    'border_style': 1,
                    'outline_width': 2.0,
                    'outline_color': "&H00000000",
                    'shadow': 0.0
                }

            segment = self.project.timeline.add_segment(
                start=start_time,
                end=end_time,
                text=text,
                voice=voice,
                language=language,
                name=name
            )

            # Set voice parameters
            segment.rate = rate
            segment.volume = volume
            segment.pitch = pitch

            # Set subtitle styling
            segment.subtitle_font = styling['font']
            segment.subtitle_size = styling['size']
            segment.subtitle_color = styling['color']
            segment.subtitle_position = styling['position']

            # Set border styling
            segment.subtitle_border_enabled = styling.get('border_enabled', True)
            segment.subtitle_border_style = styling.get('border_style', 1)
            segment.subtitle_outline_width = styling.get('outline_width', 2.0)
            segment.subtitle_outline_color = styling.get('outline_color', "&H00000000")
            segment.subtitle_shadow = styling.get('shadow', 0.0)

            # Save project immediately after creating segment
            self.project.save()

            console.print(f"[green]✓ Segment added: {name}[/green]")
            console.print(f"  Time: {segment.start_time:.2f}s - {segment.end_time:.2f}s (Duration: {segment.duration:.2f}s)")
            console.print(f"  Voice: {voice}")
            console.print(f"  Subtitle font: {styling['font']}")

            # Ask if user wants to generate audio now
            if Confirm.ask("Generate voice-over audio now?", default=True):
                await self.generate_segment_audio(segment)

            # Save again after audio generation (in case segment was modified)
            self.project.save()

        except KeyboardInterrupt:
            console.print("\n[yellow]Segment creation cancelled[/yellow]")
        except Exception as e:
            console.print(f"[red]Error adding segment: {e}[/red]")
            logger.error(f"Error in add_segment: {e}")

    def _validate_segment_timing(self, start_time: float, end_time: float) -> dict:
        """
        Validate segment timing immediately after input
        Returns dict with validation result
        """
        # Check basic timing validity
        if start_time < 0:
            return {
                'valid': False,
                'type': 'invalid_times',
                'error': 'Start time cannot be negative'
            }

        if end_time <= start_time:
            return {
                'valid': False,
                'type': 'invalid_times',
                'error': 'End time must be greater than start time'
            }

        # Check if exceeds video duration
        if end_time > self.project.timeline.video_duration:
            return {
                'valid': False,
                'type': 'exceeds_video',
                'error': f"Segment end ({end_time:.2f}s) exceeds video duration ({self.project.timeline.video_duration:.2f}s)"
            }

        # Check for overlaps with existing segments
        overlapping_segments = []
        for segment in self.project.timeline.segments:
            # Check if new segment overlaps with existing segment
            if not (end_time <= segment.start_time or start_time >= segment.end_time):
                overlapping_segments.append(segment)

        if overlapping_segments:
            return {
                'valid': False,
                'type': 'overlaps',
                'error': f"Segment overlaps with {len(overlapping_segments)} existing segment(s)",
                'overlapping_segments': overlapping_segments
            }

        return {'valid': True}

    async def _handle_segment_overlap(self, start_time: float, end_time: float, overlapping_segments: list) -> str:
        """
        Handle segment overlap with user interaction
        Returns: 'retry', 'cancel', or 'resolved'
        """
        console.print("\n[bold yellow]Segment Overlap Detected[/bold yellow]")
        console.print(f"New segment: {start_time:.2f}s - {end_time:.2f}s")
        console.print(f"Video duration: {self.project.timeline.video_duration:.2f}s\n")

        console.print("[cyan]Options:[/cyan]")
        console.print("1. Re-enter segment times")
        console.print("2. Remove overlapping segment(s)")
        console.print("3. Edit overlapping segment(s)")
        console.print("4. Cancel")

        choice = Prompt.ask("Select option", choices=["1", "2", "3", "4"], default="1")

        if choice == "1":
            return 'retry'
        elif choice == "2":
            # Remove overlapping segments
            console.print("\n[yellow]The following segments will be removed:[/yellow]")
            for seg in overlapping_segments:
                console.print(f"  • {seg.name}: {seg.start_time:.2f}s - {seg.end_time:.2f}s")

            if Confirm.ask("Confirm removal?", default=False):
                for seg in overlapping_segments:
                    self.project.timeline.remove_segment(seg.id)
                    console.print(f"[green]✓ Removed: {seg.name}[/green]")
                self.project.save()
                return 'resolved'
            else:
                return 'cancel'

        elif choice == "3":
            # Edit overlapping segments
            console.print("\n[cyan]Edit Overlapping Segments[/cyan]")
            for i, seg in enumerate(overlapping_segments, 1):
                console.print(f"\n[bold]{i}. {seg.name}[/bold]")
                console.print(f"   Current: {seg.start_time:.2f}s - {seg.end_time:.2f}s")
                console.print(f"   Duration: {seg.duration:.2f}s")

                console.print("\n   Options:")
                console.print("   a. Adjust start time")
                console.print("   b. Adjust end time")
                console.print("   c. Remove this segment")
                console.print("   d. Skip")

                edit_choice = Prompt.ask("Select option", choices=["a", "b", "c", "d"], default="d")

                if edit_choice == "a":
                    new_start = FloatPrompt.ask("New start time", default=seg.start_time)
                    if new_start != seg.start_time:
                        seg.start_time = new_start
                        console.print(f"[green]✓ Updated start time to {new_start:.2f}s[/green]")
                        self.project.save()

                elif edit_choice == "b":
                    new_end = FloatPrompt.ask("New end time", default=seg.end_time)
                    if new_end != seg.end_time:
                        seg.end_time = new_end
                        console.print(f"[green]✓ Updated end time to {new_end:.2f}s[/green]")
                        self.project.save()

                elif edit_choice == "c":
                    self.project.timeline.remove_segment(seg.id)
                    console.print(f"[green]✓ Removed: {seg.name}[/green]")
                    self.project.save()

            return 'retry'  # Ask user to re-enter times to verify no more overlaps

        else:
            return 'cancel'

    async def _validate_audio_duration(self, segment):
        """
        Validate generated audio duration against segment duration
        Handle cases where audio exceeds segment duration
        """
        from backend.ffmpeg_utils import FFmpegUtils

        # Get audio duration
        if not segment.audio_path or not Path(segment.audio_path).exists():
            return

        audio_duration = FFmpegUtils.get_media_duration(segment.audio_path)
        if audio_duration is None:
            console.print("[yellow]⚠ Could not determine audio duration[/yellow]")
            return

        segment_duration = segment.end_time - segment.start_time

        # Show duration info
        console.print(f"[dim]Segment duration: {segment_duration:.2f}s[/dim]")
        console.print(f"[dim]Audio duration: {audio_duration:.2f}s[/dim]")

        # Check if audio exceeds segment duration
        if audio_duration > segment_duration:
            console.print(f"[yellow]⚠ Audio duration ({audio_duration:.2f}s) exceeds segment duration ({segment_duration:.2f}s)[/yellow]")

            # Check if there are following segments
            following_segments = [
                seg for seg in self.project.timeline.segments
                if seg.start_time >= segment.end_time
            ]

            if not following_segments:
                # No following segments - can safely extend
                console.print("[cyan]No following segments detected.[/cyan]")
                if Confirm.ask(f"Extend segment to fit audio ({audio_duration:.2f}s)?", default=True):
                    old_end = segment.end_time
                    segment.end_time = segment.start_time + audio_duration

                    # Check if extended segment exceeds video duration
                    if segment.end_time > self.project.timeline.video_duration:
                        console.print(f"[yellow]⚠ Extended segment would exceed video duration[/yellow]")
                        segment.end_time = min(self.project.timeline.video_duration, segment.start_time + audio_duration)
                        console.print(f"[yellow]Capping segment end at video duration: {segment.end_time:.2f}s[/yellow]")

                    console.print(f"[green]✓ Segment '{segment.name}' extended: {old_end:.2f}s → {segment.end_time:.2f}s (Duration: {segment.duration:.2f}s)[/green]")
                    logger.info(f"Extended segment '{segment.name}' from {old_end:.2f}s to {segment.end_time:.2f}s")
                    self.project.save()
                else:
                    console.print("[yellow]⚠ Audio will be cut to fit segment duration during export[/yellow]")

            else:
                # Following segments exist - need user decision
                console.print(f"[yellow]⚠ {len(following_segments)} following segment(s) detected:[/yellow]")
                for seg in following_segments[:3]:  # Show first 3
                    console.print(f"  • {seg.name}: {seg.start_time:.2f}s - {seg.end_time:.2f}s")
                if len(following_segments) > 3:
                    console.print(f"  ... and {len(following_segments) - 3} more")

                console.print("\n[cyan]Options:[/cyan]")
                console.print("1. Keep current segment duration (audio will be cut)")
                console.print("2. Extend segment and adjust following segments")
                console.print("3. Shorten audio by adjusting voice rate")
                console.print("4. Edit segment manually")

                choice = Prompt.ask("Select option", choices=["1", "2", "3", "4"], default="1")

                if choice == "1":
                    console.print("[yellow]Audio will be cut to fit segment duration during export[/yellow]")

                elif choice == "2":
                    # Extend segment
                    old_end = segment.end_time
                    new_end = segment.start_time + audio_duration

                    # Check space available
                    next_segment = following_segments[0]
                    available_space = next_segment.start_time - segment.end_time

                    if audio_duration - segment_duration <= available_space:
                        segment.end_time = new_end
                        console.print(f"[green]✓ Segment extended: {old_end:.2f}s → {new_end:.2f}s[/green]")
                        self.project.save()
                    else:
                        console.print(f"[yellow]Not enough space. Available: {available_space:.2f}s, Needed: {audio_duration - segment_duration:.2f}s[/yellow]")
                        if Confirm.ask("Adjust following segments?", default=False):
                            # Push following segments
                            shift_amount = audio_duration - segment_duration - available_space
                            segment.end_time = new_end
                            for seg in following_segments:
                                seg.start_time += shift_amount
                                seg.end_time += shift_amount
                                console.print(f"[green]✓ Shifted: {seg.name}[/green]")
                            self.project.save()
                        else:
                            console.print("[yellow]Audio will be cut to fit segment duration[/yellow]")

                elif choice == "3":
                    # Suggest rate adjustment
                    rate_adjustment = (segment_duration / audio_duration - 1) * 100
                    console.print(f"[cyan]Suggested rate adjustment: {rate_adjustment:+.0f}%[/cyan]")
                    new_rate = Prompt.ask("New rate", default=f"{rate_adjustment:+.0f}%")
                    segment.rate = new_rate
                    console.print("[yellow]Please regenerate audio with new rate[/yellow]")
                    if Confirm.ask("Regenerate now?", default=True):
                        await self.generate_segment_audio(segment)

                elif choice == "4":
                    console.print("[cyan]Please use 'Edit Segment' from the menu to adjust timing[/cyan]")

        elif audio_duration < segment_duration * 0.5:
            # Audio is significantly shorter than segment
            console.print(f"[yellow]ℹ Audio duration ({audio_duration:.2f}s) is much shorter than segment duration ({segment_duration:.2f}s)[/yellow]")
            if Confirm.ask("Shorten segment to fit audio?", default=False):
                segment.end_time = segment.start_time + audio_duration
                console.print(f"[green]✓ Segment shortened to {audio_duration:.2f}s[/green]")
                self.project.save()

    def list_segments(self):
        """List all segments in timeline"""
        console.print("\n[bold green]Segments[/bold green]")
        console.print(f"[dim]Video duration: {self.project.timeline.video_duration:.2f}s[/dim]\n")

        if not self.project.timeline.segments:
            console.print("[yellow]No segments added yet[/yellow]")
            return

        table = Table()
        table.add_column("No.", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Start", style="yellow")
        table.add_column("End", style="yellow")
        table.add_column("Duration", style="magenta")
        table.add_column("Text", style="white")
        table.add_column("Audio", style="blue")

        for i, seg in enumerate(self.project.timeline.segments, 1):
            audio_status = "✓" if seg.audio_path and Path(seg.audio_path).exists() else "✗"

            # Get audio duration if available
            audio_info = ""
            if seg.audio_path and Path(seg.audio_path).exists():
                from backend.ffmpeg_utils import FFmpegUtils
                audio_dur = FFmpegUtils.get_media_duration(seg.audio_path)
                if audio_dur:
                    if audio_dur > seg.duration:
                        audio_info = f" ({audio_dur:.1f}s⚠)"
                    else:
                        audio_info = f" ({audio_dur:.1f}s)"

            table.add_row(
                str(i),
                seg.name,
                f"{seg.start_time:.2f}s",
                f"{seg.end_time:.2f}s",
                f"{seg.duration:.2f}s",
                seg.text[:40] + "..." if len(seg.text) > 40 else seg.text,
                audio_status + audio_info
            )

        console.print(table)

        # Show summary
        total_duration = sum(seg.duration for seg in self.project.timeline.segments)
        console.print(f"\n[dim]Total segment duration: {total_duration:.2f}s[/dim]")

        # Check for overlaps
        overlaps = self.project.timeline.check_overlaps()
        if overlaps:
            console.print(f"[red]⚠ {len(overlaps)} overlap(s) detected![/red]")

    async def edit_segment(self):
        """Edit an existing segment"""
        if not self.project.timeline.segments:
            console.print("[yellow]No segments to edit[/yellow]")
            return

        self.list_segments()

        segment_num = IntPrompt.ask("Select segment number (0 to cancel)")

        if segment_num == 0 or segment_num > len(self.project.timeline.segments):
            return

        segment = self.project.timeline.segments[segment_num - 1]

        # Validate and fix invalid language codes
        valid_languages = ['en', 'hi', 'ta', 'te', 'kn', 'ml', 'fr', 'es', 'de', 'ko', 'ja', 'zh', 'ar', 'ru', 'pt', 'it']
        if segment.language not in valid_languages:
            console.print(f"[yellow]⚠ Invalid language code detected: '{segment.language}'[/yellow]")
            console.print(f"[yellow]Resetting to default: 'en'[/yellow]")
            segment.language = 'en'
            self.project.save()

        console.print(f"\n[bold cyan]Editing: {segment.name}[/bold cyan]")
        console.print(f"[dim]Current language: {segment.language}[/dim]")
        console.print("[dim]Note: Text will be REPLACED (not appended)[/dim]")
        console.print("[yellow]Current text:[/yellow]")
        console.print(f"  {segment.text[:150]}{'...' if len(segment.text) > 150 else ''}\n")

        try:
            # Get text input with multiline support
            console.print("[cyan]Enter new text:[/cyan]")
            console.print("[dim]- Press Enter on empty line to keep current text[/dim]")
            console.print("[dim]- Type/paste text and press Enter when done[/dim]")
            console.print("[dim]- Multiline paste is automatically joined[/dim]\n")

            # Use multiline input handler
            text_input = self._get_multiline_input(segment.text)

            if text_input is None:
                console.print("[yellow]Edit cancelled[/yellow]")
                return

            # Sanitize text: remove problematic characters
            text = self._sanitize_text(text_input)

            if text != text_input:
                console.print("[yellow]Some special characters were removed for compatibility[/yellow]")

            # Show what will be saved (first 200 chars)
            preview = text[:200] + ('...' if len(text) > 200 else '')
            console.print(f"\n[green]Text to save ({len(text)} chars):[/green]")
            console.print(f"  {preview}")

            # Confirm if it looks correct
            if not Confirm.ask("\nIs this correct?", default=True):
                console.print("[yellow]Edit cancelled[/yellow]")
                return

            rate = Prompt.ask("Rate", default=segment.rate)
            volume = Prompt.ask("Volume", default=segment.volume)
            pitch = Prompt.ask("Pitch", default=segment.pitch)

            # Language change option
            change_language = Confirm.ask("\nChange language?", default=False)
            if change_language:
                # Use inquirer for language selection
                import inquirer
                from inquirer import themes

                language_choices = [
                    ('English (en)', 'en'),
                    ('Hindi (hi)', 'hi'),
                    ('Tamil (ta)', 'ta'),
                    ('Telugu (te)', 'te'),
                    ('Kannada (kn)', 'kn'),
                    ('Malayalam (ml)', 'ml'),
                    ('French (fr)', 'fr'),
                    ('Spanish (es)', 'es'),
                    ('German (de)', 'de'),
                    ('Korean (ko)', 'ko'),
                    ('Japanese (ja)', 'ja'),
                    ('Chinese (zh)', 'zh'),
                    ('Arabic (ar)', 'ar'),
                    ('Russian (ru)', 'ru'),
                    ('Portuguese (pt)', 'pt'),
                    ('Italian (it)', 'it'),
                ]

                questions = [
                    inquirer.List(
                        'language',
                        message='Select language',
                        choices=language_choices,
                        default=segment.language,
                        carousel=True
                    )
                ]

                try:
                    answer = inquirer.prompt(questions, theme=themes.GreenPassion())
                    if answer:
                        new_language = answer['language']
                        segment.language = new_language
                        console.print(f"[green]✓ Language changed to: {new_language}[/green]")
                    else:
                        # User cancelled
                        new_language = segment.language
                except KeyboardInterrupt:
                    console.print("\n[yellow]Language change cancelled[/yellow]")
                    new_language = segment.language
            else:
                new_language = segment.language

            # Voice selection
            change_voice = Confirm.ask("\nChange voice?", default=False)
            if change_voice:
                from utils.voice_selector import select_voice_interactive
                voice = await select_voice_interactive(
                    self.tts_service,
                    new_language,
                    segment.voice_id
                )
                if voice is None:
                    # User cancelled, keep current voice
                    voice = segment.voice_id
            else:
                voice = segment.voice_id

            # Subtitle styling
            change_styling = Confirm.ask("Change subtitle styling?", default=False)
            if change_styling:
                styling = self._get_subtitle_styling_options(segment.subtitle_font)
            else:
                styling = None

        except KeyboardInterrupt:
            console.print("\n[yellow]Edit cancelled[/yellow]")
            return
        except Exception as e:
            console.print(f"[red]Error during input: {e}[/red]")
            logger.error(f"Error in edit_segment: {e}")
            return

        # Update segment
        old_text = segment.text
        old_voice = segment.voice_id
        segment.text = text
        segment.rate = rate
        segment.volume = volume
        segment.pitch = pitch
        segment.voice_id = voice

        # Update subtitle styling if changed
        if styling:
            segment.subtitle_font = styling['font']
            segment.subtitle_size = styling['size']
            segment.subtitle_color = styling['color']
            segment.subtitle_position = styling['position']

            # Update border styling
            segment.subtitle_border_enabled = styling.get('border_enabled', True)
            segment.subtitle_border_style = styling.get('border_style', 1)
            segment.subtitle_outline_width = styling.get('outline_width', 2.0)
            segment.subtitle_outline_color = styling.get('outline_color', "&H00000000")
            segment.subtitle_shadow = styling.get('shadow', 0.0)

            console.print(f"[green]✓ Subtitle styling updated: {styling['font']}[/green]")

        # Save project immediately
        self.project.save()
        console.print("[green]✓ Segment updated and saved[/green]")

        # Regenerate audio if text or voice changed
        text_changed = (old_text != text)
        voice_changed = (old_voice != voice)

        if text_changed or voice_changed:
            if text_changed:
                console.print("[yellow]Text changed - audio regeneration recommended[/yellow]")
            if voice_changed:
                console.print("[yellow]Voice changed - audio regeneration recommended[/yellow]")

        if Confirm.ask("Regenerate voice-over audio?", default=(text_changed or voice_changed)):
            await self.generate_segment_audio(segment)
            # Save again after audio generation
            self.project.save()

    def _get_multiline_input(self, default_text: str) -> str:
        """
        Get multiline text input from user
        Handles pasted multiline content by reading all lines until empty line
        Returns None if cancelled with Ctrl+C
        """
        lines = []

        try:
            while True:
                try:
                    line = input()

                    # If first line is empty, keep default
                    if not line.strip() and len(lines) == 0:
                        return default_text

                    # If we have lines and get empty line, we're done
                    if not line.strip() and len(lines) > 0:
                        break

                    # Add line to collection
                    lines.append(line)

                except EOFError:
                    # Ctrl+D pressed - if we have lines, use them
                    if lines:
                        break
                    else:
                        return default_text

        except KeyboardInterrupt:
            # Ctrl+C pressed - cancel
            return None

        # Join all lines with spaces (not newlines, for subtitle compatibility)
        text = ' '.join(lines)

        # Remove extra whitespace
        text = ' '.join(text.split())

        return text.strip()

    def _sanitize_text(self, text: str) -> str:
        """
        Remove problematic characters that cause input hangs
        Keeps alphanumeric, punctuation, and common symbols
        """
        import re

        # Remove emojis and other problematic unicode
        # Keep: letters, numbers, spaces, common punctuation
        sanitized = re.sub(r'[^\w\s\.,!?\-\'\";:()\[\]]+', '', text)

        # Remove multiple spaces
        sanitized = ' '.join(sanitized.split())

        return sanitized.strip()

    def delete_segment(self):
        """Delete a segment"""
        if not self.project.timeline.segments:
            console.print("[yellow]No segments to delete[/yellow]")
            return

        self.list_segments()

        segment_num = IntPrompt.ask("Select segment number (0 to cancel)")

        if segment_num == 0 or segment_num > len(self.project.timeline.segments):
            return

        segment = self.project.timeline.segments[segment_num - 1]

        if Confirm.ask(f"Delete segment '{segment.name}'?", default=False):
            self.project.timeline.remove_segment(segment.id)
            console.print("[green]✓ Segment deleted[/green]")

    async def generate_segment_audio(self, segment):
        """Generate audio for a single segment"""
        try:
            with console.status(f"[bold green]Generating audio for '{segment.name}'..."):
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

            console.print(f"[green]✓ Audio generated: {Path(audio_path).name}[/green]")

            # Validate audio duration vs segment duration
            await self._validate_audio_duration(segment)

        except Exception as e:
            console.print(f"[red]Error generating audio: {e}[/red]")

    async def generate_voiceovers(self):
        """Generate voice-overs for all segments"""
        console.print("\n[bold green]Generate Voice-Overs[/bold green]")

        if not self.project.timeline.segments:
            console.print("[yellow]No segments to process[/yellow]")
            return

        # Count segments needing audio generation
        segments_to_generate = [
            seg for seg in self.project.timeline.segments
            if not seg.audio_path or not Path(seg.audio_path).exists()
        ]

        if not segments_to_generate:
            console.print("[green]All segments already have audio generated[/green]")
            return

        console.print(f"Segments needing audio: {len(segments_to_generate)}")

        if not Confirm.ask("Generate voice-overs?", default=True):
            return

        # Generate audio for all segments
        with suppress_console_logs():
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console
            ) as progress:
                task = progress.add_task("Generating audio...", total=len(segments_to_generate))

                for segment in segments_to_generate:
                    try:
                        progress.update(task, description=f"Generating: {segment.name}")

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

                        progress.advance(task)

                    except Exception as e:
                        console.print(f"[red]Failed: {segment.name} - {e}[/red]")

        console.print("[green]✓ Voice-over generation complete[/green]")

    async def export_video(self):
        """Export the final video"""
        console.print("\n[bold green]Export Video[/bold green]")

        # Validate timeline
        errors = self.project.timeline.validate_timeline()
        if errors:
            console.print("[red]Timeline validation errors:[/red]")
            for error in errors:
                console.print(f"  • {error}")

            if not Confirm.ask("Continue export anyway?", default=False):
                return

        # Get export settings
        output_path = Prompt.ask("Output file path", default=f"{self.project.name}_output.mp4")

        console.print("\nQuality presets:")
        console.print("1. Lossless (best quality, largest file)")
        console.print("2. High (near-lossless)")
        console.print("3. Balanced (good quality, smaller file)")

        quality_choice = Prompt.ask("Quality", choices=["1", "2", "3"], default="3")
        quality_map = {"1": "lossless", "2": "high", "3": "balanced"}
        quality = quality_map[quality_choice]

        include_subtitles = Confirm.ask("Include subtitles?", default=True)

        background_music = None
        if Confirm.ask("Add background music?", default=False):
            background_music = Prompt.ask("Background music file path")
            if not Path(background_music).exists():
                console.print("[yellow]Warning: Background music file not found[/yellow]")
                background_music = None

        # Start export
        console.print("\n[bold]Starting export...[/bold]")

        pipeline = ExportPipeline(self.project)

        try:
            with suppress_console_logs():
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    console=console
                ) as progress:
                    task = progress.add_task("Exporting...", total=100)

                    def progress_callback(message: str, percent: int):
                        progress.update(task, description=message, completed=percent)

                    success = await pipeline.export(
                        output_path=output_path,
                        quality=quality,
                        include_subtitles=include_subtitles,
                        background_music_path=background_music,
                        progress_callback=progress_callback
                    )

            if success:
                console.print(f"\n[green]✓ Export complete: {output_path}[/green]")

                # Show file info
                if Path(output_path).exists():
                    size_mb = Path(output_path).stat().st_size / 1024 / 1024
                    console.print(f"  File size: {size_mb:.1f} MB")
            else:
                console.print("[red]✗ Export failed[/red]")

        except Exception as e:
            console.print(f"[red]Export error: {e}[/red]")
            logger.error(f"Export error: {e}")

    def project_settings(self):
        """Configure project settings"""
        console.print("\n[bold green]Project Settings[/bold green]")

        console.print(f"Export Quality: {self.project.export_quality}")
        console.print(f"Include Subtitles: {self.project.include_subtitles}")
        console.print(f"Background Music: {self.project.background_music_path or 'None'}")

        if Confirm.ask("Edit settings?", default=False):
            quality = Prompt.ask(
                "Export quality",
                choices=["lossless", "high", "balanced"],
                default=self.project.export_quality
            )
            self.project.export_quality = quality

            self.project.include_subtitles = Confirm.ask(
                "Include subtitles",
                default=self.project.include_subtitles
            )

            if Confirm.ask("Set background music?", default=False):
                music_path = Prompt.ask("Background music file path")
                if Path(music_path).exists():
                    self.project.background_music_path = music_path
                else:
                    console.print("[yellow]File not found[/yellow]")

            console.print("[green]✓ Settings updated[/green]")

    async def run(self):
        """Main application loop"""
        self.show_banner()

        while True:
            try:
                choice = self.show_main_menu()

                if choice == "1":
                    await self.create_new_project()
                elif choice == "2":
                    await self.open_existing_project()
                elif choice == "3":
                    self.list_projects()
                elif choice == "4":
                    console.print("\n[cyan]Thank you for using Console Video Editor![/cyan]")
                    break

            except KeyboardInterrupt:
                console.print("\n\n[yellow]Operation cancelled[/yellow]")
                if Confirm.ask("Exit application?", default=False):
                    break
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")
                logger.error(f"Application error: {e}")


async def async_main():
    """Async entry point"""
    editor = ConsoleEditor()
    await editor.run()


def main():
    """
    Main entry point for console script
    This function is called when using: console-video-editor or cvd
    """
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
