"""
Interactive File Picker - Multi-select file browser with arrow key navigation
"""

import os
from pathlib import Path
from typing import List, Optional
import inquirer
from inquirer import themes
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt

console = Console()


class FilePicker:
    """
    Interactive file picker with multi-select capability for video files.
    Allows browsing filesystem and selecting multiple files using arrow keys.
    """

    # Supported video extensions
    VIDEO_EXTENSIONS = {
        '.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.m4v',
        '.mpeg', '.mpg', '.wmv', '.3gp', '.ogv', '.ts', '.mts'
    }

    def __init__(self, start_path: Optional[str] = None, multi_select: bool = True):
        """
        Initialize FilePicker

        Args:
            start_path: Starting directory path (default: user's home directory)
            multi_select: Allow selecting multiple files (default: True)
        """
        if start_path:
            self.current_path = Path(start_path).expanduser().absolute()
        else:
            self.current_path = Path.home()

        self.multi_select = multi_select
        self.selected_files: List[Path] = []

    def is_video_file(self, path: Path) -> bool:
        """Check if a file is a supported video file"""
        return path.is_file() and path.suffix.lower() in self.VIDEO_EXTENSIONS

    def get_directory_contents(self) -> tuple[List[Path], List[Path]]:
        """
        Get directories and video files in current path

        Returns:
            Tuple of (directories, video_files)
        """
        try:
            items = sorted(self.current_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))

            directories = [item for item in items if item.is_dir() and not item.name.startswith('.')]
            video_files = [item for item in items if self.is_video_file(item)]

            return directories, video_files

        except PermissionError:
            console.print(f"[red]Permission denied: {self.current_path}[/red]")
            return [], []

    def display_current_selection(self):
        """Display currently selected files"""
        if not self.selected_files:
            return

        console.print("\n[cyan]Currently Selected Files:[/cyan]")
        for idx, file in enumerate(self.selected_files, 1):
            console.print(f"  [green]{idx}. {file.name}[/green] ({file.parent})")

    def pick_files(self) -> List[str]:
        """
        Main file picker interface - Two-stage process for better UX

        Returns:
            List of selected file paths (absolute paths as strings)
        """
        console.print(Panel.fit(
            "[bold cyan]Interactive Video File Picker[/bold cyan]\n\n"
            "[bold]Stage 1:[/bold] Navigate to folder with videos\n"
            "[bold]Stage 2:[/bold] Multi-select videos with [yellow]Space[/yellow] key\n\n"
            "• Use [yellow]↑/↓[/yellow] arrow keys to navigate\n"
            "• Press [yellow]Enter[/yellow] to open directory or select folder\n"
            "• Press [yellow]Ctrl+C[/yellow] to cancel anytime",
            title="File Picker Guide",
            border_style="cyan"
        ))

        # Stage 1: Navigate to directory
        while True:
            directories, video_files = self.get_directory_contents()

            console.print(f"\n[bold]Current Directory:[/bold] [cyan]{self.current_path}[/cyan]")

            # Show video count in current directory
            if video_files:
                console.print(f"[bold green]✓ {len(video_files)} video file(s) available here![/bold green]")

            # Build directory navigation choices
            choices = []

            # Add option to select from current directory if videos exist - AT THE TOP
            if video_files:
                choices.append((
                    f'❯ ✓ SELECT VIDEOS FROM \'{self.current_path.name}\' FOLDER ({len(video_files)} videos available)',
                    'SELECT_HERE'
                ))
                choices.append(('─' * 60, None))

            # Add CANCEL option at the top as well
            choices.append(('✗ CANCEL', 'CANCEL'))
            choices.append(('─' * 60, None))

            # Add parent directory option if not at root
            if self.current_path.parent != self.current_path:
                choices.append(('📁 .. (Parent Directory)', '..'))

            # Add directories
            for directory in directories[:50]:  # Limit to first 50 directories
                choices.append((f'📁 {directory.name}/', str(directory)))

            # Use inquirer for directory navigation
            questions = [
                inquirer.List(
                    'choice',
                    message='Navigate to folder (or select to pick videos)',
                    choices=choices,
                    carousel=True
                )
            ]

            try:
                answer = inquirer.prompt(questions, theme=themes.GreenPassion())

                if not answer:
                    console.print("\n[yellow]File selection cancelled[/yellow]")
                    return []

                choice = answer['choice']

                if choice is None:
                    continue

                if choice == 'CANCEL':
                    console.print("\n[yellow]File selection cancelled[/yellow]")
                    return []

                if choice == 'SELECT_HERE':
                    # Proceed to Stage 2: Multi-select from current directory
                    selected = self._multi_select_videos(video_files)
                    if selected:
                        return selected
                    # If cancelled or no selection, go back to navigation
                    continue

                if choice == '..':
                    self.current_path = self.current_path.parent
                    continue

                # Navigate into directory
                selected_path = Path(choice)
                if selected_path.is_dir():
                    self.current_path = selected_path
                    continue

            except KeyboardInterrupt:
                console.print("\n\n[yellow]File selection cancelled[/yellow]")
                return []

    def _multi_select_videos(self, video_files: List[Path]) -> List[str]:
        """
        Stage 2: Multi-select videos using Checkbox (Space key works!)

        Args:
            video_files: List of video file paths to select from

        Returns:
            List of selected file paths
        """
        console.print(f"\n[bold green]Select Videos[/bold green]")
        console.print(f"[dim]Use Space to select/deselect, Enter to confirm[/dim]\n")

        # Limit display if too many files
        if len(video_files) > 100:
            console.print(f"[yellow]⚠ {len(video_files)} videos found. Showing first 100.[/yellow]")
            video_files = video_files[:100]

        # Build checkbox choices
        choices = []
        for video in video_files:
            size_mb = video.stat().st_size / (1024 * 1024)
            display_name = f'{video.name} ({size_mb:.1f} MB)'
            choices.append((display_name, str(video.absolute())))

        if not choices:
            console.print("[yellow]No video files found in this directory[/yellow]")
            return []

        # Use Checkbox for multi-select (Space key works here!)
        questions = [
            inquirer.Checkbox(
                'videos',
                message='Select videos (Space to toggle, Enter to confirm)',
                choices=choices,
                carousel=True
            )
        ]

        try:
            answer = inquirer.prompt(questions, theme=themes.GreenPassion())

            if not answer or not answer['videos']:
                console.print("\n[yellow]No videos selected[/yellow]")
                return []

            selected_paths = answer['videos']
            console.print(f"\n[green]✓ {len(selected_paths)} video(s) selected[/green]")

            # Show selected files
            for idx, path in enumerate(selected_paths, 1):
                console.print(f"  {idx}. {Path(path).name}")

            return selected_paths

        except KeyboardInterrupt:
            console.print("\n[yellow]Selection cancelled[/yellow]")
            return []


def pick_video_files(start_path: Optional[str] = None, multi_select: bool = True) -> List[str]:
    """
    Convenience function to pick video files

    Args:
        start_path: Starting directory path
        multi_select: Allow selecting multiple files

    Returns:
        List of selected file paths (absolute paths)
    """
    picker = FilePicker(start_path=start_path, multi_select=multi_select)
    return picker.pick_files()


def pick_single_video_file(start_path: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to pick a single video file

    Args:
        start_path: Starting directory path

    Returns:
        Selected file path or None if cancelled
    """
    picker = FilePicker(start_path=start_path, multi_select=False)
    result = picker.pick_files()
    return result[0] if result else None


# Example usage
if __name__ == "__main__":
    console.print("[bold cyan]Testing File Picker[/bold cyan]\n")

    # Test multi-select
    console.print("[yellow]Test 1: Multi-select mode[/yellow]")
    selected = pick_video_files()

    if selected:
        console.print(f"\n[green]Selected {len(selected)} file(s):[/green]")
        for file_path in selected:
            console.print(f"  • {file_path}")
    else:
        console.print("\n[yellow]No files selected[/yellow]")

    # Test single-select
    # console.print("\n[yellow]Test 2: Single-select mode[/yellow]")
    # single_file = pick_single_video_file()

    # if single_file:
    #     console.print(f"\n[green]Selected file:[/green] {single_file}")
    # else:
    #     console.print("\n[yellow]No file selected[/yellow]")
