from __future__ import annotations

import re
from spokenfile.models import PreparedChange, PreparedUnit


class FakeEngine:
    replacements = {
        "2": "two",
        "24": "twenty four",
        "Dr.": "Doctor",
    }

    def prepare(
        self,
        text: str,
        *,
        language: str,
        unit_id: str,
        role: str = "prose",
        protected_spans=(),
        metadata=None,
    ) -> PreparedUnit:
        changes = []
        output = text
        edits = []
        for surface, spoken in self.replacements.items():
            for match in re.finditer(re.escape(surface), text):
                edits.append((match.start(), match.end(), surface, spoken))
        edits.sort(key=lambda item: (item[0], -(item[1] - item[0])))
        selected = []
        end = -1
        for edit in edits:
            if edit[0] < end:
                continue
            selected.append(edit)
            end = edit[1]
        for start, end, surface, spoken in selected:
            changes.append(
                PreparedChange(
                    source_start=start,
                    source_end=end,
                    source=surface,
                    replacement=spoken,
                    kind="test",
                    rule="fake",
                )
            )
        for start, end, surface, spoken in reversed(selected):
            output = output[:start] + spoken + output[end:]
        return PreparedUnit(unit_id, text, output, language, tuple(changes), ())
