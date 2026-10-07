from __future__ import annotations

import io
import zipfile
from pathlib import Path

from ..engine import PreparationEngine
from ..errors import PreparationError
from ..models import AdapterResult, FileChange, FileIssue
from .common import decode_htmlish
from .html import prepare_html_text

_HTML_SUFFIXES = (".xhtml", ".html", ".htm")


class EpubAdapter:
    name = "epub"
    extensions = (".epub",)

    def supports(self, source: Path) -> bool:
        return source.suffix.casefold() == ".epub"

    def prepare(
        self,
        source: Path,
        *,
        engine: PreparationEngine,
        language: str,
        strict: bool = False,
    ) -> AdapterResult:
        changes: list[FileChange] = []
        issues: list[FileIssue] = []
        units_processed = 0
        changed_members = 0
        output = io.BytesIO()

        try:
            archive = zipfile.ZipFile(source, "r")
        except (OSError, zipfile.BadZipFile) as exc:
            raise PreparationError(f"Invalid EPUB/ZIP file: {source}") from exc

        with archive:
            names = archive.namelist()
            if "mimetype" not in names or archive.read("mimetype") != b"application/epub+zip":
                raise PreparationError("EPUB must contain an application/epub+zip mimetype member")

            with zipfile.ZipFile(output, "w") as target:
                target.comment = archive.comment
                for info in archive.infolist():
                    data = archive.read(info.filename)
                    if info.filename.casefold().endswith(_HTML_SUFFIXES):
                        try:
                            decoded = decode_htmlish(data)
                        except UnicodeDecodeError:
                            issues.append(
                                FileIssue(
                                    code="source.encoding",
                                    severity="warning",
                                    unit_id=f"epub:{info.filename}",
                                    locator=info.filename,
                                    source_start=None,
                                    source_end=None,
                                    text=None,
                                    message=f"Skipped {info.filename}: unsupported non-Unicode HTML encoding",
                                )
                            )
                        else:
                            rendered, member_changes, member_issues, count = prepare_html_text(
                                decoded.text,
                                source_path=source,
                                engine=engine,
                                language=language,
                                strict=strict,
                                prefix=f"epub:{info.filename}",
                                locator_prefix=info.filename,
                            )
                            new_data = decoded.encode(rendered)
                            if new_data != data:
                                changed_members += 1
                                data = new_data
                            changes.extend(member_changes)
                            issues.extend(member_issues)
                            units_processed += count
                    target.writestr(info, data)

        if units_processed == 0:
            issues.append(
                FileIssue(
                    code="source.no_visible_text",
                    severity="warning",
                    unit_id="epub",
                    locator=str(source),
                    source_start=None,
                    source_end=None,
                    text=None,
                    message="No visible HTML/XHTML text units were found in the EPUB",
                )
            )
        if changed_members == 0 and changes:
            raise PreparationError("EPUB reported changes but no archive member changed")
        return AdapterResult(output.getvalue(), tuple(changes), tuple(issues), units_processed)
