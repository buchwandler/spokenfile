from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from .errors import PreparationError
from .models import PreparedChange, PreparedIssue, PreparedUnit


class PreparationEngine(Protocol):
    def prepare(
        self,
        text: str,
        *,
        language: str,
        unit_id: str,
        role: str = "prose",
        protected_spans: Iterable[tuple[int, int]] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> PreparedUnit: ...


def _value(item: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(item, dict) and name in item:
            return item[name]
        if hasattr(item, name):
            return getattr(item, name)
    return default


def _normalize_change(item: Any) -> PreparedChange:
    return PreparedChange(
        source_start=int(_value(item, "source_start", default=0)),
        source_end=int(_value(item, "source_end", default=0)),
        source=str(_value(item, "source", "source_text", default="")),
        replacement=str(_value(item, "replacement", "spoken_text", default="")),
        kind=str(_value(item, "kind", default="normalization")),
        rule=(str(value) if (value := _value(item, "rule")) is not None else None),
        stages=tuple(_value(item, "stages", default=()) or ()),
        recognition_domain=(
            str(value) if (value := _value(item, "recognition_domain")) is not None else None
        ),
        provenance=dict(_value(item, "provenance", default={}) or {}),
    )


def _normalize_issue(item: Any, *, unit_id: str) -> PreparedIssue:
    start = _value(item, "source_start")
    end = _value(item, "source_end")
    return PreparedIssue(
        code=str(_value(item, "code", default="ttsready.issue")),
        severity=str(_value(item, "severity", default="warning")),
        unit_id=str(_value(item, "unit_id", default=unit_id)),
        source_start=int(start) if start is not None else None,
        source_end=int(end) if end is not None else None,
        text=(str(value) if (value := _value(item, "text")) is not None else None),
        message=str(_value(item, "message", default=str(item))),
    )


@dataclass(frozen=True, slots=True)
class TTSReadyEngine:
    """Thin bridge to the source-neutral ttsready 0.2 API."""

    strict: bool = False

    def prepare(
        self,
        text: str,
        *,
        language: str,
        unit_id: str,
        role: str = "prose",
        protected_spans: Iterable[tuple[int, int]] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> PreparedUnit:
        try:
            import ttsready
        except ImportError as exc:  # pragma: no cover - packaging/runtime failure
            raise PreparationError("ttsready>=0.2 is required") from exc

        prepare_text = getattr(ttsready, "prepare_text", None)
        if not callable(prepare_text):
            raise PreparationError(
                "Installed ttsready does not expose the required 0.2 prepare_text() API"
            )

        result = prepare_text(
            text,
            language=language,
            unit_id=unit_id,
            role=role,
            protected_spans=tuple(protected_spans),
            metadata=dict(metadata or {}),
            strict=self.strict,
        )
        spoken_text = str(_value(result, "spoken_text", "text", default=text))
        changes = tuple(_normalize_change(item) for item in _value(result, "changes", default=()))
        issues = tuple(
            _normalize_issue(item, unit_id=unit_id) for item in _value(result, "issues", default=())
        )

        # Tolerate a convenience warnings property without depending on it as the
        # canonical 0.2 contract. Convert unstructured warnings to issues so the
        # rest of spokenfile has one QA representation.
        existing_messages = {item.message for item in issues}
        extra_issues = tuple(
            PreparedIssue(
                code="ttsready.warning",
                severity="warning",
                unit_id=unit_id,
                source_start=None,
                source_end=None,
                text=None,
                message=str(item),
            )
            for item in _value(result, "warnings", default=())
            if str(item) not in existing_messages
        )
        issues = (*issues, *extra_issues)

        effective_language = str(_value(result, "language", default=language))
        if effective_language != language:
            raise PreparationError(
                f"ttsready changed the caller-selected language for {unit_id!r}: "
                f"{language!r} -> {effective_language!r}"
            )
        return PreparedUnit(
            unit_id=unit_id,
            source_text=text,
            spoken_text=spoken_text,
            language=effective_language,
            changes=changes,
            issues=issues,
        )
