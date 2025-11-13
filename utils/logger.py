"""Logging configuration using loguru"""

import sys
from contextlib import contextmanager
from loguru import logger
from pathlib import Path

# Remove default handler
logger.remove()

# Add console handler with custom format
console_handler_id = logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True
)

# Add file handler
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Use Path for cross-platform compatibility
log_file = log_dir / "termivoxed.log"

logger.add(
    str(log_file),
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
)


@contextmanager
def suppress_console_logs():
    """
    Context manager to temporarily suppress console logging while keeping file logging active.
    Useful for clean progress bar display without log interference.

    Usage:
        with suppress_console_logs():
            # Your code with progress bars
            pass
    """
    global console_handler_id

    # Remove console handler
    logger.remove(console_handler_id)

    try:
        yield
    finally:
        # Restore console handler
        console_handler_id = logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
            level="INFO",
            colorize=True
        )


__all__ = ["logger", "suppress_console_logs"]
