"""
UTIL: Logger
PURPOSE: Structured logging with timestamps. Logs to console (colorized) + file (automation.log).
"""

import logging
import os
import sys
import colorlog

LOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(LOG_DIR, "automation.log")

# ── Formatter ────────────────────────────────────────────────
FILE_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
# Console: Gray time | Colorized Level | Message
CONSOLE_FORMAT = "%(log_color)s%(asctime)s | %(message)s"

DATE_FORMAT_FILE = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT_CONSOLE = "%H:%M:%S"

COLORS = {
    'DEBUG':    'cyan',
    'INFO':     'green',
    'WARNING':  'yellow',
    'ERROR':    'red',
    'CRITICAL': 'red,bg_white',
}

def get_logger(name: str = "ai_flow") -> logging.Logger:
    """Return a configured logger instance."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(logging.DEBUG)

    # Console handler (INFO+) - visually clean
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    
    formatter = colorlog.ColoredFormatter(
        CONSOLE_FORMAT,
        datefmt=DATE_FORMAT_CONSOLE,
        log_colors=COLORS,
        reset=True,
    )
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler (DEBUG+) - full detail
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(FILE_FORMAT, datefmt=DATE_FORMAT_FILE))
    logger.addHandler(file_handler)

    return logger


# ── Convenience shortcuts ────────────────────────────────────
_log = get_logger()

log_info = _log.info
log_error = _log.error
log_warning = _log.warning
log_debug = _log.debug

def log_section(title: str):
    """Print a visual separator line to the log."""
    _log.info(f"\n{'─'*15} {title} {'─'*15}")
