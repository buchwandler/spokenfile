from __future__ import annotations

from pathlib import Path

import typer

from . import __version__
from .api import inspect_file, prepare_file, supported_formats
from .errors import SpokenFileError

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    invoke_without_command=True,
    help="Prepare files for TTS.",
)


def _print_result(result) -> None:  # type: ignore[no-untyped-def]
    typer.echo(
        f"format={result.format} units={result.units_processed} "
        f"changes={len(result.changes)} changed={str(result.changed).lower()}"
    )
    for change in result.changes:
        typer.echo(f"{change.locator}: {change.source!r} -> {change.replacement!r}")
    for issue in result.issues:
        typer.echo(
            f"{issue.severity}: {issue.locator}: {issue.code}: {issue.message}",
            err=issue.severity in {"warning", "error"},
        )
    if result.output is not None:
        typer.echo(str(result.output))


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", help="Show the installed version and exit."),
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@app.command("formats")
def formats_command() -> None:
    """List supported input extensions."""
    typer.echo("\n".join(supported_formats()))


@app.command("inspect")
def inspect_command(
    source: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True),
    language: str = typer.Option(..., "--language", "-l"),
    report: Path | None = typer.Option(None, "--report"),
    strict: bool = typer.Option(False, "--strict"),
) -> None:
    """Show proposed changes without writing the converted file."""
    try:
        result = inspect_file(source, language=language, report=report, strict=strict)
    except (SpokenFileError, ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    _print_result(result)


@app.command("prepare")
def prepare_command(
    source: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True),
    language: str = typer.Option(..., "--language", "-l"),
    output: Path | None = typer.Option(None, "--output", "-o"),
    report: Path | None = typer.Option(None, "--report"),
    strict: bool = typer.Option(False, "--strict"),
    force: bool = typer.Option(False, "--force", help="Replace an existing output file."),
) -> None:
    """Write a same-format file containing explicit spoken forms."""
    try:
        result = prepare_file(
            source,
            language=language,
            output=output,
            report=report,
            strict=strict,
            force=force,
        )
    except (SpokenFileError, ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    _print_result(result)
