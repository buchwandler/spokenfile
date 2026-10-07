from __future__ import annotations

from pathlib import Path

from ..engine import PreparationEngine
from ..models import AdapterResult
from ..patches import apply_spans, trimmed_line_spans
from .common import decode_utf8


class TextAdapter:
    name = "text"
    extensions = (".txt",)

    def supports(self, source: Path) -> bool:
        return source.suffix.casefold() in self.extensions

    def prepare(
        self,
        source: Path,
        *,
        engine: PreparationEngine,
        language: str,
        strict: bool = False,
    ) -> AdapterResult:
        decoded = decode_utf8(source.read_bytes())
        spans = trimmed_line_spans(decoded.text, prefix="text")
        rendered, changes, issues, count = apply_spans(
            decoded.text,
            spans,
            engine=engine,
            language=language,
            source_path=source,
            strict=strict,
        )
        return AdapterResult(decoded.encode(rendered), changes, issues, count)
