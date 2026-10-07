from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..engine import PreparationEngine
from ..models import AdapterResult


class Adapter(Protocol):
    name: str
    extensions: tuple[str, ...]

    def supports(self, source: Path) -> bool: ...

    def prepare(
        self,
        source: Path,
        *,
        engine: PreparationEngine,
        language: str,
        strict: bool = False,
    ) -> AdapterResult: ...
