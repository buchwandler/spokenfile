from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .adapters import adapter_for, adapters
from .engine import PreparationEngine, TTSReadyEngine
from .errors import SpokenFileError
from .models import FilePreparationResult


def supported_formats() -> tuple[str, ...]:
    return tuple(sorted({ext for adapter in adapters() for ext in adapter.extensions}))


def default_output_path(source: str | Path) -> Path:
    path = Path(source).expanduser().resolve()
    return path.with_name(f"{path.stem}.spoken{path.suffix}")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.tmp-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _run(
    source: str | Path,
    *,
    language: str,
    output: str | Path | None,
    write: bool,
    report: str | Path | None,
    strict: bool,
    engine: PreparationEngine | None,
    force: bool,
) -> FilePreparationResult:
    source_path = Path(source).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if not language or not language.strip():
        raise ValueError("language must be a non-empty language identifier")

    adapter = adapter_for(source_path)
    selected_engine = engine or TTSReadyEngine(strict=strict)
    adapter_result = adapter.prepare(
        source_path,
        engine=selected_engine,
        language=language.strip(),
        strict=strict,
    )
    source_bytes = source_path.read_bytes()
    changed = source_bytes != adapter_result.data

    output_path: Path | None = None
    if write:
        output_path = (
            Path(output).expanduser().resolve()
            if output is not None
            else default_output_path(source_path)
        )
        if output_path == source_path:
            raise SpokenFileError("Output must be different from the source path")
        if output_path.exists():
            if output_path.is_dir():
                raise SpokenFileError(f"Output path is a directory: {output_path}")
            if not force:
                raise SpokenFileError(
                    f"Output already exists: {output_path}; pass force=True to replace it"
                )
        _atomic_write(output_path, adapter_result.data)

    result = FilePreparationResult(
        source=source_path,
        output=output_path,
        format=adapter.name,
        changed=changed,
        units_processed=adapter_result.units_processed,
        changes=adapter_result.changes,
        issues=adapter_result.issues,
    )
    if report is not None:
        report_path = Path(report).expanduser().resolve()
        if report_path.exists() and report_path.is_dir():
            raise SpokenFileError(f"Report path is a directory: {report_path}")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(result.to_json(), encoding="utf-8", newline="\n")
    return result


def prepare_file(
    source: str | Path,
    *,
    language: str,
    output: str | Path | None = None,
    report: str | Path | None = None,
    strict: bool = False,
    engine: PreparationEngine | None = None,
    force: bool = False,
) -> FilePreparationResult:
    """Prepare a source file and write a same-format spoken copy."""
    return _run(
        source,
        language=language,
        output=output,
        write=True,
        report=report,
        strict=strict,
        engine=engine,
        force=force,
    )


def inspect_file(
    source: str | Path,
    *,
    language: str,
    report: str | Path | None = None,
    strict: bool = False,
    engine: PreparationEngine | None = None,
) -> FilePreparationResult:
    """Prepare in memory and return the proposed changes without writing the converted file."""
    return _run(
        source,
        language=language,
        output=None,
        write=False,
        report=report,
        strict=strict,
        engine=engine,
        force=False,
    )
