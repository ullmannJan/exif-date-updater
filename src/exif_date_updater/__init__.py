"""EXIF Date Updater - A tool to analyze and update missing EXIF date information."""

from .exif_analyzer import ExifAnalyzer, MediaFile
from .exif_updater import ExifUpdater
from .cli import main as cli_main
from .gui import run_gui

try:
    from ._version import __version__
except ImportError:
    # Fallback version if _version.py doesn't exist (e.g., during development)
    __version__ = "0.0.0+unknown"

__all__ = ["ExifAnalyzer", "MediaFile", "ExifUpdater", "cli_main", "run_gui"]
