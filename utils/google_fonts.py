"""Google Fonts utility for extracting font names from Google Fonts links"""

import re
from typing import Optional
from utils.logger import logger


def parse_google_font_url(url: str) -> Optional[str]:
    """
    Extract font family name from Google Fonts URL
    Handles multiple fonts in URL - returns the LAST font (most prominent)

    Examples:
        https://fonts.googleapis.com/css2?family=Roboto:wght@400;700
        → Roboto

        https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400
        → Open Sans

        https://fonts.googleapis.com/css2?family=Roboto&family=Stack+Sans+Headline:wght@200
        → Stack Sans Headline (last/primary font)

    Args:
        url: Google Fonts URL or font link HTML

    Returns:
        Font family name or None if parsing fails
    """
    # Handle both direct URL and HTML link tag
    if 'href=' in url:
        # Extract URL from HTML link tag
        match = re.search(r'href=["\']([^"\']+)["\']', url)
        if match:
            url = match.group(1)

    # Extract ALL family parameters from URL
    matches = re.findall(r'family=([^:&]+)', url)

    if not matches:
        return None

    # Use the LAST font family (typically the primary/main font)
    font_name = matches[-1]

    # Replace + with spaces and URL decode
    font_name = font_name.replace('+', ' ')

    # Remove any URL encoding
    import urllib.parse
    font_name = urllib.parse.unquote(font_name)

    return font_name.strip()


def validate_font_name(font_name: str) -> bool:
    """
    Validate that font name is reasonable for FFmpeg/ASS

    Args:
        font_name: Font family name

    Returns:
        True if valid, False otherwise
    """
    if not font_name or len(font_name) > 100:
        return False

    # Font name should only contain letters, numbers, spaces, hyphens
    if not re.match(r'^[a-zA-Z0-9\s\-]+$', font_name):
        return False

    return True


def get_font_from_input(user_input: str, default_font: str = "Arial") -> str:
    """
    Get font name from user input (URL or direct name)

    Args:
        user_input: Google Font URL, HTML link, or font name
        default_font: Default font if parsing fails

    Returns:
        Font family name
    """
    # Try parsing as Google Fonts URL
    if 'fonts.googleapis.com' in user_input or 'family=' in user_input:
        font = parse_google_font_url(user_input)
        if font and validate_font_name(font):
            return font

    # Try using as direct font name
    font_name = user_input.strip()
    if validate_font_name(font_name):
        return font_name

    # Return default if all else fails
    return default_font


def get_font_from_input_with_install(user_input: str, default_font: str = "Arial") -> str:
    """
    Get font name from user input and ensure it's installed

    Args:
        user_input: Google Font URL, HTML link, or font name
        default_font: Default font if parsing fails

    Returns:
        Font family name
    """
    # Import here to avoid circular dependency
    from utils.font_manager import FontManager

    # Get font name
    font_name = get_font_from_input(user_input, default_font)

    # Try to ensure font is available
    try:
        FontManager.ensure_font_available(font_name)
    except Exception as e:
        logger.warning(f"Could not ensure font availability: {e}")

    return font_name
