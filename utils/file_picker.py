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

    def search_files_and_folders(self, search_term: str, max_depth: int = 5) -> tuple[List[Path], List[Path]]:
        """
        Recursively search for folders and video files matching the search term

        Args:
            search_term: Search string to match against folder/file names (case-insensitive)
            max_depth: Maximum depth to search (default: 5 levels deep)

        Returns:
            Tuple of (matching_directories, matching_video_files)
        """
        matching_dirs = []
        matching_videos = []
        search_lower = search_term.lower()

        def search_recursive(path: Path, current_depth: int):
            if current_depth > max_depth:
                return

            try:
                for item in path.iterdir():
                    # Skip hidden files/folders
                    if item.name.startswith('.'):
                        continue

                    try:
                        # Check if name matches search term
                        if search_lower in item.name.lower():
                            if item.is_dir():
                                matching_dirs.append(item)
                            elif self.is_video_file(item):
                                matching_videos.append(item)

                        # Recurse into directories
                        if item.is_dir():
                            search_recursive(item, current_depth + 1)

                    except (PermissionError, OSError):
                        # Skip items we can't access
                        continue

            except (PermissionError, OSError):
                # Skip directories we can't access
                pass

        # Start search from current path
        search_recursive(self.current_path, 0)

        # Sort results alphabetically
        matching_dirs.sort(key=lambda x: x.name.lower())
        matching_videos.sort(key=lambda x: x.name.lower())

        return matching_dirs, matching_videos

    def _handle_search(self) -> Optional[List[str]]:
        """
        Handle search functionality - prompt user for search term and display results

        Returns:
            List of selected file paths or None to return to navigation
        """
        console.print("\n[bold cyan]🔍 Search for Folders and Video Files[/bold cyan]")
        console.print(f"[dim]Searching from: {self.current_path}[/dim]")
        console.print(f"[dim]Search depth: 5 levels (subdirectories)[/dim]\n")

        search_term = Prompt.ask("[yellow]Enter search term (folder or file name)[/yellow]", default="")

        if not search_term or search_term.strip() == "":
            console.print("[yellow]Search cancelled[/yellow]")
            return None

        console.print(f"\n[cyan]Searching for '{search_term}'...[/cyan]")

        matching_dirs, matching_videos = self.search_files_and_folders(search_term.strip())

        if not matching_dirs and not matching_videos:
            console.print(f"[yellow]No results found for '{search_term}'[/yellow]")
            console.print("[dim]Press Enter to continue...[/dim]")
            input()
            return None

        # Display search results summary
        console.print(f"\n[green]✓ Found {len(matching_dirs)} folder(s) and {len(matching_videos)} video(s)[/green]\n")

        # Build choices for search results
        choices = []

        # Add option to go back
        choices.append(('← Back to Navigation', 'BACK'))
        choices.append(('─' * 60, None))

        # Add matching directories
        if matching_dirs:
            choices.append(('[bold]📁 MATCHING FOLDERS:[/bold]', None))
            for directory in matching_dirs[:200]:  # Limit to 200 for performance
                relative_path = directory.relative_to(self.current_path) if directory.is_relative_to(self.current_path) else directory
                choices.append((f'📁 {directory.name}/ → {relative_path.parent}', ('DIR', str(directory))))

        # Add separator if both types exist
        if matching_dirs and matching_videos:
            choices.append(('─' * 60, None))

        # Add matching video files
        if matching_videos:
            choices.append(('[bold]🎬 MATCHING VIDEO FILES:[/bold]', None))
            for video in matching_videos[:200]:  # Limit to 200 for performance
                size_mb = video.stat().st_size / (1024 * 1024)
                relative_path = video.relative_to(self.current_path) if video.is_relative_to(self.current_path) else video
                choices.append((
                    f'🎬 {video.name} ({size_mb:.1f} MB) → {relative_path.parent}',
                    ('VIDEO', str(video))
                ))

        # Show selection menu
        questions = [
            inquirer.List(
                'choice',
                message='Select a folder to navigate to, or video to select',
                choices=choices,
                carousel=True
            )
        ]

        try:
            answer = inquirer.prompt(questions, theme=themes.GreenPassion())

            if not answer or answer['choice'] == 'BACK' or answer['choice'] is None:
                return None

            choice_type, choice_path = answer['choice']

            if choice_type == 'DIR':
                # Navigate to selected directory
                self.current_path = Path(choice_path)
                console.print(f"\n[green]Navigated to: {self.current_path}[/green]")
                return None  # Return to main navigation

            elif choice_type == 'VIDEO':
                # Ask if user wants to select just this video or browse the folder
                video_path = Path(choice_path)
                folder_path = video_path.parent

                confirm_choices = [
                    ('Select this video only', 'SELECT_ONE'),
                    ('Browse folder to select multiple videos', 'BROWSE_FOLDER'),
                    ('Back to search results', 'BACK')
                ]

                confirm_q = [
                    inquirer.List(
                        'action',
                        message='What would you like to do?',
                        choices=confirm_choices,
                        carousel=True
                    )
                ]

                confirm_answer = inquirer.prompt(confirm_q, theme=themes.GreenPassion())

                if not confirm_answer or confirm_answer['action'] == 'BACK':
                    return self._handle_search()  # Restart search

                if confirm_answer['action'] == 'SELECT_ONE':
                    return [str(video_path.absolute())]

                elif confirm_answer['action'] == 'BROWSE_FOLDER':
                    self.current_path = folder_path
                    console.print(f"\n[green]Navigated to: {self.current_path}[/green]")
                    return None  # Return to main navigation

        except KeyboardInterrupt:
            console.print("\n[yellow]Search cancelled[/yellow]")
            return None

        return None

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
            "• Use [yellow]🔍 SEARCH[/yellow] to find folders/files by name\n"
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

            # Add SEARCH option prominently at the top
            choices.append(('🔍 SEARCH for folders/files by name', 'SEARCH'))

            # Add CANCEL option
            choices.append(('✗ CANCEL', 'CANCEL'))
            choices.append(('─' * 60, None))

            # Add parent directory option if not at root
            if self.current_path.parent != self.current_path:
                choices.append(('📁 .. (Parent Directory)', '..'))

            # Add directories (no limit - show all)
            for directory in directories:
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

                if choice == 'SEARCH':
                    # Handle search functionality
                    search_result = self._handle_search()
                    if search_result:
                        return search_result
                    # If None, continue with navigation (user may have navigated to a folder)
                    continue

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

        # Show info if many files, but allow all to be displayed
        if len(video_files) > 100:
            console.print(f"[cyan]ℹ {len(video_files)} videos found in this folder.[/cyan]")
            if len(video_files) > 1000:
                console.print(f"[yellow]⚠ Large number of videos. Showing first 1000. Use search to find specific files.[/yellow]")
                video_files = video_files[:1000]

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
