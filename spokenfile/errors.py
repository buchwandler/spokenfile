class SpokenFileError(RuntimeError):
    """Base error for spokenfile."""


class UnsupportedFormatError(SpokenFileError):
    """Raised when no adapter supports an input file."""


class PreparationError(SpokenFileError):
    """Raised when TTS preparation cannot be mapped safely."""
