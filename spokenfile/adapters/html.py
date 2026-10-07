from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from ..engine import PreparationEngine
from ..models import AdapterResult, SourceSpan
from ..patches import apply_spans, split_source_span
from .common import DecodedText, decode_htmlish

_SKIP_TAGS = frozenset({"script", "style", "pre", "code", "noscript", "svg", "math", "textarea"})


def _line_offsets(text: str) -> list[int]:
    offsets = [0]
    for index, char in enumerate(text):
        if char == "\n":
            offsets.append(index + 1)
    return offsets


class _VisibleTextParser(HTMLParser):
    def __init__(self, source: str, *, prefix: str, locator_prefix: str) -> None:
        super().__init__(convert_charrefs=False)
        self.source = source
        self.prefix = prefix
        self.locator_prefix = locator_prefix
        self.offsets = _line_offsets(source)
        self.stack: list[str] = []
        self.spans: list[SourceSpan] = []
        self.counter = 0

    def _absolute(self) -> int:
        line, column = self.getpos()
        return self.offsets[line - 1] + column

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        self.stack.append(tag.casefold())

    def handle_startendtag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        return None

    def handle_endtag(self, tag: str) -> None:
        folded = tag.casefold()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == folded:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if not data or any(tag in _SKIP_TAGS for tag in self.stack):
            return
        absolute = self._absolute()
        cursor = 0
        for piece in data.splitlines(keepends=True):
            logical = piece.rstrip("\r\n")
            left = len(logical) - len(logical.lstrip())
            right = len(logical.rstrip())
            if left < right:
                start = absolute + cursor + left
                end = absolute + cursor + right
                if self.source[start:end] != logical[left:right]:
                    # HTMLParser can normalize some malformed constructs. Fail closed by
                    # skipping any data segment whose raw source cannot be proven exact.
                    cursor += len(piece)
                    continue
                items, self.counter = split_source_span(
                    text=self.source,
                    start=start,
                    end=end,
                    unit_prefix=self.prefix,
                    locator=f"{self.locator_prefix} text",
                    counter_start=self.counter,
                )
                self.spans.extend(items)
            cursor += len(piece)


def html_spans(
    text: str, *, prefix: str = "html", locator_prefix: str = "HTML"
) -> list[SourceSpan]:
    parser = _VisibleTextParser(text, prefix=prefix, locator_prefix=locator_prefix)
    parser.feed(text)
    parser.close()
    return parser.spans


def prepare_html_text(
    text: str,
    *,
    source_path: Path,
    engine: PreparationEngine,
    language: str,
    strict: bool,
    prefix: str = "html",
    locator_prefix: str = "HTML",
) -> tuple[str, tuple, tuple[str, ...], int]:
    spans = html_spans(text, prefix=prefix, locator_prefix=locator_prefix)
    return apply_spans(
        text,
        spans,
        engine=engine,
        language=language,
        source_path=source_path,
        strict=strict,
    )


class HtmlAdapter:
    name = "html"
    extensions = (".html", ".htm", ".xhtml")

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
        decoded: DecodedText = decode_htmlish(source.read_bytes())
        rendered, changes, issues, count = prepare_html_text(
            decoded.text,
            source_path=source,
            engine=engine,
            language=language,
            strict=strict,
        )
        return AdapterResult(decoded.encode(rendered), changes, issues, count)
