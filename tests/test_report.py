import json

from spokenfile import inspect_file


def test_report_json(tmp_path):
    from conftest import FakeEngine

    source = tmp_path / "notes.txt"
    source.write_text("2 kg\n", encoding="utf-8")
    report = tmp_path / "report.json"
    result = inspect_file(source, language="en", report=report, engine=FakeEngine())
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["schema"] == "spokenfile.report.v2"
    assert payload["change_count"] == len(result.changes) == 1
    assert payload["output"] is None
