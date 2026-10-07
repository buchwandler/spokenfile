from __future__ import annotations

import sys
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from spokenfile.engine import TTSReadyEngine
from spokenfile.errors import PreparationError


def test_engine_uses_source_neutral_prepare_text(monkeypatch):
    @dataclass
    class Change:
        source_start: int = 0
        source_end: int = 1
        source: str = "2"
        replacement: str = "two"
        kind: str = "number"
        stages: tuple[str, ...] = ("numbers",)

    def prepare_text(text, **kwargs):
        assert kwargs["unit_id"] == "u1"
        assert kwargs["role"] == "prose"
        assert kwargs["metadata"]["locator"] == "line 1"
        return SimpleNamespace(
            source_text=text,
            spoken_text="two kg",
            language="en",
            changes=(Change(),),
            issues=(),
        )

    monkeypatch.setitem(sys.modules, "ttsready", SimpleNamespace(prepare_text=prepare_text))
    result = TTSReadyEngine().prepare(
        "2 kg",
        language="en",
        unit_id="u1",
        metadata={"locator": "line 1"},
    )
    assert result.spoken_text == "two kg"
    assert result.changes[0].replacement == "two"
    assert result.issues == ()


def test_engine_requires_ttsready_02_prepare_text(monkeypatch):
    monkeypatch.setitem(sys.modules, "ttsready", SimpleNamespace())
    with pytest.raises(PreparationError, match="0.2 prepare_text"):
        TTSReadyEngine().prepare("2 kg", language="en", unit_id="u1")


def test_engine_normalizes_structured_issues(monkeypatch):
    def prepare_text(text, **kwargs):
        return SimpleNamespace(
            spoken_text=text,
            language="en",
            changes=(),
            issues=(
                SimpleNamespace(
                    code="speech.residual_symbol",
                    severity="warning",
                    unit_id=kwargs["unit_id"],
                    source_start=1,
                    source_end=2,
                    text="+",
                    message="symbol remains",
                ),
            ),
        )

    monkeypatch.setitem(sys.modules, "ttsready", SimpleNamespace(prepare_text=prepare_text))
    result = TTSReadyEngine().prepare("A+B", language="en", unit_id="u1")
    assert result.issues[0].code == "speech.residual_symbol"
    assert result.warnings == ("symbol remains",)
