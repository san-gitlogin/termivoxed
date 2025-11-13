"""Font Manager - Downloads and installs Google Fonts for FFmpeg/ASS rendering"""

import os
import sys
import shutil
import platform
import requests
import zipfile
import re
from pathlib import Path
from typing import Optional, List
from utils.logger import logger
from config import settings


class FontManager:
    """Manages downloading and installing fonts from Google Fonts"""

    # Google Fonts CSS API for getting font URLs
    GOOGLE_FONTS_CSS_API = "https://fonts.googleapis.com/css2?family="

    # Cache of installed fonts to avoid re-downloading
    _installed_fonts = set()

    @staticmethod
    def get_system_font_dir() -> Optional[Path]:
        """
        Get the appropriate system font directory based on platform
        Returns user font directory (no sudo/admin required)
        """
        system = platform.system()

        if system == "Darwin":  # macOS
            font_dir = Path.home() / "Library" / "Fonts"
        elif system == "Linux":
            # Try ~/.local/share/fonts first, fallback to ~/.fonts
            font_dir = Path.home() / ".local" / "share" / "fonts"
            if not font_dir.exists():
                font_dir = Path.home() / ".fonts"
        elif system == "Windows":
            # Windows 10+ user fonts (no admin required)
            font_dir = Path(os.getenv('LOCALAPPDATA')) / "Microsoft" / "Windows" / "Fonts"
        else:
            logger.warning(f"Unsupported platform: {system}")
            return None

        # Create directory if it doesn't exist
        font_dir.mkdir(parents=True, exist_ok=True)
        return font_dir

    @staticmethod
    def is_font_installed(font_name: str) -> bool:
        """
        Check if a font is already installed on the system

        Args:
            font_name: Font family name (e.g., "Roboto", "Momo Signature")

        Returns:
            True if font is installed, False otherwise
        """
        # Check cache first
        if font_name in FontManager._installed_fonts:
            return True

        system_font_dir = FontManager.get_system_font_dir()
        if not system_font_dir:
            return False

        # Normalize font name for file matching
        normalized_name = font_name.replace(" ", "").lower()

        # Check if any font files with this name exist
        for font_file in system_font_dir.glob("*"):
            if font_file.suffix.lower() in ['.ttf', '.otf', '.ttc', '.woff', '.woff2']:
                file_normalized = font_file.stem.replace(" ", "").replace("-", "").lower()
                if normalized_name in file_normalized:
                    FontManager._installed_fonts.add(font_name)
                    logger.info(f"Font '{font_name}' found: {font_file.name}")
                    return True

        return False

    @staticmethod
    def download_google_font(font_name: str) -> Optional[Path]:
        """
        Download font from Google Fonts to local cache

        Args:
            font_name: Font family name (e.g., "Roboto", "Momo Signature")

        Returns:
            Path to downloaded font directory, or None if download failed
        """
        try:
            # Create fonts cache directory
            fonts_dir = Path(settings.FONTS_DIR)
            fonts_dir.mkdir(parents=True, exist_ok=True)

            # Normalize font name for directory
            safe_font_name = re.sub(r'[^\w\s-]', '', font_name).replace(' ', '_')
            font_cache_dir = fonts_dir / safe_font_name

            # Check if already downloaded (any font format)
            if font_cache_dir.exists():
                existing_fonts = (list(font_cache_dir.glob("*.ttf")) +
                                  list(font_cache_dir.glob("*.otf")) +
                                  list(font_cache_dir.glob("*.woff")) +
                                  list(font_cache_dir.glob("*.woff2")))
                if existing_fonts:
                    logger.info(f"Font '{font_name}' already in cache: {font_cache_dir}")
                    return font_cache_dir

            # Download font from Google Fonts using CSS API
            logger.info(f"Downloading font '{font_name}' from Google Fonts...")

            # Format font name for URL (replace spaces with +)
            url_font_name = font_name.replace(' ', '+')
            css_url = f"{FontManager.GOOGLE_FONTS_CSS_API}{url_font_name}"

            # Get CSS file which contains font URLs
            # Use a desktop User-Agent to get TTF files instead of WOFF2
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(css_url, headers=headers, timeout=30)
            response.raise_for_status()

            css_content = response.text

            # Extract font URLs from CSS
            # Look for url() patterns
            font_urls = re.findall(r'url\((https://[^)]+)\)', css_content)

            if not font_urls:
                logger.error(f"No font URLs found in CSS for '{font_name}'")
                logger.debug(f"CSS content: {css_content[:500]}")
                return None

            logger.info(f"Found {len(font_urls)} font file(s) in CSS")

            # Create font cache directory
            font_cache_dir.mkdir(parents=True, exist_ok=True)

            # Download each font file
            downloaded_count = 0
            for i, font_url in enumerate(font_urls):
                try:
                    # Download font file
                    font_response = requests.get(font_url, timeout=30)
                    font_response.raise_for_status()

                    # Determine file extension from content-type or URL
                    content_type = font_response.headers.get('content-type', '')
                    if 'woff2' in content_type or font_url.endswith('.woff2'):
                        ext = '.woff2'
                    elif 'woff' in content_type or font_url.endswith('.woff'):
                        ext = '.woff'
                    elif 'truetype' in content_type or font_url.endswith('.ttf'):
                        ext = '.ttf'
                    elif 'opentype' in content_type or font_url.endswith('.otf'):
                        ext = '.otf'
                    else:
                        # Default to ttf
                        ext = '.ttf'

                    # Save font file
                    font_file_name = f"{safe_font_name}_{i}{ext}"
                    font_file_path = font_cache_dir / font_file_name

                    with open(font_file_path, 'wb') as f:
                        f.write(font_response.content)

                    downloaded_count += 1
                    logger.info(f"Downloaded: {font_file_name}")

                except Exception as e:
                    logger.warning(f"Failed to download font file from {font_url}: {e}")
                    continue

            if downloaded_count == 0:
                logger.error(f"Failed to download any font files for '{font_name}'")
                return None

            logger.info(f"Font downloaded: {downloaded_count} file(s)")
            return font_cache_dir

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download font '{font_name}': {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading font '{font_name}': {e}")
            return None

    @staticmethod
    def install_font(font_name: str) -> bool:
        """
        Download and install a Google Font to system font directory

        Args:
            font_name: Font family name (e.g., "Roboto", "Momo Signature")

        Returns:
            True if font was successfully installed, False otherwise
        """
        try:
            # Check if already installed
            if FontManager.is_font_installed(font_name):
                logger.info(f"Font '{font_name}' is already installed")
                return True

            # Download font
            font_cache_dir = FontManager.download_google_font(font_name)
            if not font_cache_dir:
                logger.error(f"Failed to download font: {font_name}")
                return False

            # Get system font directory
            system_font_dir = FontManager.get_system_font_dir()
            if not system_font_dir:
                logger.error("Could not determine system font directory")
                return False

            # Copy font files to system directory (all formats)
            font_files = (list(font_cache_dir.glob("*.ttf")) +
                          list(font_cache_dir.glob("*.otf")) +
                          list(font_cache_dir.glob("*.woff")) +
                          list(font_cache_dir.glob("*.woff2")))

            if not font_files:
                logger.error(f"No font files found for: {font_name}")
                return False

            logger.info(f"Installing {len(font_files)} font file(s) to: {system_font_dir}")

            for font_file in font_files:
                dest_path = system_font_dir / font_file.name

                # Check if file already exists
                if dest_path.exists():
                    logger.info(f"Font file already exists: {font_file.name}")
                    continue

                # Copy font file
                shutil.copy2(font_file, dest_path)
                logger.info(f"Installed: {font_file.name}")

            # Update font cache on system (platform-specific)
            FontManager._update_font_cache()

            # Mark as installed
            FontManager._installed_fonts.add(font_name)

            logger.info(f"✓ Font '{font_name}' successfully installed!")
            return True

        except Exception as e:
            logger.error(f"Failed to install font '{font_name}': {e}")
            return False

    @staticmethod
    def _update_font_cache():
        """
        Update system font cache after installing new fonts
        Platform-specific commands
        """
        system = platform.system()

        try:
            if system == "Linux":
                # Run fc-cache to update fontconfig cache
                import subprocess
                result = subprocess.run(['fc-cache', '-f', '-v'],
                                        capture_output=True,
                                        text=True,
                                        timeout=30)
                if result.returncode == 0:
                    logger.info("Font cache updated (fc-cache)")
                else:
                    logger.warning("fc-cache command failed, but fonts should still work")

            elif system == "Darwin":  # macOS
                # macOS automatically updates font cache
                logger.info("Font cache will be updated automatically (macOS)")

            elif system == "Windows":
                # Windows 10+ automatically updates font cache
                logger.info("Font cache will be updated automatically (Windows)")

        except Exception as e:
            logger.warning(f"Could not update font cache: {e}")
            logger.info("Fonts should still work after restart")

    @staticmethod
    def ensure_font_available(font_name: str) -> bool:
        """
        Ensure a font is available for FFmpeg/ASS rendering
        Downloads and installs if necessary

        Args:
            font_name: Font family name

        Returns:
            True if font is available, False otherwise
        """
        # Skip system default fonts
        default_fonts = ['Arial', 'Roboto', 'Times New Roman', 'Helvetica', 'DejaVu Sans']
        if font_name in default_fonts:
            logger.info(f"Using system default font: {font_name}")
            return True

        # Check if installed
        if FontManager.is_font_installed(font_name):
            return True

        # Try to install
        logger.info(f"Font '{font_name}' not found. Attempting to download and install...")
        success = FontManager.install_font(font_name)

        if not success:
            logger.warning(f"Could not install font '{font_name}'. Video will use system default font.")

        return success

    @staticmethod
    def get_available_fonts() -> List[str]:
        """
        Get list of fonts available in the fonts cache

        Returns:
            List of font directory names
        """
        fonts_dir = Path(settings.FONTS_DIR)
        if not fonts_dir.exists():
            return []

        return [d.name for d in fonts_dir.iterdir() if d.is_dir()]
