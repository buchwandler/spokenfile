from __future__ import annotations

from pathlib import Path

from ..errors import UnsupportedFormatError
from .base import Adapter
from .epub import EpubAdapter
from .html import HtmlAdapter
from .markdown import MarkdownAdapter
from .text import TextAdapter

_ADAPTERS: tuple[Adapter, ...] = (
    EpubAdapter(),
    HtmlAdapter(),
    MarkdownAdapter(),
    TextAdapter(),
)


def adapters() -> tuple[Adapter, ...]:
    return _ADAPTERS


def adapter_for(source: Path) -> Adapter:
    for adapter in _ADAPTERS:
        if adapter.supports(source):
            return adapter
    supported = ", ".join(sorted(ext for adapter in _ADAPTERS for ext in adapter.extensions))
    raise UnsupportedFormatError(
        f"Unsupported input format {source.suffix or '<none>'!r}; supported: {supported}"
    )
