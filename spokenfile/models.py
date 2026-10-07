from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class PreparedChange:
    source_start: int
    source_end: int
    source: str
    replacement: str
    kind: str = "normalization"
    rule: str | None = None
    stages: tuple[str, ...] = ()
    recognition_domain: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PreparedIssue:
    code: str
    severity: str
    unit_id: str
    source_start: int | None
    source_end: int | None
    text: str | None
    message: str


@dataclass(frozen=True, slots=True)
class PreparedUnit:
    unit_id: str
    source_text: str
    spoken_text: str
    language: str
    changes: tuple[PreparedChange, ...] = ()
    issues: tuple[PreparedIssue, ...] = ()

    @property
    def warnings(self) -> tuple[str, ...]:
        return tuple(item.message for item in self.issues if item.severity == "warning")


@dataclass(frozen=True, slots=True)
class SourceSpan:
    unit_id: str
    start: int
    end: int
    text: str
    locator: str
    role: str = "prose"


@dataclass(frozen=True, slots=True)
class FileChange:
    unit_id: str
    locator: str
    source_start: int
    source_end: int
    source: str
    replacement: str
    kind: str = "normalization"
    rule: str | None = None
    stages: tuple[str, ...] = ()
    recognition_domain: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FileIssue:
    code: str
    severity: str
    unit_id: str
    locator: str
    source_start: int | None
    source_end: int | None
    text: str | None
    message: str


@dataclass(frozen=True, slots=True)
class AdapterResult:
    data: bytes
    changes: tuple[FileChange, ...]
    issues: tuple[FileIssue, ...]
    units_processed: int

    @property
    def warnings(self) -> tuple[str, ...]:
        return tuple(item.message for item in self.issues if item.severity == "warning")


@dataclass(frozen=True, slots=True)
class FilePreparationResult:
    source: Path
    output: Path | None
    format: str
    changed: bool
    units_processed: int
    changes: tuple[FileChange, ...]
    issues: tuple[FileIssue, ...]

    @property
    def warnings(self) -> tuple[str, ...]:
        return tuple(item.message for item in self.issues if item.severity == "warning")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "spokenfile.report.v2",
            "source": str(self.source),
            "output": str(self.output) if self.output is not None else None,
            "format": self.format,
            "changed": self.changed,
            "units_processed": self.units_processed,
            "change_count": len(self.changes),
            "changes": [asdict(item) for item in self.changes],
            "issue_count": len(self.issues),
            "issues": [asdict(item) for item in self.issues],
            "warnings": list(self.warnings),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n"
