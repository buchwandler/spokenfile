"""Format-preserving preparation of files for text-to-speech."""

from __future__ import annotations

try:
    from ._version import version as __version__
except (ImportError, AttributeError):
    try:
        from importlib.metadata import version

        __version__ = version("spokenfile")
    except Exception:  # pragma: no cover - bare source tree
        __version__ = "0.1.0.dev0"

from .api import inspect_file, prepare_file, supported_formats
from .errors import SpokenFileError, UnsupportedFormatError
from .models import FileChange, FilePreparationResult

__all__ = [
    "FileChange",
    "FilePreparationResult",
    "SpokenFileError",
    "UnsupportedFormatError",
    "__version__",
    "inspect_file",
    "prepare_file",
    "supported_formats",
]
