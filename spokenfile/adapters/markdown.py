from __future__ import annotations

import re
from pathlib import Path

from ..engine import PreparationEngine
from ..models import AdapterResult, SourceSpan
from ..patches import apply_spans, split_source_span
from .common import decode_utf8

_FENCE_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
_REFERENCE_RE = re.compile(r"^[ \t]{0,3}\[[^\]]+\]:\s+\S+")
_PREFIX_RE = re.compile(r"^(?:[ \t]{0,3}(?:#{1,6}[ \t]+|>[ \t]?|[-+*][ \t]+|\d+[.)][ \t]+))")
_URL_RE = re.compile(r"(?:https?://|mailto:)[^\s)>]+", re.IGNORECASE)
_ENTITY_RE = re.compile(r"&(?:#\d+|#x[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]+);")
_LINK_DEST_RE = re.compile(r"\]\((?:[^()\\]|\\.)*\)")
_AUTOLINK_RE = re.compile(r"<(?:https?://|mailto:)[^>]+>", re.IGNORECASE)
_SYNTAX = frozenset("*_~[]()!<>#>|`")


def _protected_ranges(line: str) -> list[tuple[int, int]]:
    protected: list[tuple[int, int]] = []
    prefix = _PREFIX_RE.match(line)
    if prefix:
        protected.append((0, prefix.end()))
    for regex in (_URL_RE, _ENTITY_RE, _LINK_DEST_RE, _AUTOLINK_RE):
        protected.extend((m.start(), m.end()) for m in regex.finditer(line))

    index = 0
    while index < len(line):
        if line[index] != "`":
            index += 1
            continue
        run = 1
        while index + run < len(line) and line[index + run] == "`":
            run += 1
        delimiter = "`" * run
        end = line.find(delimiter, index + run)
        if end < 0:
            protected.append((index, len(line)))
            break
        protected.append((index, end + run))
        index = end + run
    return protected


def _contains(ranges: list[tuple[int, int]], index: int) -> int | None:
    for start, end in ranges:
        if start <= index < end:
            return end
    return None


def markdown_spans(text: str) -> list[SourceSpan]:
    spans: list[SourceSpan] = []
    cursor = 0
    in_fence: str | None = None
    front_matter: str | None = None
    counter = 0

    lines = text.splitlines(keepends=True)
    for line_number, line in enumerate(lines, start=1):
        logical = line.rstrip("\r\n")
        stripped = logical.strip()

        if line_number == 1 and stripped in {"---", "+++"}:
            front_matter = stripped
            cursor += len(line)
            continue
        if front_matter is not None:
            if stripped == front_matter:
                front_matter = None
            cursor += len(line)
            continue

        fence_match = _FENCE_RE.match(logical)
        if in_fence is not None:
            if stripped.startswith(in_fence):
                in_fence = None
            cursor += len(line)
            continue
        if fence_match:
            in_fence = fence_match.group(1)[0] * len(fence_match.group(1))
            cursor += len(line)
            continue

        if not stripped or logical.startswith(("    ", "\t")) or _REFERENCE_RE.match(logical):
            cursor += len(line)
            continue
        if stripped.startswith("<") and stripped.endswith(">"):
            cursor += len(line)
            continue

        protected = _protected_ranges(logical)
        index = 0
        while index < len(logical):
            protected_end = _contains(protected, index)
            if protected_end is not None:
                index = protected_end
                continue
            if logical[index] in _SYNTAX:
                index += 1
                continue
            start = index
            while index < len(logical):
                if _contains(protected, index) is not None or logical[index] in _SYNTAX:
                    break
                index += 1
            raw = logical[start:index]
            left = len(raw) - len(raw.lstrip())
            right = len(raw.rstrip())
            if left < right:
                absolute_start = cursor + start + left
                absolute_end = cursor + start + right
                items, counter = split_source_span(
                    text=text,
                    start=absolute_start,
                    end=absolute_end,
                    unit_prefix="markdown",
                    locator=f"line {line_number}",
                    counter_start=counter,
                )
                spans.extend(items)
            if index == start:
                index += 1
        cursor += len(line)
    return spans


class MarkdownAdapter:
    name = "markdown"
    extensions = (".md", ".markdown")

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
        spans = markdown_spans(decoded.text)
        rendered, changes, issues, count = apply_spans(
            decoded.text,
            spans,
            engine=engine,
            language=language,
            source_path=source,
            strict=strict,
        )
        return AdapterResult(decoded.encode(rendered), changes, issues, count)
