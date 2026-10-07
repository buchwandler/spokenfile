from __future__ import annotations

from pathlib import Path
import re

from .engine import PreparationEngine
from .errors import PreparationError
from .models import FileChange, FileIssue, SourceSpan

_HORIZONTAL_GAP = re.compile(r"[ \t]{2,}")


def split_source_span(
    *,
    text: str,
    start: int,
    end: int,
    unit_prefix: str,
    locator: str,
    counter_start: int = 0,
) -> tuple[list[SourceSpan], int]:
    """Split a visible range at wide horizontal gaps without touching the gaps.

    Wide horizontal gaps are kept outside preparation units. This is conservative
    for same-format rewriting: formatting whitespace remains byte-for-byte untouched
    while linguistic text is prepared through ttsready.
    """
    spans: list[SourceSpan] = []
    counter = counter_start
    local = text[start:end]
    cursor = 0
    for match in _HORIZONTAL_GAP.finditer(local):
        piece_start, piece_end = cursor, match.start()
        if piece_start < piece_end:
            counter += 1
            absolute_start = start + piece_start
            absolute_end = start + piece_end
            spans.append(
                SourceSpan(
                    unit_id=f"{unit_prefix}:{counter}",
                    start=absolute_start,
                    end=absolute_end,
                    text=text[absolute_start:absolute_end],
                    locator=locator,
                )
            )
        cursor = match.end()
    if cursor < len(local):
        counter += 1
        absolute_start = start + cursor
        absolute_end = end
        spans.append(
            SourceSpan(
                unit_id=f"{unit_prefix}:{counter}",
                start=absolute_start,
                end=absolute_end,
                text=text[absolute_start:absolute_end],
                locator=locator,
            )
        )
    return spans, counter


def trimmed_line_spans(text: str, *, prefix: str, locator_prefix: str = "line") -> list[SourceSpan]:
    spans: list[SourceSpan] = []
    cursor = 0
    counter = 0
    for line_number, line in enumerate(text.splitlines(keepends=True), start=1):
        logical = line.rstrip("\r\n")
        left = len(logical) - len(logical.lstrip())
        right = len(logical.rstrip())
        if left < right:
            start = cursor + left
            end = cursor + right
            items, counter = split_source_span(
                text=text,
                start=start,
                end=end,
                unit_prefix=prefix,
                locator=f"{locator_prefix} {line_number}",
                counter_start=counter,
            )
            spans.extend(items)
        cursor += len(line)
    return spans


def apply_spans(
    text: str,
    spans: list[SourceSpan],
    *,
    engine: PreparationEngine,
    language: str,
    source_path: Path,
    strict: bool = False,
) -> tuple[str, tuple[FileChange, ...], tuple[FileIssue, ...], int]:
    replacements: list[tuple[int, int, str]] = []
    changes: list[FileChange] = []
    issues: list[FileIssue] = []

    previous_end = -1
    for span in sorted(spans, key=lambda item: (item.start, item.end)):
        if span.start < previous_end:
            raise PreparationError(f"Overlapping source spans at {span.locator}")
        previous_end = span.end
        if text[span.start : span.end] != span.text:
            raise PreparationError(f"Source span changed before preparation: {span.locator}")

        prepared = engine.prepare(
            span.text,
            language=language,
            unit_id=span.unit_id,
            role=span.role,
            metadata={"locator": span.locator, "source_name": source_path.name},
        )
        for issue in prepared.issues:
            if issue.unit_id != span.unit_id:
                raise PreparationError(
                    f"ttsready returned an issue for unexpected unit {issue.unit_id!r}"
                )
            absolute_start = (
                span.start + issue.source_start if issue.source_start is not None else None
            )
            absolute_end = span.start + issue.source_end if issue.source_end is not None else None
            if issue.source_start is not None and not (
                0 <= issue.source_start <= (issue.source_end or -1) <= len(span.text)
            ):
                raise PreparationError(
                    f"ttsready returned an invalid issue range for {span.locator}"
                )
            issues.append(
                FileIssue(
                    code=issue.code,
                    severity=issue.severity,
                    unit_id=span.unit_id,
                    locator=span.locator,
                    source_start=absolute_start,
                    source_end=absolute_end,
                    text=issue.text,
                    message=issue.message,
                )
            )

        if strict:
            error = next((item for item in prepared.issues if item.severity == "error"), None)
            if error is not None:
                raise PreparationError(
                    f"Strict preparation rejected {span.locator}: {error.message}"
                )

        if prepared.spoken_text != span.text:
            replacements.append((span.start, span.end, prepared.spoken_text))

        if prepared.changes:
            for change in prepared.changes:
                if not (0 <= change.source_start <= change.source_end <= len(span.text)):
                    raise PreparationError(
                        f"ttsready returned an invalid source range for {span.locator}"
                    )
                if span.text[change.source_start : change.source_end] != change.source:
                    raise PreparationError(f"ttsready change source does not match {span.locator}")
                changes.append(
                    FileChange(
                        unit_id=span.unit_id,
                        locator=span.locator,
                        source_start=span.start + change.source_start,
                        source_end=span.start + change.source_end,
                        source=change.source,
                        replacement=change.replacement,
                        kind=change.kind,
                        rule=change.rule,
                        stages=change.stages,
                        recognition_domain=change.recognition_domain,
                        provenance=change.provenance,
                    )
                )
        elif prepared.spoken_text != span.text:
            # The 0.2 contract should normally expose every source-relative change.
            # Preserve a fail-visible fallback for a backend that returns only a
            # complete transformed string.
            changes.append(
                FileChange(
                    unit_id=span.unit_id,
                    locator=span.locator,
                    source_start=span.start,
                    source_end=span.end,
                    source=span.text,
                    replacement=prepared.spoken_text,
                    kind="prepared-unit",
                    provenance={"origin": "ttsready", "mapping": "whole-unit-fallback"},
                )
            )

    rendered = text
    for start, end, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
        rendered = rendered[:start] + replacement + rendered[end:]
    return rendered, tuple(changes), tuple(issues), len(spans)
