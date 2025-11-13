"""Interactive Voice Selector with Preview - Enhanced UX for voice selection"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Optional
import inquirer
from inquirer import themes
import pygame
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from utils.logger import logger

console = Console()


class VoiceSelector:
    """
    Interactive voice selector with preview capability
    Provides arrow-key navigation and audio preview for voice selection
    """

    def __init__(self, tts_service):
        """
        Initialize voice selector

        Args:
            tts_service: TTSService instance for generating preview audio
        """
        self.tts_service = tts_service
        self.preview_cache_dir = Path(tempfile.gettempdir()) / "voice_previews"
        self.preview_cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize pygame mixer for audio playback
        self.audio_available = False
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.audio_available = True
            logger.info("Audio playback initialized successfully")
        except Exception as e:
            logger.warning(f"Audio playback not available: {e}")
            logger.info("Voice selection will work without preview capability")

    def __del__(self):
        """Cleanup pygame mixer"""
        try:
            if self.audio_available:
                pygame.mixer.quit()
        except:
            pass

    async def select_voice(
        self,
        language: str,
        voices: List[Dict],
        current_voice: Optional[str] = None
    ) -> Optional[str]:
        """
        Interactive voice selection with preview

        Args:
            language: Language code (e.g., 'en', 'hi')
            voices: List of voice dictionaries from edge-tts
            current_voice: Currently selected voice (if editing)

        Returns:
            Selected voice short_name, or None if cancelled
        """
        if not voices:
            console.print("[yellow]No voices available for this language[/yellow]")
            return None

        # Display voice information in a nice table
        self._display_voice_table(voices, language)

        # Show instructions
        self._show_instructions()

        # Prepare choices for inquirer
        choices = self._prepare_choices(voices, current_voice)

        # Interactive selection loop
        while True:
            try:
                # Use inquirer for arrow-key selection
                questions = [
                    inquirer.List(
                        'voice',
                        message=f"Select voice for {language} (↑↓ to navigate, Enter to preview, 's' to select)",
                        choices=choices,
                        carousel=True
                    )
                ]

                # Custom theme for better visibility
                custom_theme = themes.GreenPassion()

                answer = inquirer.prompt(questions, theme=custom_theme)

                if not answer:
                    # User cancelled (Ctrl+C)
                    return None

                selected_value = answer['voice']

                # Check if user wants to preview or select
                if selected_value == 'default':
                    # User selected default
                    return self.tts_service.best_voices.get(language, "en-US-AvaMultilingualNeural")
                elif selected_value == 'cancel':
                    return None
                else:
                    # Extract voice index from the value
                    voice_index = int(selected_value.split('_')[1])
                    selected_voice = voices[voice_index]

                    # Action menu loop - stay here until user selects or goes back
                    while True:
                        # Ask user: Preview or Select?
                        action_questions = [
                            inquirer.List(
                                'action',
                                message=f"Voice: {selected_voice['name']}",
                                choices=[
                                    ('🎧 Preview this voice', 'preview'),
                                    ('✓ Select this voice', 'select'),
                                    ('← Back to list', 'back')
                                ]
                            )
                        ]

                        action_answer = inquirer.prompt(action_questions, theme=custom_theme)

                        if not action_answer or action_answer['action'] == 'back':
                            # Go back to voice list
                            break
                        elif action_answer['action'] == 'preview':
                            # Generate and play preview (if audio available)
                            if self.audio_available:
                                await self._play_preview(selected_voice, language)
                            else:
                                console.print("[yellow]⚠ Audio preview not available on this system[/yellow]")
                                console.print(f"[dim]Would have previewed: {selected_voice['name']}[/dim]")
                            # Loop back to action menu (not voice list!)
                            continue
                        elif action_answer['action'] == 'select':
                            # User confirmed selection
                            console.print(f"[green]✓ Selected voice: {selected_voice['name']}[/green]")
                            return selected_voice['short_name']

            except KeyboardInterrupt:
                console.print("\n[yellow]Voice selection cancelled[/yellow]")
                return None
            except Exception as e:
                logger.error(f"Error in voice selection: {e}")
                console.print(f"[red]Error: {e}[/red]")
                return None

    def _display_voice_table(self, voices: List[Dict], language: str):
        """Display available voices in a formatted table"""
        console.print()
        table = Table(
            title=f"[bold cyan]Available Voices for {language.upper()}[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
            border_style="blue",
            title_style="bold cyan"
        )

        table.add_column("#", style="dim", width=4)
        table.add_column("Voice Name", style="cyan", min_width=30)
        table.add_column("Gender", style="yellow", width=10)
        table.add_column("Locale", style="green", width=10)

        for i, voice in enumerate(voices, 1):
            table.add_row(
                str(i),
                voice.get('name', 'Unknown'),
                voice.get('gender', 'Unknown'),
                voice.get('locale', 'Unknown')
            )

        console.print(table)
        console.print(f"\n[dim]Total voices available: {len(voices)}[/dim]\n")

    def _show_instructions(self):
        """Display usage instructions"""
        audio_note = ""
        if not self.audio_available:
            audio_note = "\n[dim italic]Note: Audio preview not available on this system[/dim italic]"

        instructions = Panel(
            Text.from_markup(
                "[bold cyan]How to use:[/bold cyan]\n\n"
                "• Use [bold]↑/↓ arrow keys[/bold] to navigate\n"
                "• Press [bold]Enter[/bold] to select a voice\n"
                "• Choose [bold]'Preview'[/bold] to hear the voice\n"
                "• Choose [bold]'Select'[/bold] to use the voice\n"
                f"• Press [bold]Ctrl+C[/bold] to cancel{audio_note}"
            ),
            title="[bold yellow]Voice Selection Guide[/bold yellow]",
            border_style="yellow",
            padding=(1, 2)
        )
        console.print(instructions)
        console.print()

    def _prepare_choices(self, voices: List[Dict], current_voice: Optional[str]) -> List[tuple]:
        """
        Prepare choices for inquirer list

        Returns:
            List of tuples (display_name, value)
        """
        choices = []

        for i, voice in enumerate(voices):
            name = voice.get('name', 'Unknown')
            gender = voice.get('gender', 'Unknown')
            locale = voice.get('locale', 'Unknown')
            short_name = voice.get('short_name', '')

            # Mark current voice if editing
            marker = " [CURRENT]" if short_name == current_voice else ""

            display = f"{i+1:3d}. {name} ({gender}, {locale}){marker}"
            value = f"voice_{i}"  # Use index as value

            choices.append((display, value))

        # Add default and cancel options
        choices.append(("─" * 50, 'separator'))
        choices.append(("Use default voice", 'default'))
        choices.append(("Cancel", 'cancel'))

        return choices

    async def _play_preview(self, voice: Dict, language: str):
        """
        Generate and play a preview of the selected voice

        Args:
            voice: Voice dictionary with voice information
            language: Language code
        """
        if not self.audio_available:
            console.print("[yellow]⚠ Audio playback not available[/yellow]")
            console.print("[dim]Preview audio would have been generated for testing[/dim]")
            return

        voice_name = voice.get('name', 'Unknown')
        short_name = voice.get('short_name', '')

        console.print(f"\n[cyan]🎧 Generating preview for: {voice_name}...[/cyan]")

        try:
            # Generate preview text based on language
            preview_text = self._get_preview_text(language)

            # Use safer filename (replace problematic chars)
            safe_name = short_name.replace('/', '_').replace('\\', '_')
            cache_file = self.preview_cache_dir / f"{safe_name}.mp3"

            # Check if we need to generate
            needs_generation = not cache_file.exists() or cache_file.stat().st_size < 1000

            if needs_generation:
                # Remove corrupt cache if exists
                if cache_file.exists():
                    cache_file.unlink()
                    logger.info("Removed corrupt cache file")

                # Generate preview audio
                import edge_tts

                try:
                    communicate = edge_tts.Communicate(
                        text=preview_text,
                        voice=short_name
                    )

                    await communicate.save(str(cache_file))

                    # Verify file was created successfully
                    if not cache_file.exists() or cache_file.stat().st_size < 1000:
                        raise Exception("Audio generation produced no output or file too small")

                    logger.info(f"Generated preview audio: {cache_file}")

                except Exception as gen_err:
                    # Clean up failed attempt
                    if cache_file.exists():
                        cache_file.unlink()
                    raise Exception(f"Audio generation failed: {gen_err}")

            else:
                logger.info(f"Using cached preview: {cache_file}")

            # Play the audio
            console.print("[green]▶ Playing preview...[/green]")
            try:
                self._play_audio_file(str(cache_file))
                console.print("[green]✓ Preview complete[/green]\n")
            except Exception as play_err:
                # If playback fails, remove corrupt cache
                logger.error(f"Playback failed: {play_err}")
                if cache_file.exists():
                    cache_file.unlink()
                    logger.info("Removed corrupt audio file")
                raise Exception(f"Audio playback failed: {play_err}")

        except Exception as e:
            logger.error(f"Failed to generate/play preview: {e}")
            console.print(f"[red]⚠ Preview unavailable for this voice[/red]")
            console.print(f"[dim]Voice: {voice_name}[/dim]")
            console.print(f"[dim]You can still select this voice - it will work for actual generation[/dim]\n")

    def _get_preview_text(self, language: str) -> str:
        """
        Get preview text in the appropriate language

        Args:
            language: Language code

        Returns:
            Preview text string
        """
        preview_texts = {
            'en': "Hello! This is a voice preview. How do you like this voice?",
            'hi': "नमस्ते! यह एक आवाज़ का पूर्वावलोकन है। आपको यह आवाज़ कैसी लगी?",
            'ta': "வணக்கம்! இது குரல் முன்னோட்டம். இந்த குரல் உங்களுக்கு எப்படி உள்ளது?",
            'te': "నమస్కారం! ఇది వాయిస్ ప్రివ్యూ. ఈ వాయిస్ మీకు ఎలా అనిపిస్తుంది?",
            'kn': "ನಮಸ್ಕಾರ! ಇದು ಧ್ವನಿ ಪೂರ್ವವೀಕ್ಷಣೆ. ಈ ಧ್ವನಿ ನಿಮಗೆ ಹೇಗೆ ಅನಿಸುತ್ತದೆ?",
            'ml': "നമസ്കാരം! ഇതൊരു ശബ്ദ പ്രിവ്യൂ ആണ്. ഈ ശബ്ദം നിങ്ങൾക്ക് എങ്ങനെയുണ്ട്?",
            'fr': "Bonjour! Ceci est un aperçu vocal. Comment aimez-vous cette voix?",
            'es': "¡Hola! Esta es una vista previa de voz. ¿Cómo te gusta esta voz?",
            'de': "Hallo! Dies ist eine Sprachvorschau. Wie gefällt Ihnen diese Stimme?",
            'ko': "안녕하세요! 이것은 음성 미리보기입니다. 이 목소리가 어떻습니까?",
            'ja': "こんにちは！これは音声プレビューです。この声はいかがですか？",
            'zh': "你好！这是语音预览。你觉得这个声音怎么样？",
            'ar': "مرحبا! هذه معاينة صوتية. كيف تحب هذا الصوت؟",
            'ru': "Привет! Это предварительный просмотр голоса. Как вам этот голос?",
            'pt': "Olá! Esta é uma prévia de voz. Como você gosta dessa voz?",
            'it': "Ciao! Questa è un'anteprima vocale. Come ti piace questa voce?"
        }

        return preview_texts.get(
            language.lower(),
            "Hello! This is a voice preview. How do you like this voice?"
        )

    def _play_audio_file(self, file_path: str):
        """
        Play an audio file using pygame mixer

        Args:
            file_path: Path to audio file
        """
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()

            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            raise

    def cleanup_cache(self):
        """Clean up preview audio cache"""
        try:
            import shutil
            if self.preview_cache_dir.exists():
                shutil.rmtree(self.preview_cache_dir)
                logger.info("Voice preview cache cleaned up")
        except Exception as e:
            logger.warning(f"Could not clean up preview cache: {e}")


async def select_voice_interactive(
    tts_service,
    language: str,
    current_voice: Optional[str] = None
) -> Optional[str]:
    """
    Convenience function for interactive voice selection

    Args:
        tts_service: TTSService instance
        language: Language code
        current_voice: Currently selected voice (optional)

    Returns:
        Selected voice short_name, or None if cancelled
    """
    # Fetch available voices
    console.print(f"[cyan]Fetching available voices for {language}...[/cyan]")

    try:
        voices = await tts_service.get_available_voices(language)

        if not voices:
            console.print(f"[yellow]No voices found for {language}, using default[/yellow]")
            return tts_service.best_voices.get(language, "en-US-AvaMultilingualNeural")

        # Create selector and let user choose
        selector = VoiceSelector(tts_service)
        selected_voice = await selector.select_voice(language, voices, current_voice)

        return selected_voice

    except Exception as e:
        logger.error(f"Error in voice selection: {e}")
        console.print(f"[red]Error fetching voices: {e}[/red]")
        return tts_service.best_voices.get(language, "en-US-AvaMultilingualNeural")
