"""Subtitle utilities - Proven patterns from existing system"""

import subprocess
import os
from typing import Dict, Optional
from utils.logger import logger
from config import settings


class SubtitleUtils:
    """Wraps proven subtitle styling patterns from existing system"""

    # Language-specific fonts (from existing system)
    LANGUAGE_FONTS = {
        'en': 'Roboto',
        'english': 'Roboto',
        'hi': 'Noto Sans Devanagari',
        'hindi': 'Noto Sans Devanagari',
        'ta': 'Noto Sans Tamil',
        'tamil': 'Noto Sans Tamil',
        'te': 'Noto Sans Telugu',
        'telugu': 'Noto Sans Telugu',
        'kn': 'Noto Sans Kannada',
        'kannada': 'Noto Sans Kannada',
        'ml': 'Noto Sans Malayalam',
        'malayalam': 'Noto Sans Malayalam',
        'ko': 'Noto Sans KR',
        'korean': 'Noto Sans KR',
        'fr': 'Roboto',
        'french': 'Roboto',
    }

    @staticmethod
    def convert_srt_to_ass(srt_path: str, ass_path: str) -> bool:
        """
        PROVEN: Convert SRT subtitle file to ASS format using FFmpeg
        From: FFmpeg_Video_Generation_Documentation.md
        """
        try:
            # Validate SRT file exists and has content
            if not os.path.exists(srt_path):
                logger.error(f"SRT file not found: {srt_path}")
                return False

            # Check if SRT file is empty
            if os.path.getsize(srt_path) == 0:
                logger.error(f"SRT file is empty: {srt_path}")
                return False

            # Read and validate SRT content
            try:
                with open(srt_path, 'r', encoding='utf-8') as f:
                    srt_content = f.read().strip()
                    if not srt_content:
                        logger.error(f"SRT file has no content: {srt_path}")
                        return False
            except Exception as e:
                logger.error(f"Cannot read SRT file: {e}")
                return False

            cmd = [
                settings.FFMPEG_PATH,
                '-i', srt_path,
                '-y',
                ass_path
            ]

            logger.info(f"Converting SRT to ASS: {srt_path}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            if os.path.exists(ass_path):
                logger.info("SRT to ASS conversion completed")
                return True
            else:
                logger.error("ASS file not created")
                return False

        except subprocess.CalledProcessError as e:
            logger.error(f"SRT to ASS conversion failed: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error converting SRT to ASS: {e}")
            return False

    @staticmethod
    def get_language_specific_font(language: str) -> str:
        """Get appropriate font for language"""
        return SubtitleUtils.LANGUAGE_FONTS.get(
            language.lower(),
            'Arial'
        )

    @staticmethod
    def create_custom_ass_style(
        srt_path: str,
        ass_path: str,
        style_options: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        PROVEN: Convert SRT to ASS with custom styling
        From: FFmpeg_Video_Generation_Documentation.md
        """
        # Default style
        default_style = {
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
            'outline': '0.5',  # Reduced from 1 to 0.5 for thinner border
            'shadow': '0',
            'alignment': '2',  # Bottom center
            'marginl': '10',
            'marginr': '10',
            'marginv': '30'
        }

        # Update with custom options
        if style_options:
            default_style.update(style_options)

        # First convert SRT to basic ASS
        if not SubtitleUtils.convert_srt_to_ass(srt_path, ass_path):
            return False

        # Read the generated ASS file
        try:
            with open(ass_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Build style line
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

            logger.info("Custom ASS styling applied")
            return True

        except Exception as e:
            logger.error(f"Error applying custom styling: {e}")
            return False

    @staticmethod
    def get_default_style_for_language(language: str) -> Dict[str, str]:
        """
        Get default subtitle style for a language
        Based on proven patterns from existing system
        """
        font = SubtitleUtils.get_language_specific_font(language)

        return {
            'fontname': font,
            'fontsize': '20',
            'primarycolour': '&H00FFFFFF',  # White
            'secondarycolour': '&H000000FF',  # Red
            'outlinecolour': '&H00000000',  # Black outline
            'backcolour': '&H80000000',  # Semi-transparent black
            'bold': '-1',
            'italic': '0',
            'underline': '0',
            'strikeout': '0',
            'scalex': '100',
            'scaley': '100',
            'spacing': '0',
            'angle': '0',
            'borderstyle': '1',
            'outline': '0.5',  # Reduced from 1 to 0.5 for thinner border
            'shadow': '0',
            'alignment': '2',  # Bottom center
            'marginl': '10',
            'marginr': '10',
            'marginv': '30'  # For landscape videos
        }
